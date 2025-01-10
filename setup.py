from setuptools import setup, find_packages

setup(
    name='openfactory',
    version='0.1.0',
    packages=find_packages(include=["openfactory", "openfactory.*"]),
    include_package_data=True,
    install_requires=[
        "paramiko",
        "docker",
        "pyyaml",
        "click",
        "sqlalchemy",
        "flake8",
        "python-dotenv",
        "PyGithub",
        "fsspec",
        "influxdb-client",
        "asyncua",
        "git+https://github.com/rwuthric/PyKSQL.git",
        "git+https://github.com/rwuthric/python-mtc2kafka.git",
        # DataFabric WebApp dependencies
        "flask",
        "flask-sqlalchemy",
        "flask-admin",
        "flask-login",
        "flask-wtf",
        "WTForms-SQLAlchemy",
        "python-on-whales",
        "rq"
    ],
)
