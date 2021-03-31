#!/usr/bin/env python

from setuptools import setup
import os


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='oemoflex',
    version='0.0.0',
    description='',
    long_description=read('README.md'),
    packages=['oemoflex'],
    install_requires=[
        'pyyaml',
        'pandas',
        'pyomo<5.6.9',
        'pyutilib<6.0.0',
        'oemof.tabular @ git+https://git@github.com/oemof/oemof-tabular@dev#egg=oemof.tabular',
        'frictionless',
    ],
)
