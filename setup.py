from setuptools import setup, find_packages

setup(
    name="traders-parse",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'requests',
        'dacite',
    ],
) 