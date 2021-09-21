.. _overview_label:

~~~~~~~~
Overview
~~~~~~~~

oemoflex is a flexible model structure for creating and analysing multi-regional sector-integrated
energysystem models featuring many flexibility options.

oemoflex defines **schemas for tabular data** amd makes it easy to create datapackages that represent
energy systems that can be optimized with oemof.solph.

The schemas :file:`oemoflex.model.facade_attrs`
:file:`oemoflex.modelbusses.yml`
:file:`components_attrs.yml`
:file:`foreign_keys.yml`

Custom-defined components can be passed.

**Build datapackages** EnergyDataPackage.setup_default

**parametrize** EnergyDataPackage.parametrize

**validate** EnergyDataPackage.validate

**stack** **unstack**

It also helps to **postprocess** the results so that you can focus on your main tasks
of modeling: Finding good data and drawing assumptions to build meaningful scenarios and interpret
them. ResultsDataPackage(es)
