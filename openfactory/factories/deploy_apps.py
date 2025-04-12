from openfactory import OpenFactoryManager
from openfactory.schemas.apps import get_apps_from_config_file
from openfactory.models.user_notifications import user_notify


def deploy_apps_from_config_file(yaml_config_file, ksqlClient):
    """
    Deploy OpenFactory applications based on a yaml configuration file
    """

    # load yaml description file
    apps = get_apps_from_config_file(yaml_config_file)
    if apps is None:
        return

    ofa = OpenFactoryManager(ksqlClient=ksqlClient)

    for app_name, app in apps.items():
        user_notify.info(f"{app_name}:")
        if app['uuid'] in ofa.applications_uuid():
            user_notify.info(f"Application {app['uuid']} exists already and was not deployed")
            continue

        ofa.deploy_openfactory_application(app)
