# install in your virtualenv with
# pip install --editable .

from setuptools import setup

setup(
    name='ofa',
    version='0.1.0',
    py_modules=['ofa'],
    install_requires=[
        'Click',
    ],
    entry_points={
        'console_scripts': [
            'ofa = ofa:cli',
        ],
    },
)
