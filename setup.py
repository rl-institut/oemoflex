#!/usr/bin/env python

from setuptools import find_packages, setup
import os


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="oemoflex",
    version="0.0.0",
    description="A flexible model structure for creating and analysing multi-regional"
    "sector-integrated energysystem models featuring many flexibility options",
    long_description=read("README.md"),
    packages=find_packages(),
    package_data={
        "oemoflex.model": [
            "*.yml",
            "*.csv",
            os.path.join("component_attrs", "*.csv"),
        ],
    },
    package_dir={"oemoflex": "oemoflex"},
    install_requires=[
        "pyyaml",
        "pandas",
        "pyomo<5.6.9",
        "pyutilib<6.0.0",
        "oemof.tabular @ git+https://git@github.com/oemof/oemof-tabular@dev#egg=oemof.tabular",
        "frictionless",
    ],
)
