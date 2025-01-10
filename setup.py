from setuptools import setup, find_packages

def parse_requirements(filename):
    with open(filename) as file:
        return file.read().splitlines()

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
        "flask",
        "flask-sqlalchemy",
        "flask-admin",
        "flask-login",
        "flask-wtf",
        "WTForms-SQLAlchemy",
        "python-on-whales",
        "rq"
    ],
    dependency_links=[
        "git+https://github.com/rwuthric/PyKSQL.git#egg=PyKSQL",
        "git+https://github.com/rwuthric/python-mtc2kafka.git#egg=python-mtc2kafka",
    ],
)
