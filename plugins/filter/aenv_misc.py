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

from jinja2.runtime import Undefined


def str_to_bool(arg):
    if isinstance(arg, bool):
        return arg

    elif isinstance(arg, int):
        return bool(arg)

    elif isinstance(arg, str):
        norm_arg = arg.strip().lower()

        # on/off, enable(d)/disable(d), ...
        if norm_arg in {'true', 'yes', '1'}:
            return True

        elif norm_arg in {'false', 'no', '0'}:
            return False

        else:
            raise ValueError('not a bool word', arg)

    else:
        raise TypeError(arg)
# --- end of str_to_bool (...) ---


def _bool_str(word_true, word_false, arg):
    return (word_true if str_to_bool(arg) else word_false)
# --- end of _bool_str (...) ---

bool_str       = functools.partial(_bool_str, 'true', 'false')
bool_str_yesno = functools.partial(_bool_str, 'yes', 'no')
bool_str_int   = functools.partial(_bool_str, '1', '0')


def split_host_domain(arg, default_domain=Undefined):
    if (not arg) or (arg is Undefined):
        return (Undefined, default_domain)
    else:
        hostname, sep, domain = arg.rstrip('.').partition('.')

        return ((hostname or Undefined), (domain or default_domain))
# --- end of split_host_domain (...) ---


def short_hostname(arg):
    """Returns the hostname (first label) of a fully-qualified domain name."""
    return split_host_domain(arg)[0]
# --- end of short_hostname (...) ---


def split_domain(arg):
    """Returns the domain path of a fully-qualified domain name.
    (substr starting at the second domain label)."""
    return split_host_domain(arg)[1]
# --- end of split_domain (...) ---


class FilterModule(object):
    ''' Ansible jinja2 filters - misc/generic '''

    def filters(self):
        return {
            # booleans
            'aenv_bool'             : str_to_bool,
            'aenv_bool_str'         : bool_str,
            'aenv_bool_str_yesno'   : bool_str_yesno,
            'aenv_bool_str_int'     : bool_str_int,

            # misc
            'aenv_hostname'         : short_hostname,
            'aenv_domainname'       : split_domain,
        }
