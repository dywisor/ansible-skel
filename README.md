Scripts and base layout for Ansible playbook/roles collections.

There's no formal design specification,
but here are a few choices that I try to adhere to:

* Split (topic) roles into smaller sub roles,
  e.g. ``mariadb/install``, ``mariadb/create-users``

  It suits me better for reusing roles
  and quickly testing specific parts.

* Use per-OS subdirectories in e.g. ``roles/``,
  e.g. ``roles/debian``, ``roles/openbsd``.

* For generic roles (Unix/Linux, that is),
  use subdirectories below ``roles/generic/``.

  This design decision *may* result in having tasks
  for a specific topic in both ``roles/generic/<topic>``
  and ``roles/<os>/<topic>``.

  Having a few *which-os-is-it?* checks below ``roles/generic/``
  could be OK, but distro-specific blocks should not be put there.

* Put defaults and handlers below ``includes/``,
  organized in a per-topic structure, e.g. ``debian/common``, ``debian/nginx``

  Those are loaded in rules in ``<role>/meta/main.yml``:

  ```
  ---

  dependencies:
    - includes/generic/common
    - includes/debian/common
    - ...

  ...
  ```

* Always use directories for ``group_vars`` and ``host_vars``,
  prefix files with a 2-digit number for sorting in lexicographic order.

  Example: ``group_vars/all/20-proxy.yml``

* Prefer YAML over JSON / ini.

* Define tags:

  - by function:

    - ``does_install``
    - ``does_config``
    - ``does_user_mgmt``
    - ...
  
  - by OS, ``os_<name> or os_any``

  - by product:

    - ``product_openssh``
    - ``product_nginx``
    - ...

  - for tasks/roles that should be run regardless of user-requested tags:

    - ``always``

* Use double quotes for var expansion and single quotes inside

  ```
  value: "{{ var['key'] }}"
  ```

* Use ``true``/``false`` for booleans

* Create a metadata.yml file for each topic / role, ``roles/<topic>/metadata.yml``,
  that specifies which other roles must or should be run before/after this role.

  It's not implemented in any script so far, but the metadata.yml file
  could be used for generating playbooks and whatnot in future.
  Sub roles inherit the topics and dependencies of their respective parents.

  ```
  ---
  name:   ""
  topics: []

  dependencies:
    requires: []
    after:    []
    before:   []
  ...
  ```
