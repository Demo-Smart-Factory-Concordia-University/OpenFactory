from openfactory import OpenFactoryManager
from openfactory.schemas.apps import get_apps_from_config_file
from openfactory.models.user_notifications import user_notify


def shut_down_apps_from_config_file(yaml_config_file):
    """
    Shut down OpenFactory applications based on a config file
    """

    # Load yaml description file
    apps = get_apps_from_config_file(yaml_config_file)
    if apps is None:
        return

    ofa = OpenFactoryManager()
    for app_name, app in apps.items():
        user_notify.info(f"{app_name}:")
        if not app['uuid'] in ofa.applications_uuid():
            user_notify.info(f"No application {app['uuid']} deployed in OpenFactory")
            continue

        ofa.tear_down_application(app['uuid'])
