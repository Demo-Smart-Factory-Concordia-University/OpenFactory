from setuptools import setup, find_packages

def parse_requirements(filename):
    with open(filename) as file:
        return file.read().splitlines()

setup(
    name='openfactory',
    version='0.1.0',
    packages=find_packages(include=["openfactory", "openfactory.*"]),
    include_package_data=True,
    install_requires=parse_requirements('requirements.txt'),
)
