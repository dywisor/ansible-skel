# lazy makefile that will generate set-defaults task files
# NOTE: you still have to add import_tasks: defaults.yml to the main.yml

S := $(CURDIR)
O := $(CURDIR)

AENV_SKEL_SHAREDIR ?=

X_GEN_TASK = awk -f $(AENV_SKEL_SHAREDIR)/helpers/gen-task-set-defaults

_xsort = LC_COLLATE=C sort

# find or custom rwildcard()
_DEFAULTS_VARS_FILES := $(sort $(shell LC_COLLATE=C find $(S) -type f -path "*/defaults/main.yml" -print))
_DEFAULTS_TASKS_FROM_FILES := $(patsubst %/defaults/main.yml,%/tasks/defaults.yml,$(_DEFAULTS_VARS_FILES))

_DEFAULTS_VARS_DIRS  := $(sort $(shell LC_COLLATE=C find $(S) -type d -not -empty -path "*/defaults/main" -print))
_DEFAULTS_TASKS_FROM_DIRS  := $(patsubst %/defaults/main,%/tasks/defaults.yml,$(_DEFAULTS_VARS_DIRS))

all: set-defaults

set-defaults: $(sort $(_DEFAULTS_TASKS_FROM_FILES) $(_DEFAULTS_TASKS_FROM_DIRS))

$(_DEFAULTS_TASKS_FROM_FILES): %/tasks/defaults.yml: %/defaults/main.yml
	mkdir -p -- $(@D)
	$(X_GEN_TASK) < $(<) > $(@).make_tmp
	mv -f -- $(@).make_tmp $(@)

$(_DEFAULTS_TASKS_FROM_DIRS): %/tasks/defaults.yml: %/defaults/main
	mkdir -p -- $(@D)
	cat -- $(sort $(wildcard $(<)/*.yml)) /dev/null | $(X_GEN_TASK) > $(@).make_tmp
	mv -f -- $(@).make_tmp $(@)

.PHONY: all set-defaults
