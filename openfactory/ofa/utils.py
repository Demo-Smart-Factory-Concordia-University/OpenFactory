import os
from openfactory.utils import find_yaml_files
from openfactory.models.user_notifications import user_notify


def process_yaml_files(path, dry_run, action_func, action_name="process", pattern='app_*.yml'):
    """ Generic processor for YAML files (single or folder) with dry-run support """
    if os.path.isfile(path):
        if dry_run:
            user_notify.info(f"[DRY-RUN] {path} would be {action_name}.")
        else:
            action_func(path)

    elif os.path.isdir(path):
        yaml_files = find_yaml_files(path, pattern=pattern)

        if not yaml_files:
            user_notify.fail(f"No YAML files found in '{path}'.")
            return

        for yaml_file in yaml_files:
            if dry_run:
                user_notify.info(f"[DRY-RUN] {yaml_file} would be {action_name}.")
            else:
                user_notify.info(f"[INFO] {action_name.capitalize()} from '{yaml_file}' ...")
                action_func(yaml_file)
