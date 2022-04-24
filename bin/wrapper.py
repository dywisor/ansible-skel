#!/usr/bin/python3
# -*- coding: utf-8 -*-

import collections
import os
import os.path
import pathlib
import shlex
import sys


def is_scalar(arg):
    if isinstance(arg, str):
        return True
    elif hasattr(arg, '__iter__') or hasattr(arg, '__next__'):
        return False
    else:
        return True
# ---


class EnvBuilder(object):

    def __init__(self, base_env):
        super().__init__()
        self.base_env  = base_env
        self.extra_env = {}
        self._cached_pathlike = {}

    def __setitem__(self, key, value):
        self.extra_env[key] = value

    def __delitem__(self, key):
        # add del-stub entry
        self.extra_env[key] = None

    discard = __delitem__

    def __getitem__(self, key):
        try:
            return self.extra_env[key]
        except KeyError:
            return self.base_env[key]
    # --- end of __getitem__ (...) ---

    def __contains__(self, key):
        try:
            value = self[key]
        except KeyError:
            return False
        else:
            return (value is not None)
    # --- end of __contains__ (...) ---

    def commit(self):
        self.extra_env.update((
            (varname, ':'.join(map(str, values)))
            for varname, values in self._cached_pathlike.items()
        ))
        self._cached_pathlike.clear()
    # --- end of commit (...) ---

    def build_env(self):
        self.commit()

        env = {}
        env.update(self.base_env)
        env.update(self.extra_env)

        return {
            k: str(v)
            for k, v in env.items()
            if (v is not None)
        }
    # --- end of build_env (...) ---

    def _get_pathlike(self, key):
        try:
            value = self._cached_pathlike[key]

        except KeyError:
            value = collections.deque()

            try:
                str_value = self[key]

            except KeyError:
                pass

            else:
                if str_value:
                    value.extend(str_value.split(':'))
            # --

            self._cached_pathlike[key] = value
        # --

        return value
    # --- end of _get_pathlike (...) ---

    def pathlike_push(self, key, values):
        pathlike = self._get_pathlike(key)
        if is_scalar(values):
            pathlike.appendleft(values)
        else:
            pathlike.extendleft(reversed(values))
    # ---

    def pathlike_append(self, key, values):
        pathlike = self._get_pathlike(key)

        if is_scalar(values):
            pathlike.append(values)
        else:
            pathlike.extend(values)
    # ---

# --- end of EnvBuilder ---


class RunConfig(object):

    BUILTIN_WRAPPERS_INSTALL = {
        'ansible-config',
        'ansible-connection',
        'ansible-console',
        'ansible-doc',
        'ansible-galaxy',
        'ansible-inventory',
        #'ansible-lint',
        'ansible-playbook',
        'ansible-pull',
        'ansible-test',
        'ansible-vault',

        'env', 'env-diff',
    }

    BUILTIN_WRAPPERS_NOINSTALL = {
        'bash', 'dash', 'ksh', 'ash', 'sh',
    }

    def __init__(self):
        self.script_called = None
        self.script_called_dir = None

        self.script_file = None
        self.script_dir = None

        self.skel_prjroot = None
        self.ansible_prjroot = None

        self.skel_sharedir = None
        self.script_searchpath = None
    # --- end of __init__ (...) ---

    def get_scripts_map(self, *, add_noinstall=False):
        def scan_scripts():
            for script_dir in self.script_searchpath:
                for ent in script_dir.iterdir():
                    if ent.is_file():
                        yield ent
        # ---

        smap = {}

        for script_ent in scan_scripts():
            name = script_ent.name

            if name not in smap:
                smap[name] = str(script_ent)
        # --

        for name in self.BUILTIN_WRAPPERS_INSTALL:
            if name not in smap:
                smap[name] = None
        # --

        if add_noinstall:
            for name in self.BUILTIN_WRAPPERS_NOINSTALL:
                if name not in smap:
                    smap[name] = None
            # --
        # --

        return smap
    # --- end of get_scripts_map (...) ---

    def find_script(self, wrapped_name):
        for search_dir in self.script_searchpath:
            wrapped_script = search_dir / wrapped_name

            if wrapped_script.is_file():
                return (False, wrapped_script)
        # --

        # builtins after script search
        for builtin_wrappers in [
            self.BUILTIN_WRAPPERS_INSTALL,
            self.BUILTIN_WRAPPERS_NOINSTALL,
        ]:
            if wrapped_name in builtin_wrappers:
                return (True, wrapped_name)
        # --

        return (None, None)
    # --- end of find_script (...) ---

# --- end of RunConfig ---


def main(prog, argv):
    config = RunConfig()

    config.script_called = pathlib.Path(__file__)
    # do not resolve symlinks..
    config.script_called_dir = pathlib.Path(os.path.abspath(config.script_called.parent))

    config.script_file = pathlib.Path(os.path.realpath(config.script_called))
    config.script_dir = config.script_file.parent

    # get ansible-skel project root
    config.skel_prjroot = config.script_dir.parent
    if not (config.skel_prjroot / '.ansible_skel').exists():
        sys.stderr.write(
            f'Failed to detect ansible skel root directory: {config.skel_prjroot}?\n'
        )
        return 254
    # --

    # get helper files root below ansible-skel project root
    config.skel_sharedir = config.skel_prjroot / 'share'
    if not config.skel_sharedir.is_dir():
        config.skel_sharedir = None
    # --

    # get ansible project root from where we were called
    # (if not equal not ansible-skel project root)
    config.ansible_prjroot = config.script_called_dir.parent
    if config.skel_prjroot.samefile(config.ansible_prjroot):
        config.ansible_prjroot = None

    else:
        if not (config.ansible_prjroot / 'roles').is_dir():
            sys.stderr.write(
                f'Failed to detect ansible roles root directory: {config.ansible_prjroot}? (no roles/ subdir)\n'
            )
            return 253
        # --
    # --

    # construct search path for scripts and aux files
    config.script_searchpath = [
        search_dir for search_dir in (
            (d / 'libexec')
            for d in filter(None, [config.ansible_prjroot, config.skel_sharedir])
        )
        if search_dir.is_dir()
    ]

    # get the requested wrapped script
    wrapped_name = config.script_called.stem

    if wrapped_name == 'wrapper':
        if not argv:
            sys.stderr.write('Cannot infer wrapped script name!\n')
            return 252

        else:
            wrapped_name = argv[0]
            argv = argv[1:]

            if wrapped_name and wrapped_name[0] == '-':
                if wrapped_name in {'-h', '--help'}:
                    return main_show_help(config.script_called.name)

                elif wrapped_name in {'-l', '--list'}:
                    return main_list_scripts(config)

                elif wrapped_name in {'-i', '--install'}:
                    return main_install_scripts(config, argv, uninstall=False)

                elif wrapped_name in {'-u', '--uninstall'}:
                    return main_install_scripts(config, argv, uninstall=True)

                elif wrapped_name in {'-r', '--reinstall'}:
                    exit_code = main_install_scripts(config, argv, uninstall=True)
                    if exit_code is True:
                        exit_code = main_install_scripts(config, argv, uninstall=False)

                    return exit_code

                else:
                    sys.stderr.write(f'Unknown wrapper command: {wrapped_name}\n')
                    return 252
            # --
        # --
    # --

    (wrapped_path_lookup, wrapped_script) = config.find_script(wrapped_name)

    if not wrapped_script:
        sys.stderr.write(f'Failed to locate script: {wrapped_name}\n')
        return 251
    # --

    # initialize environment
    env_builder = EnvBuilder(os.environ)

    # drop some shell vars
    env_builder.discard('_')
    env_builder.discard('OLDPWD')

    env_builder['AENV_ROOT'] = (config.ansible_prjroot or config.skel_prjroot)
    env_builder['AENV_SKEL_PRJROOT'] = config.skel_prjroot
    env_builder['AENV_SKEL_SHAREDIR'] = config.skel_sharedir
    env_builder['AENV_ANSIBLE_PRJROOT'] = config.ansible_prjroot

    env_builder.pathlike_push('PATH', config.script_searchpath)

    # scan <skel>
    main_init_env_ansible_prjroot(env_builder, config.skel_prjroot)

    if config.ansible_prjroot:
        # scan <prjroot>/dust/*
        custom_collections_dir = config.ansible_prjroot / 'dust'

        if custom_collections_dir.is_dir():
            for ent in custom_collections_dir.iterdir():
                if ent.is_dir():
                    main_init_env_ansible_common(env_builder, ent)
        # --

        # scan <prjroot>
        main_init_env_ansible_skel(env_builder, config.ansible_prjroot)
    # --

    env  = env_builder.build_env()
    cmdv = [wrapped_script] + argv

    if wrapped_path_lookup:
        # could also be a code builtin
        if wrapped_script == 'env-diff':
            return main_dump_env(env_builder.extra_env)

        elif wrapped_script == 'env':
            return main_dump_env(env)

        else:
            os.execvpe(cmdv[0], cmdv, env)

    else:
        os.execve(cmdv[0], cmdv, env)
# --- end of main (...) ---


def main_show_help(prog, *, fh=None):
    if fh is None:
        fh = sys.stdout

    fh.write(
        (
            'Usage:\n'
            '  {prog} [-h|-l]\n'
            '  {prog} [-i|-u|-r] [DESTDIR]\n'
            '  {prog} COMMAND [ARG...]\n'
            '\n'
            'Options:\n'
            '  -h, --help           show this message and exit\n'
            '  -l, --list           list wrapper commands\n'
            '  -i, --install        add wrapper links to DESTDIR\n'
            '  -u, --uninstall      remove wrapper links from DESTDIR\n'
            '  -r, --reinstall      remove wrapper links from DESTDIR and then readd them\n'
            '\n'
            'DESTDIR defaults to the Ansible project root if the wrapper is run from there.\n'
        ).format(prog=prog)
    )
# --- end of main_show_help (...) ---


def main_dump_env(env):
    for varname, value in sorted(env.items(), key=lambda kv: kv[0]):
        if value is not None:
            # str(value) may be necessary when processing
            # intermediate env data (e.g. env_builder.extra_env)
            sys.stdout.write(
                '{}={}\n'.format(varname, shlex.quote(str(value)))
            )
    # --

    return True
# --- end of main_dump_env (...) ---


def main_list_scripts(config):
    scripts_map = config.get_scripts_map(add_noinstall=True)

    if scripts_map:
        sys.stderr.write('\n'.join(sorted(scripts_map)) + '\n')

    return True
# --- end of main_list_scripts (...) ---


def main_install_scripts(config, argv, *, uninstall=False):
    if argv:
        dest_dir = pathlib.Path(argv[0])

    elif config.ansible_prjroot:
        dest_dir = config.ansible_prjroot / 'bin'

    else:
        sys.stderr.write('Missing <destdir> argument (or ansible prjroot)\n')
        return 2
    # --

    scripts_map = config.get_scripts_map(add_noinstall=False)

    if uninstall:
        for script_name in sorted(scripts_map):
            script_link = dest_dir / script_name

            try:
                # NOT checking whether script_link is a symlink
                os.unlink(script_link)

            except FileNotFoundError:
                pass

            else:
                sys.stdout.write(f'Removed: {script_link}\n')
        # --

    else:
        link_target = os.path.relpath(config.script_file, dest_dir)

        os.makedirs(dest_dir, exist_ok=True)

        for script_name in sorted(scripts_map):
            script_link = dest_dir / script_name

            try:
                os.symlink(link_target, (dest_dir / script_name))

            except FileExistsError:
                # accept that, regardless of file type
                pass

            else:
                sys.stdout.write(f'Added: {script_link}\n')
        # --
    # --

    return True
# --- end of main_install_scripts (...) ---


def main_init_env_ansible_common(env, root):
    for varname, dirname in [
        ('AENV_FILES_PATH',             'files'),
        # ANSIBLE_COLLECTIONS_PATH -- new name in Ansible 2.10,
        # old name can still be used:
        ('ANSIBLE_COLLECTIONS_PATHS',   'collections'),
        ('ANSIBLE_ROLES_PATH',          'roles'),
        ('PYTHONPATH',                  'pym'),
    ]:
        dirpath = root / dirname

        if dirpath.is_dir():
            env.pathlike_push(varname, dirpath)
    # --

    plugins_dir = root / 'plugins'
    if plugins_dir.is_dir():
        for varname, dirname in [
            ('ANSIBLE_DOC_FRAGMENT_PLUGINS',    'doc_fragment'),
            ('ANSIBLE_ACTION_PLUGINS',          'action'),
            ('ANSIBLE_BECOME_PLUGINS',          'become'),
            ('ANSIBLE_CACHE_PLUGINS',           'cache'),
            ('ANSIBLE_CALLBACK_PLUGINS',        'callback'),
            ('ANSIBLE_CLICONF_PLUGINS',         'cliconf'),
            ('ANSIBLE_CONNECTION_PLUGINS',      'connection'),
            ('ANSIBLE_FILTER_PLUGINS',          'filter'),
            ('ANSIBLE_HTTPAPI_PLUGINS',         'httpapi'),
            ('ANSIBLE_INVENTORY_PLUGINS',       'inventory'),
            ('ANSIBLE_LIBRARY',                 'modules'),
            ('ANSIBLE_LOOKUP_PLUGINS',          'lookup'),
            ('ANSIBLE_MODULE_UTILS',            'module_utils'),
            ('ANSIBLE_NETCONF_PLUGINS',         'netconf'),
            ('ANSIBLE_STRATEGY_PLUGINS',        'strategy'),
            ('ANSIBLE_TERMINAL_PLUGINS',        'terminal'),
            ('ANSIBLE_TEST_PLUGINS',            'test'),
            ('ANSIBLE_VARS_PLUGINS',            'vars'),
        ]:
            dirpath = plugins_dir / dirname

            if dirpath.is_dir():
                env.pathlike_push(varname, dirpath)
    # --
# --- end of main_init_env_ansible_common (...) ---


def main_init_env_ansible_skel(env, root):
    main_init_env_ansible_common(env, root)
# --- end of main_init_env_ansible_skel (...) ---


def main_init_env_ansible_prjroot(env, root):
    main_init_env_ansible_common(env, root)

    local_dir = root / 'local'

    if not local_dir.is_dir():
        env.discard('AENV_LOCAL_DIR')
        env.discard('AENV_BACKUP_ROOT')
        env.discard('AENV_LOCAL_SRC')

    else:
        env['AENV_LOCAL_DIR'] = local_dir

        # directory for file transfers to the control node,
        # typically used for storing backup files
        env['AENV_BACKUP_ROOT'] = local_dir / 'backup'

        # directory for copying source files from the control node to managed nodes,
        # when no other transfer methods like git-https are conveniently available
        env['AENV_LOCAL_SRC'] = local_dir / 'src'

        # lazy-init ANSIBLE_VAULT_PASSWORD_FILE if
        # (a) ANSIBLE_VAULT_PASSWORD_FILE is not already set
        # (b) <root>/local/vault_pass exists and is readable
        #
        # vault_pass may be a symlink to an encrypted partition,
        # but it has to be readable "now".
        # NOTE: only checking for non-broken symlinks, not readable
        #
        if 'ANSIBLE_VAULT_PASSWORD_FILE' not in env:
            vault_password_file = local_dir / 'vault_pass'

            if vault_password_file.is_file():
                env['ANSIBLE_VAULT_PASSWORD_FILE'] = vault_password_file
        # --
    # --
# --- end of main_init_env_ansible_prjroot (...) ---


def run_main():
    os_ex_ok = getattr(os, 'EX_OK', 0)

    try:
        exit_code = main(sys.argv[0], sys.argv[1:])

    except BrokenPipeError:
        for fh in [sys.stdout, sys.stderr]:
            try:
                fh.close()
            except:
                pass

        exit_code = os_ex_ok ^ 11

    except KeyboardInterrupt:
        exit_code = os_ex_ok ^ 130

    else:
        if (exit_code is None) or (exit_code is True):
            exit_code = os_ex_ok

        elif exit_code is False:
            exit_code = os_ex_ok ^ 1
    # --

    sys.exit(exit_code)
# --- end of run_main (...) ---


if __name__ == '__main__':
    run_main()
