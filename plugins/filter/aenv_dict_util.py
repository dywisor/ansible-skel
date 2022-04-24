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

import operator
from ansible.module_utils.common.collections import is_sequence


# lazy copy-paste
def _convert_to_sequence(arg):
    """Converts arg so that it can be processed as a list-like object."""
    if is_sequence(arg):
        return arg
    else:
        return [arg]
# --- end of _convert_to_sequence (...) ---


def _dict_extract_keys(func, dict_arg):
    """Returns a list of all dict keys for which func(value) evaluates to True.

    @param func:  dict value checker
    @type  func:  callable :: C{object} -> C{bool}

    @return: list of dict keys
    @rtype:  usually C{list} of C{str}
    """
    if hasattr(dict_arg, 'items'):
        dict_items_iter = dict_arg.items()
    else:
        dict_items_iter = dict_arg

    return [k for k, v in dict_items_iter if func(v)]
# --- end of _dict_extract_keys (...) ---


def dict_extract_true(dict_arg):
    """Returns all keys from the given dictionary whose values are true-ish."""
    return _dict_extract_keys(bool, dict_arg)
# --- end of dict_extract_true (...) ---


def dict_extract_false(dict_arg):
    """Returns all keys from the given dictionary whose values are false-ish."""
    return _dict_extract_keys(operator.__not__, dict_arg)
# --- end of dict_extract_false (...) ---


def _dict_sort(dict_arg, *, key=None):
    if key is None:
        key = lambda kv: kv[0]

    return sorted(dict_arg.items(), key=key)
# --- end of _dict_sort (...) ---


def dict_sort_keys(dict_arg, *, key=None):
    """Returns a sorted list of keys from the given dictionary."""
    # return sorted(dict_arg)
    return [k for k, v in _dict_sort(dict_arg, key=key)]
# --- end of dict_sort_keys (...) ---


def dict_sort_values(dict_arg, *, key=None):
    """Returns a sorted list of values from the given dictionary.
    By default, values are sorted by their dict key."""
    return [v for k, v in _dict_sort(dict_arg, key=key)]
# --- end of dict_sort_values (...) ---


def dict_fromkeys(arg, *, value=True):
    return {k: value for k in _convert_to_sequence(arg)}
# --- end of dict_fromkeys (...) ---


class FilterModule(object):
    ''' Ansible jinja2 filters - generic dict helpers '''

    def filters(self):
        return {
            'aenv_dict_extract_true'    : dict_extract_true,
            'aenv_dict_extract_false'   : dict_extract_false,

            'aenv_dictsort_keys'        : dict_sort_keys,
            'aenv_dictsort_values'      : dict_sort_values,
            'aenv_dict_fromkeys'        : dict_fromkeys,
        }
