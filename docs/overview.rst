.. _overview_label:

~~~~~~~~
Overview
~~~~~~~~

oemoflex is a flexible model structure for creating and analysing multi-regional sector-integrated
energysystem models featuring many flexibility options.

In particular, oemoflex makes it easy to create datapackages that represent
energy systems that can be optimized with oemof.solph. You want to focus on the main tasks of
modeling: Find suitable data and make assumptions to build meaningful scenarios and interpret them.
To support you with that, oemoflex helps you to:


Define schemas for tabular data packages
========================================

The schemas describe the energy systems and are defined for different
types of components in
`facade_attrs <https://github.com/rl-institut/oemoflex/tree/dev/oemoflex/model/facade_attrs>`_.
The files `component_attrs.yml <https://github.com/rl-institut/oemoflex/blob/dev/oemoflex/model/component_attrs.yml>`_
and `busses.yml <https://github.com/rl-institut/oemoflex/blob/dev/oemoflex/model/busses.yml>`_
define the available components and busses.


Setup datapackages
==================

You can create data packages for an energy system by passing the lists of
regions, links, busses and components that you want to model to
:meth:`EnergyDataPackage.setup_default <oemoflex.model.datapackage.EnergyDataPackage.setup_default>`.
Custom-defined busses and components can be passed as dictionaries :attr:`bus_attrs_update` and
:attr:`component_attrs_update`.


Infer metadata
==============

Metadata that describe the tables and their foreign key relations in form of a
:file:`datapackage.json` are a requirement for oemof.tabular to load the datapackage as an
:class:`oemof.solph.EnergySystem`. To infer metadata for an existing data package, use
:meth:`EnergyDataPackage.infer_metadata <oemoflex.model.datapackage.EnergyDataPackage.infer_metadata>`.
Foreign key relations are defined in
`foreign_keys.yml <https://github.com/rl-institut/oemoflex/blob/dev/oemoflex/model/foreign_keys.yml>`_.
When adding custom-defined components and busses, a dictionary with :attr:`foreign_keys_update`
can be passed.


Parametrize data packages
=========================

Parametrize the EnergyDataPackage with
:meth:`EnergyDataPackage.parametrize <oemoflex.model.datapackage.EnergyDataPackage.parametrize>` to
set the values of parameters for all components.

.. TODO: Not implemented yet. **Validate data schemas.** EnergyDataPackage.validate

.. TODO: Not implemented yet. **Create variations.** of existing EnergyDataPackages.


Postprocess results
===================

Results of an oemof.solph optimisation can be postprocessed and saved as
a :class:`ResultsDataPackage <oemoflex.model.datapackage.ResultsDataPackage>`.

Postprocessed results are stored as `csv` files in the following directory structure:

.. code-block::

    postprocessed
    ├── sequences
    │     ├── bus
    │     ├── by_variable
    │     ├── component
    ├── objective.csv
    ├── scalars.csv

The directory `sequences` contains time series of flows. In directory `bus` flows from and to each bus can be found.
The `by_variable` directory contains `csv` files with time series of all optimized variables.
In `component` there is a `csv` file for each component which contains the time series of flows from and to it.

The result of the objective function of the optimized energy system is stored in `objective.csv`.
The file `scalars.csv` includes the results aggregated over the optimisations time horizon.
These include summed flows, storage losses, transmission losses, invested capacity, invested storage capacity,
invested capacity costs, invested storage capacity costs, summed carrier costs, and summed marginal costs.


Plot results
============

Plot methods help to visualize and understand the results of a scenario. Read the
API documentation of :mod:`oemoflex.tools.plots <oemoflex.tools.plots>` for more details.
