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

Define **schemas for tabular data packages** that describe energy systems. The schemas for different
types of components are defined in
`facade_attrs <https://github.com/rl-institut/oemoflex/tree/dev/oemoflex/model/facade_attrs>`_.
The files `component_attrs.yml <https://github.com/rl-institut/oemoflex/blob/dev/oemoflex/model/component_attrs.yml>`_
and `busses.yml <https://github.com/rl-institut/oemoflex/blob/dev/oemoflex/model/busses.yml>`_
define the available components and busses.

**Setup datapackages.** You can create data packages for an energy system by passing the lists of
:attr:`regions`, :attr:`links`, :attr:`busses` and :attr:`components` that you want to model.
Custom-defined busses and components can be passed as dictionaries :attr:`bus_attrs_update` and
:attr:`component_attrs_update`.

**Infer metadata:** Metadata that describe the tables and their foreign key relations in form of a
:file:`datapackage.json` are a requirement for oemof.tabular to load the datapackage as an
:class:`EnergySystem`. Foreign key relations are defined in
`foreign_keys.yml <https://github.com/rl-institut/oemoflex/blob/dev/oemoflex/model/foreign_keys.yml>`_.
When adding custom-defined components and busses, a dictionary with :attr:`foreign_keys_update`
can be passed.

**Parametrizes data packages.** EnergyDataPackage.parametrize

**Validate data schemas.** EnergyDataPackage.validate

**Postprocess results.**

**Plot results.**
