#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# Python >= 3.7 only

import functools
import operator
import re

from ansible.module_utils.common.collections import is_sequence


# lazy copy-paste
def _convert_to_sequence(arg):
    """Converts arg so that it can be processed as a list-like object."""
    if is_sequence(arg):
        return arg
    else:
        return [arg]
# --- end of _convert_to_sequence (...) ---

def _iter_sequence(arg):
    if hasattr(arg, 'values'):
        # dict-like
        return iter(arg.values())
    else:
        # list-like
        return iter(arg)
# --- end of _iter_sequence (...) ---


def _identity(obj):
    return obj


@functools.lru_cache(maxsize=32)
def _itemgetter_recursive(full_key):
    key_path = full_key.split('.')

    def wrapper_recursive(obj):
        attr = obj

        for key in key_path:
            try:
                next_attr = getattr(attr, key)
            except AttributeError:
                return None
            else:
                attr = next_attr
            # --
        # -- end for

        return attr
    # --- end of wrapper_recursive (...) ---

    if not key_path:
        return _identity

    elif len(key_path) == 1:
        return operator.itemgetter(key_path[0])

    else:
        return wrapper_recursive
# --- end of _itemgetter_recursive (...) ---


def _get_keyfunc(key):
    if (not key) or (key is True):
        return _identity

    elif isinstance(key, str):
        return _itemgetter_recursive(key)

    elif hasattr(key, '__iter__') or hasattr(key, '__next__'):
        item_getters = [_itemgetter_recursive(k) for k in key]
        # function that returns a (usually hashable) tuple of keys
        return (lambda o, *, _fnv=item_getters: tuple((_fn(o) for _fn in _fnv)))

    else:
        return _itemgetter_recursive(key)
# --- end of _get_keyfunc (...) ---


def _aenv_items_diff_calc_key_sets(
    dict_left, dict_right,
    keys_ignore=None, keys_regexp_ignore=None
):
    """Helper function, see aenv_items_diff()."""
    # build effective keys set for left / right
    # start fully loaded
    keys_left   = set(dict_left)
    keys_right  = set(dict_right)

    drop_keys_left = set()
    drop_keys_right = set()

    # mark keys for removal: apply keys_ignore if given
    if keys_ignore:
        keys_ignore_set = set(_convert_to_sequence(keys_ignore))
        drop_keys_left.update(keys_ignore_set)
        drop_keys_right.update(keys_ignore_set)
    # --

    # mark keys for removal: apply keys_regexp_ignore if given
    if keys_regexp_ignore:
        keys_regexp_ignore_exprv = [
            re.compile(expr) for expr in _convert_to_sequence(keys_regexp_ignore)
        ]
        keys_regexp_ignore_searchv = [
            expr.search for expr in keys_regexp_ignore_exprv
        ]

        check_keys_regexp_ignored = (
            lambda s, *, _fnv=keys_regexp_ignore_searchv:
            any((_fn(s) for _fn in _fnv))
        )

        # NOTE: might check individual keys twice
        # when both keys_ignore and keys_regexp_ignore are given
        drop_keys_left.update((
            s for s in keys_left if check_keys_regexp_ignored(s)
        ))

        drop_keys_right.update((
            s for s in keys_right if check_keys_regexp_ignored(s)
        ))
    # --

    # remove keys
    if drop_keys_left:
        keys_left -= drop_keys_left

    if drop_keys_right:
        keys_right -= drop_keys_right

    return (keys_left, keys_right)
# --- end of _aenv_items_diff_calc_key_sets (...) ---


def aenv_items_diff(
    left, right, *,
    key=None, lkey=None, rkey=None,
    keys_ignore=None, keys_regexp_ignore=None
):
    """Given two item collections left and right,
    this filter functions determines which items
    appear in both of them or just either one.

    Comparison may be controlled by specifying
    which key should be used for which collection (lkey / rkey).
    When lkey/rkey is True, items are used as keys.
    When lkey/rkey is None, key is used as fallback,
    which may be None or True for identical behavior to a True lkey/rkey.

    Certain keys can be ignored via the keys_ignore
    and keys_regexp_ignore keyword arguments.
    The latter one applies to str keys only.

    Example:
      >>> ['a', 'b', 'c'] | aenv_items_diff(['b', 'c', 'd'])
      {
        kboth:  {'b', 'c'},
        kdiff:  {'a', 'd'},
        kleft:  {'a'},
        kright: {'d'},
        both:   {'b': ('b', 'b'), 'c': ('c', 'c')},
        left:   {'a': 'a'},
        right:  {'d': 'd'},
      }

    Note: This function is not suitable for complex dict comparisions.
          One could, for instance, compare create-user objects by key 'name',
          but that doesn't verify whether options such as 'can-login' differ.
          See aenv_dict_diff() for an extendend variant that offers this functionality.

    @param   left:      collection of items (left hand side)
    @type    left:      iterable|genexpr of C{object}
    @param   right:     collection of items (right hand side)
    @type    right:     iterable|genexpr of C{object}
    @keyword key:       fallback key for lkey/rkey
                        Either None/True for identity (use item as key)
                        or a string for getattr.
                        Supports nested attributes separated by dot chars ('a.b').
                        May also be a list of attributes.
    @type    key:       C{None} | C{bool} | C{str}
    @keyword lkey:      preferred key for items from left (unless None)
    @type    lkey:      C{None} | C{bool} | C{str}
    @keyword rkey:      preferred key for items from right (unless None)
    @type    rkey:      C{None} | C{bool} | C{str}
    @keyword keys_ignore:         listed keys should be ignored
    @type    keys_ignore:         typically C{None} or iterable of C{object}
    @keyword keys_regexp_ignore:  keys matching these regular expression(s) should be ignored
    @type    keys_regexp_ignore:  typically C{None} or iterable of C{str}

    @returns:           diff result mapping containing these keys / values:
                          - both       => (item_left, item_right)
                          - only_left  => item_left
                          - only_right => item_right
    @rtype:             C{dict}
    """
    keyfunc_left  = _get_keyfunc(lkey or key)
    keyfunc_right = _get_keyfunc(rkey or key)

    dict_left  = {keyfunc_left(o)  : o for o in _iter_sequence(left)}
    dict_right = {keyfunc_right(o) : o for o in _iter_sequence(right)}

    (keys_left, keys_right) = _aenv_items_diff_calc_key_sets(
        dict_left, dict_right,
        keys_ignore=keys_ignore,
        keys_regexp_ignore=keys_regexp_ignore
    )

    # cmp operation on key sets
    kboth  = keys_left & keys_right
    kdiff  = keys_left ^ keys_right
    kleft  = kdiff - keys_right
    kright = kdiff - keys_left

    return {
        # key -> (left, right)
        'both'       : {k: (dict_left[k], dict_right[k]) for k in kboth},
        # key -> left
        'only_left'  : {k: dict_left[k] for k in kleft},
        # key -> right
        'only_right' : {k: dict_right[k] for k in kright},
    }
# --- end of aenv_items_diff (...) ---


def aenv_dict_diff(left, right, *, cmp_key=None, cmp_lkey=None, cmp_rkey=None, **kwargs):
    """Given two item collections left and right,
    this filter functions determines which items
    appear in both of them or just either one.

    For items appearing in both left and right,
    this function also checks relevant attributes for equality,
    as determined by the cmp_key / cmp_lkey / cmp_rkey keyword arguments.

    See aenv_items_diff() for the overall idea and details.
    This function adds item comparison based on a second key func.

    Use cases include:
      - user management: Compare wanted user entries ("left")
                         against current configuration ("right")
                         while ignore some builtin names
                         ("keys_ignore" or "keys_regexp_ignore").
                         One would then proceed to drop users
                         listed in "only_right" and reconfigure
                         those listed in "both_diff".

    @param   left:      collection of items (left hand side)
    @type    left:      iterable|genexpr of C{object}
    @param   right:     collection of items (right hand side)
    @type    right:     iterable|genexpr of C{object}
    @keyword key:       fallback key for lkey/rkey
                        Either None/True for identity (use item as key)
                        or a string for getattr.
                        Supports nested attributes separated by dot chars ('a.b').
                        May also be a list of attributes.
    @type    key:       C{None} | C{bool} | C{str}
    @keyword lkey:      preferred key for items from left (unless None)
    @type    lkey:      C{None} | C{bool} | C{str}
    @keyword rkey:      preferred key for items from right (unless None)
    @type    kkey:      C{None} | C{bool} | C{str}

    @keyword cmp_key:   fallback attr-cmp key for cmp_lkey/cmp_rkey
    @type    cmp_key:   C{None} | C{bool} | C{str}
    @keyword cmp_lkey:  preferred attr-cmp key for items from left (unless None)
    @type    cmp_lkey:  C{None} | C{bool} | C{str}
    @keyword cmp_rkey:  preferred attr-cmp key for items from right (unless None)
    @type    cmp_rkey:  C{None} | C{bool} | C{str}
    @keyword keys_ignore:         listed keys should be ignored
    @type    keys_ignore:         typically C{None} or iterable of C{object}
    @keyword keys_regexp_ignore:  keys matching these regular expression(s) should be ignored
    @type    keys_regexp_ignore:  typically C{None} or iterable of C{str}


    @returns:           diff result mapping containing these keys / values:
                          - both       => (item_left, item_right)
                          - both_equal => (item_left, item_right)
                          - both_diff  => (item_left, item_right)
                          - only_left  => item_left
                          - only_right => item_right
    @rtype:             C{dict}
    """

    keyfunc_cmp_left  = _get_keyfunc(cmp_lkey or cmp_key)
    keyfunc_cmp_right = _get_keyfunc(cmp_rkey or cmp_key)

    items_diff_result = aenv_items_diff(left, right, **kwargs)
    items_both = items_diff_result['both']

    items_both_equal = {}
    items_both_diff  = {}

    for item_key, item in items_both.items():
        item_cmp_key_left  = keyfunc_cmp_left(item[0])
        item_cmp_key_right = keyfunc_cmp_right(item[1])

        if item_cmp_key_left == item_cmp_key_right:
            items_both_equal[item_key] = item
        else:
            items_both_diff[item_key] = item
        # --
    # --

    items_diff_result['both_equal'] = items_both_equal
    items_diff_result['both_diff'] = items_both_diff
    return items_diff_result
# --- end of aenv_dict_diff (...) ---


class FilterModule(object):
    ''' Ansible jinja2 filters - dict diff '''

    def filters(self):
        return {
            # misc
            'aenv_items_diff' : aenv_items_diff,
            'aenv_dict_diff'  : aenv_dict_diff,
        }
