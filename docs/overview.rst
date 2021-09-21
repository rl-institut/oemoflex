.. _overview_label:

~~~~~~~~
Overview
~~~~~~~~

oemoflex is a flexible model structure for creating and analysing multi-regional sector-integrated
energysystem models featuring many flexibility options.

oemoflex makes it easy to create datapackages that represent
energy systems that can be optimized with oemof.solph. In detail, oemoflex:

* defines **schemas for tabular data packages** that describe energy systems.

  The schemas for different types of components are defined here :file:`oemoflex.model.facade_attrs`.
  The files :file:`oemoflex.model.components_attrs.yml` and :file:`oemoflex.model.busses.yml` define
  the available components and busses.

* **builds datapackages**

  EnergyDataPackage.setup_default
  :attr:`regions`, :attr:`links`, :attr:`busses` and :attr:`components`.

  Custom-defined busses and components can be passed as :attr:`bus_attrs_update` and
  :attr:`component_attrs_update`.

* **infers metadata**
  Foreign key relations are defined in :file:`oemoflex.model.foreign_keys.yml`

* **parametrizes data packages** EnergyDataPackage.parametrize

* **validates data schemas** EnergyDataPackage.validate

* helps **postprocessing** the results so that you can focus on your main tasks of modeling: Finding
  good data and drawing assumptions to build meaningful scenarios and interpret them.
  ResultsDataPackage(es)

* provides functions for **plotting** results.