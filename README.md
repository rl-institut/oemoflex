# oemoflex

oemoflex is a flexible model structure for creating and analysing multi-regional sector-integrated 
energysystem models featuring many flexibility options.

oemoflex makes it easy to create datapackages that represent energy systems that can be optimized
with oemof.solph. It also helps to postprocess the results so that you can focus on your main tasks
of modeling: Finding good data and drawing assumptions to build meaningful scenarios and interpret
them.

The core parts of oemoflex have been originally developed in the project FlexMex. Its main
application is currently within the energy system model [oemof-B3](https://oemof-b3.readthedocs.io/)

## Getting started

## Installation

You can install oemoflex in your environment for developing with pip:

    pip install -e <path-to-oemoflex>

## Usage

Have a look at the examples to see how to create an EnergyDataPackage by specifying the components,
busses, regions and links, how to parametrize it and how to pass it to oemof.solph to solve the
optimization problem.

## Docs

Online documentation is hosted by readthedocs and can be found 
[here](https://oemoflex.readthedocs.io/en/latest/). The docs are currently under construction. 

To build the docs simply go to the `docs` folder

    cd docs

Install the requirements

    pip install -r docs_requirements.txt

and run

    make html

The output will then be located in `docs/_build/html` and can be opened with your favorite browser
