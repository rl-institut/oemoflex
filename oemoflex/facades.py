from oemof import solph
from oemof.solph import sequence, Bus, Sink, Flow, Investment
from oemof.solph.components import GenericStorage, ExtractionTurbineCHP

from oemof.tabular import facades
from oemof.tabular.facades import Link, TYPEMAP


class Source(solph.Source):
    r"""
    Supplement Source with carrier and tech properties to work with labeling in postprocessing

    Needed for Source subnodes in
    * ReservoirWithPump: inflow subnode
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.carrier = kwargs.get('carrier', None)
        self.tech = kwargs.get('tech', None)


class Transformer(solph.Transformer):
    r"""
    Supplement Transformer with carrier and tech properties to work with labeling in postprocessing

    Needed for Transformer subnodes in
    * ReservoirWithPump: pump subnode
    * Bev: vehicle_to_grid subnode
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.carrier = kwargs.get('carrier', None)
        self.tech = kwargs.get('tech', None)


class Facade(facades.Facade):

    def _nominal_value(self):
        """ Returns None if self.expandable ist True otherwise it returns
        the capacities
        """
        if self.expandable is True:
            return None

        if isinstance(self, Link):
            return {
                "from_to": self.from_to_capacity,
                "to_from": self.to_from_capacity}

        if isinstance(self, AsymmetricStorage):
            return {
                "charge": self.capacity_charge,
                "discharge": self.capacity_discharge}

        return self.capacity


class AsymmetricStorage(GenericStorage, Facade):

    def __init__(self, *args, **kwargs):

        super().__init__(
            _facade_requires_=["bus", "carrier", "tech"], *args, **kwargs
        )

        self.storage_capacity = kwargs.get("storage_capacity", 0)

        self.capacity_charge = kwargs.get("capacity_charge", 0)
        self.capacity_discharge = kwargs.get("capacity_discharge", 0)

        self.capacity_cost_charge = kwargs.get("capacity_cost_charge")
        self.capacity_cost_discharge = kwargs.get("capacity_cost_discharge")

        self.storage_capacity_cost = kwargs.get("storage_capacity_cost")

        self.storage_capacity_potential = kwargs.get(
            "storage_capacity_potential", float("+inf")
        )

        self.capacity_potential_charge = kwargs.get(
            "capacity_potential_charge", float("+inf")
        )

        self.capacity_potential_discharge = kwargs.get(
            "capacity_potential_discharge", float("+inf")
        )

        self.expandable = bool(kwargs.get("expandable", False))

        self.marginal_cost = kwargs.get("marginal_cost", 0)

        self.efficiency_charge = kwargs.get("efficiency_charge", 1)

        self.efficiency_discharge = kwargs.get("efficiency_discharge", 1)

        self.input_parameters = kwargs.get("input_parameters", {})

        self.output_parameters = kwargs.get("output_parameters", {})

        self.build_solph_components()

    def build_solph_components(self):

        self.nominal_storage_capacity = self.storage_capacity

        self.inflow_conversion_factor = sequence(self.efficiency_charge)

        self.outflow_conversion_factor = sequence(self.efficiency_discharge)

        # self.investment = self._investment()
        if self.expandable is True:
            if any([self.capacity_cost_charge,
                    self.capacity_cost_discharge,
                    self.storage_capacity_cost]) is None:
                msg = (
                    "If you set `expandable` to True you need to set "
                    "attribute `storage_capacity_cost`,"
                    "`capacity_cost_charge` and `capacity_cost_discharge` of component {}!"
                )
                raise ValueError(msg.format(self.label))

            self.investment = Investment(
                ep_costs=self.storage_capacity_cost,
                maximum=getattr(self, "storage_capacity_potential", float("+inf")),
                minimum=getattr(self, "minimum_storage_capacity", 0),
                existing=getattr(self, "storage_capacity", 0),
            )

            fi = Flow(
                investment=Investment(
                    ep_costs=self.capacity_cost_charge,
                    maximum=getattr(self, "capacity_potential_charge", float("+inf")),
                    existing=getattr(self, "capacity_charge", 0),
                ),
                **self.input_parameters
            )

            fo = Flow(
                investment=Investment(
                    ep_costs=self.capacity_cost_discharge,
                    maximum=getattr(self, "capacity_potential_discharge", float("+inf")),
                    existing=getattr(self, "capacity_discharge", 0),
                ),
                # Attach marginal cost to Flow out
                variable_costs=self.marginal_cost,
                **self.output_parameters
            )
            # required for correct grouping in oemof.solph.components
            self._invest_group = True

        else:
            fi = Flow(
                nominal_value=self._nominal_value()["charge"], **self.input_parameters
            )
            fo = Flow(
                nominal_value=self._nominal_value()["discharge"],
                # Attach marginal cost to Flow out
                variable_costs=self.marginal_cost,
                **self.output_parameters
            )

        self.inputs.update({self.bus: fi})

        self.outputs.update({self.bus: fo})

        self._set_flows()


class Bev(GenericStorage, Facade):
    r""" A fleet of Battery electric vehicles with vehicle-to-grid.

    Note that the investment option is not available for this facade at
    the current development state.

    Parameters
    ----------
    bus: oemof.solph.Bus
        An oemof bus instance where the storage unit is connected to.
    storage_capacity: numeric
        The total storage capacity of the vehicles (e.g. in MWh)
    capacity: numeric
        Total charging/discharging capacity of the vehicles.
    availability : array-like
        Ratio of available capacity for charging/vehicle-to-grid due to
        grid connection.
    drive_power : array-like
        Profile of the load of the fleet through driving relative amount.
    amount : numeric
        Total amount of energy consumed by driving. The drive_power profile
        will be scaled by this number.
    efficiency_charging: numeric
        Efficiency of charging the batteries, default: 1
    efficiency_discharging: numeric
        Efficiency of discharging the batteries, default: 1
    efficiency_v2g: numeric
        Efficiency of vehicle-to-grid, default: 1
    min_storage_level : array-like
        Profile of minimum storage level.
    max_storage_level : array-like
        Profile of maximum storage level.
    input_parameters: dict
        Dictionary to specify parameters on the input edge. You can use
        all keys that are available for the  oemof.solph.network.Flow class.
    output_parameters: dict
        see: input_parameters


    The vehicle fleet is modelled as a storage together with an internal sink with
    fixed flow:

    .. math::

        x^{level}(t) =
        x^{level}(t-1) \cdot (1 - c^{loss\_rate}(t))
        + c^{efficiency\_charging}(t) \cdot  x^{flow, in}(t)
        - \frac{x^{drive\_power}(t)}{c^{efficiency\_discharging}(t)}
        - \frac{x^{flow, v2g}(t)}
               {c^{efficiency\_discharging}(t) \cdot c^{efficiency\_v2g}(t)}
        \qquad \forall t \in T

    Note
    ----
    As the Bev is a sub-class of `oemof.solph.GenericStorage` you also
    pass all arguments of this class.

    The concept is similar to the one described in the following publications with the difference
    that uncontrolled charging is not (yet) considered.

    Wulff, N., Steck, F., Gils, H. C., Hoyer-Klick, C., van den Adel, B., & Anderson, J. E. (2020).
    Comparing power-system and user-oriented battery electric vehicle charging representation and
    its implications on energy system modeling. Energies, 13(5). https://doi.org/10.3390/en13051093

    Diego Luca de Tena Costales. (2014).
    Large Scale Renewable Power Integration with Electric Vehicles. https://doi.org/10.04.2014

    Examples
    --------
    Basic usage example of the Bev class with an arbitrary selection of
    attributes.

    >>> from oemof import solph
    >>> from oemof.tabular import facades
    >>> my_bus = solph.Bus('my_bus')
    >>> my_bev = Bev(
    ...     name='my_bev',
    ...     bus=el_bus,
    ...     carrier='electricity',
    ...     tech='bev',
    ...     storage_capacity=1000,
    ...     capacity=50,
    ...     availability=[0.8, 0.7, 0.6],
    ...     drive_power=[0.3, 0.2, 0.5],
    ...     amount=450,
    ...     loss_rate=0.01,
    ...     initial_storage_level=0,
    ...     min_storage_level=[0.1, 0.2, 0.15],
    ...     max_storage_level=[0.9, 0.95, 0.92],
    ...     efficiency=0.93
    ...     )

    """

    def __init__(self, *args, **kwargs):

        kwargs.update(
            {
                "_facade_requires_": [
                    "bus",
                    "carrier",
                    "tech",
                    "availability",
                    "drive_power",
                    "amount",
                ]
            }
        )
        super().__init__(*args, **kwargs)

        self.storage_capacity = kwargs.get("storage_capacity")

        self.capacity = kwargs.get("capacity")

        self.efficiency_charging = kwargs.get("efficiency_charging", 1)

        self.efficiency_discharging = kwargs.get("efficiency_discharging", 1)

        self.efficiency_v2g = kwargs.get("efficiency_v2g", 1)

        self.profile = kwargs.get("profile")

        self.marginal_cost = kwargs.get("marginal_cost", 0)

        self.input_parameters = kwargs.get("input_parameters", {})

        self.output_parameters = kwargs.get("output_parameters", {})

        self.expandable = bool(kwargs.get("expandable", False))

        self.build_solph_components()

    def build_solph_components(self):

        self.nominal_storage_capacity = self.storage_capacity

        self.inflow_conversion_factor = sequence(self.efficiency_charging)

        self.outflow_conversion_factor = sequence(self.efficiency_discharging)

        if self.expandable:
            raise NotImplementedError(
                "Investment for bev class is not implemented."
            )

        internal_bus = Bus(label=self.label + "-internal_bus")

        vehicle_to_grid = Transformer(
            carrier=self.carrier,
            tech=self.tech,
            label=self.label + '-vehicle_to_grid',
            inputs={internal_bus: Flow()},
            outputs={
                self.bus: Flow(
                    nominal_value=self.capacity,
                    max=self.availability,
                    variable_costs=self.marginal_cost,
                    **self.output_parameters
                )
            },
            conversion_factors={internal_bus: self.efficiency_v2g},
        )

        drive_power = Sink(
            label=self.label + "-drive_power",
            inputs={
                internal_bus: Flow(nominal_value=self.amount,
                                   actual_value=self.drive_power,
                                   fixed=True)
            },
        )

        self.inputs.update(
            {
                self.bus: Flow(
                    nominal_value=self.capacity,
                    max=self.availability,
                    **self.input_parameters
                )
            }
        )

        self.outputs.update(
            {
                internal_bus: Flow()
            }
        )

        self.subnodes = (internal_bus, drive_power, vehicle_to_grid)


class ReservoirWithPump(GenericStorage, Facade):
    r""" A Reservoir storage unit, that is initially half full.

    Note that the investment option is not available for this facade at
    the current development state.

    Parameters
    ----------
    bus: oemof.solph.Bus
        An oemof bus instance where the storage unit is connected to.
    storage_capacity: numeric
        The total storage capacity of the storage (e.g. in MWh)
    capacity_turbine: numeric
        Installed production capacity of the turbine installed at the
        reservoir
    capacity_pump: numeric
        Installed pump capacity
    efficiency_turbine: numeric
        Efficiency of the turbine converting inflow to electricity
        production, default: 1
    efficiency_pump: numeric
        Efficiency of the turbine converting inflow to electricity
        production, default: 1
    profile: array-like
        Relative inflow profile of inflow into the storage, ratio of turbine power
    input_parameters: dict
        Dictionary to specifiy parameters on the input edge. You can use
        all keys that are available for the  oemof.solph.network.Flow class.
    output_parameters: dict
        see: input_parameters


    The reservoir is modelled as a storage with a constant inflow:

    .. math::

        x^{level}(t) =
        x^{level}(t-1) \cdot (1 - c^{loss\_rate}(t))
        + x^{profile}(t) - \frac{x^{flow, out}(t)}{c^{efficiency}(t)}
        \qquad \forall t \in T

    .. math::
        x^{level}(0) = 0.5 \cdot c^{capacity}

    The inflow is bounded by the exogenous inflow profile. Thus if the inflow
    exceeds the maximum capacity of the storage, spillage is possible by
    setting :math:`x^{profile}(t)` to lower values.

    .. math::
        0 \leq x^{profile}(t) \leq c^{profile}(t) \qquad \forall t \in T


    The spillage of the reservoir is therefore defined by:
    :math:`c^{profile}(t) - x^{profile}(t)`.

    Note
    ----
    As the ReservoirWithPump is a sub-class of `oemof.solph.GenericStorage` you also
    pass all arguments of this class.


    Examples
    --------
    Basic usage examples of the GenericStorage with a random selection of
    attributes. See the Flow class for all Flow attributes.

    >>> from oemof import solph
    >>> from oemof.tabular import facades
    >>> my_bus = solph.Bus('my_bus')
    >>> my_reservoir = ReservoirWithPump(
    ...     label='my_reservoir',
    ...     bus=my_bus,
    ...     carrier='water',
    ...     tech='reservoir with pump',
    ...     storage_capacity=1000,
    ...     capacity_turbine=50,
    ...     capacity_pump=20,
    ...     profile=[0.1, 0.2, 0.7],
    ...     loss_rate=0.01,
    ...     initial_storage_level=0,
    ...     max_storage_level = 0.9,
    ...     efficiency_turbine=0.93
    ...     efficiency_pump=0.8)

    """

    def __init__(self, *args, **kwargs):
        kwargs.update(
            {
                "_facade_requires_": [
                    "bus",
                    "carrier",
                    "tech",
                    "profile",
                    "capacity_pump",
                    "capacity_turbine",
                    "storage_capacity",
                    "efficiency_turbine",
                    "efficiency_pump",
                ]
            }
        )
        super().__init__(*args, **kwargs)

        self.marginal_cost = kwargs.get("marginal_cost", 0)

        self.input_parameters = kwargs.get("input_parameters", {})

        self.output_parameters = kwargs.get("output_parameters", {})

        self.expandable = bool(kwargs.get("expandable", False))

        self.build_solph_components()

    def build_solph_components(self):

        self.nominal_storage_capacity = self.storage_capacity

        self.outflow_conversion_factor = sequence(self.efficiency_turbine)

        if self.expandable:
            raise NotImplementedError(
                "Investment for reservoir class is not implemented."
            )

        internal_bus = Bus(label=self.label + '-internal_bus')

        pump = Transformer(
            label=self.label + '-pump',
            inputs={
                self.bus: Flow(
                    nominal_value=self.capacity_pump,
                    **self.input_parameters
                )
            },
            outputs={internal_bus: Flow()},
            conversion_factors={internal_bus: self.efficiency_pump},
            carrier=self.carrier,
            tech=self.tech
        )

        inflow = Source(
            label=self.label + "-inflow",
            outputs={
                internal_bus: Flow(
                    nominal_value=self.capacity_turbine,
                    max=self.profile,
                    fixed=False
                )
            },
            carrier=self.carrier,
            tech=self.tech
        )

        self.inputs.update(
            {
                internal_bus: Flow()
            }
        )

        self.outputs.update(
            {
                self.bus: Flow(
                    nominal_value=self.capacity_turbine,
                    variable_costs=self.marginal_cost,
                    **self.output_parameters
                )
            }
        )

        self.subnodes = (inflow, internal_bus, pump)


class ExtractionTurbine(ExtractionTurbineCHP, Facade):  # pylint: disable=too-many-ancestors
    r""" Combined Heat and Power (extraction) unit with one input and
    two outputs.

    Parameters
    ----------
    electricity_bus: oemof.solph.Bus
        An oemof bus instance where the chp unit is connected to with its
        electrical output
    heat_bus: oemof.solph.Bus
        An oemof bus instance where the chp unit is connected to with its
        thermal output
    fuel_bus:  oemof.solph.Bus
        An oemof bus instance where the chp unit is connected to with its
        input
    carrier_cost: numeric
        Cost per unit of used input carrier
    capacity: numeric
        The electrical capacity of the chp unit (e.g. in MW) in full extraction
        mode.
    electric_efficiency:
        Electrical efficiency of the chp unit in full backpressure mode
    thermal_efficiency:
        Thermal efficiency of the chp unit in full backpressure mode
    condensing_efficiency:
        Electrical efficiency if turbine operates in full extraction mode
    marginal_cost: numeric
        Marginal cost for one unit of produced electrical output
        E.g. for a powerplant:
        marginal cost =fuel cost + operational cost + co2 cost (in Euro / MWh)
        if timestep length is one hour.
    capacity_cost: numeric
        Investment costs per unit of electrical capacity (e.g. Euro / MW) .
        If capacity is not set, this value will be used for optimizing the
        chp capacity.
    expandable: boolean
        True, if capacity can be expanded within optimization. Default: False.


    The mathematical description is derived from the oemof base class
    `ExtractionTurbineCHP <https://oemof.readthedocs.io/en/
    stable/oemof_solph.html#extractionturbinechp-component>`_ :

    .. math::
        x^{flow, carrier}(t) =
        \frac{x^{flow, electricity}(t) + x^{flow, heat}(t) \
        \cdot c^{beta}(t)}{c^{condensing\_efficiency}(t)}
        \qquad \forall t \in T

    .. math::
        x^{flow, electricity}(t)  \geq  x^{flow, thermal}(t) \cdot
        \frac{c^{electrical\_efficiency}(t)}{c^{thermal\_efficiency}(t)}
        \qquad \forall t \in T

    where :math:`c^{beta}` is defined as:

     .. math::
        c^{beta}(t) = \frac{c^{condensing\_efficiency}(t) -
        c^{electrical\_efficiency(t)}}{c^{thermal\_efficiency}(t)}
        \qquad \forall t \in T

    **Ojective expression** for operation includes marginal cost and/or
    carrier costs:

        .. math::

            x^{opex} = \sum_t (x^{flow, out}(t) \cdot c^{marginal\_cost}(t)
            + x^{flow, carrier}(t) \cdot c^{carrier\_cost}(t))


    Examples
    ---------

    >>> from oemof import solph
    >>> from oemof.tabular import facades
    >>> my_elec_bus = solph.Bus('my_elec_bus')
    >>> my_fuel_bus = solph.Bus('my_fuel_bus')
    >>> my_heat_bus = solph.Bus('my_heat_bus')
    >>> my_extraction = ExtractionTurbine(
    ...     label='extraction',
    ...     carrier='gas',
    ...     tech='ext',
    ...     electricity_bus=my_elec_bus,
    ...     heat_bus=my_heat_bus,
    ...     fuel_bus=my_fuel_bus,
    ...     capacity=1000,
    ...     condensing_efficiency=[0.5, 0.51, 0.55],
    ...     electric_efficiency=0.4,
    ...     thermal_efficiency=0.35)

    """

    def __init__(self, *args, **kwargs):
        kwargs.update(
            {
                "_facade_requires_": [
                    "fuel_bus",
                    "carrier",
                    "tech",
                    "electricity_bus",
                    "heat_bus",
                    "thermal_efficiency",
                    "electric_efficiency",
                    "condensing_efficiency",
                ]
            }
        )
        super().__init__(
            conversion_factor_full_condensation={}, *args, **kwargs
        )

        self.fuel_bus = kwargs.get("fuel_bus")

        self.electricity_bus = kwargs.get("electricity_bus")

        self.heat_bus = kwargs.get("heat_bus")

        self.carrier = kwargs.get("carrier")

        self.carrier_cost = kwargs.get("carrier_cost", 0)

        self.capacity = kwargs.get("capacity")

        self.fuel_capacity = self.capacity / self.condensing_efficiency  # noqa: E501  # pylint: disable=access-member-before-definition  # done with kwargs.update()

        self.condensing_efficiency = sequence(self.condensing_efficiency)

        self.marginal_cost = kwargs.get("marginal_cost", 0)

        self.expandable = bool(kwargs.get("expandable", False))

        self.input_parameters = kwargs.get("input_parameters", {})

        self.build_solph_components()

    def build_solph_components(self):

        if self.expandable:
            raise NotImplementedError(
                "Investment for extraction class is not implemented."
            )

        self.conversion_factors.update(
            {
                self.fuel_bus: sequence(1),
                self.electricity_bus: sequence(self.electric_efficiency),
                self.heat_bus: sequence(self.thermal_efficiency),
            }
        )

        self.inputs.update(
            {
                self.fuel_bus: Flow(
                    variable_costs=self.carrier_cost,
                    nominal_value=self.fuel_capacity,
                    **self.input_parameters
                )
            }
        )

        self.outputs.update(
            {
                self.electricity_bus: Flow(
                    variable_costs=self.marginal_cost,
                ),
                self.heat_bus: Flow(),
            }
        )

        self.conversion_factor_full_condensation.update(
            {self.electricity_bus: self.condensing_efficiency}
        )


TYPEMAP.update(
    {
        "asymmetric storage": AsymmetricStorage,
        "reservoir": ReservoirWithPump,
        "bev": Bev,
        "extraction": ExtractionTurbine,
    }
)
