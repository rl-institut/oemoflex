import pandas as pd
import numpy as np
from oemof.network import Node
from oemof.solph import Source, Sink, Bus, Flow, Model, EnergySystem
from oemof.outputlib import processing
from oemoflex import facades as oemoflex_facades
from oemof.tabular import facades as tabular_facades

# Set up an energy system model
solver = "cbc"
periods = 100
datetimeindex = pd.date_range("1/1/2019", periods=periods, freq="H")
demand_timeseries = np.zeros(periods)
demand_timeseries[-5:] = 1
heat_feedin_timeseries = np.zeros(periods)
heat_feedin_timeseries[:10] = 1


class TestCases:
    def prepare_es(self):
        self.energysystem = EnergySystem(timeindex=datetimeindex)

        Node.registry = self.energysystem

        bus_heat = Bus(label="bus_heat")

        Source(
            label="heat_source",
            outputs={
                bus_heat: Flow(
                    nominal_value=1, fixed=True, actual_value=heat_feedin_timeseries
                )
            },
        )

        Source(
            label="shortage", outputs={bus_heat: Flow(variable_costs=1e6)}
        )

        Sink(label="excess", inputs={bus_heat: Flow()})

        Sink(
            label="heat_demand",
            inputs={
                bus_heat: Flow(
                    nominal_value=1, fixed=True, actual_value=demand_timeseries
                )
            },
        )

        return bus_heat

    def run_model(self):
        # Create and solve the optimization model
        optimization_model = Model(self.energysystem)

        optimization_model.solve(
            solver=solver, solve_kwargs={"tee": False, "keepfiles": False}
        )

        # Get results
        results = processing.results(optimization_model)

        # string_results = processing.convert_keys_to_strings(results)
        # sequences = {k: v["sequences"] for k, v in string_results.items()}
        # df = pd.concat(sequences, axis=1)

        return results

    def test_storage_investment(self):

        bus_heat = self.prepare_es()

        storage = tabular_facades.Storage(
            label="facades_Storage",
            carrier="heat",
            tech="storage",
            bus=bus_heat,
            efficiency=0.9,
            expandable=True,
            storage_capacity=0,  # Initially installed storage capacity
            storage_capacity_potential=10,  # Potential for investment in storage capacity
            storage_capacity_cost=2,
            capacity=1,
            # Reduces the inflow capacity in respect to a non restricted capacity_potential.
            # As a result the missing capacity is added on the outflow capacity (?)
            capacity_cost=0,  # Doesn't do anything?
            capacity_potential=0.9,
        )

        results = self.run_model()

        capacity_in = results[bus_heat, storage]["scalars"]["invest"]
        capacity_out = results[storage, bus_heat]["scalars"]["invest"]
        storage_capacity = results[storage, None]["scalars"]["invest"]

        assert capacity_in == capacity_out

    def test_asymemtric_storage_investment(self):

        bus_heat = self.prepare_es()

        storage = oemoflex_facades.AsymmetricStorage(
            label="oemoflex_Storage",
            carrier="heat",
            tech="storage",
            type="storage",
            bus=bus_heat,
            efficiency=0.9,
            expandable=True,
            storage_capacity=0,  # Initially installed storage capacity
            storage_capacity_potential=10,  # Invested storage capacity
            storage_capacity_cost=2,
            capacity=0.03,
            # Reduces the inflow capacity in respect to a non restricted capacity_potential.
            # As a result the missing capacity is added on the outflow capacity (?)
            capacity_cost=0,  # Doesn't do anything. -> capacity_cost_charge instead
            capacity_cost_charge=0,
            capacity_cost_discharge=0,  # Doesn't do anything?
            # capacity_potential=0,
            # Doesn't do anything. -> capacity_potential_charge and capacity_potential_discharge
            # instead
            capacity_potential_charge=0.9,
            capacity_potential_discharge=0.9,
        )

        results = self.run_model()

        capacity_in = results[bus_heat, storage]["scalars"]["invest"]
        capacity_out = results[storage, bus_heat]["scalars"]["invest"]
        storage_capacity = results[storage, None]["scalars"]["invest"]
