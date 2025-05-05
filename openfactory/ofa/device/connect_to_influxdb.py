""" ofa InfluxDB connect command. """

import click
# from openfactory.factories import connect_devices_to_influxdb


@click.command(name='connect-influxdb')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def click_connect_influxdb(yaml_config_file):
    """
    Connects devices to InfluxDB.

    Args:
        yaml_config_file (str): Path to the YAML configuration file.
    """
    pass
    # connect_devices_to_influxdb(db.session, yaml_config_file)
