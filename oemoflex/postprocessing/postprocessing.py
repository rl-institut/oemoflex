import pandas as pd
import numpy as np

from oemoflex.postprocessing import helper as ppu
from oemoflex.postprocessing.core import Calculation, Calculator


class SummedFlows(Calculation):
    def calculate_result(self):
        summed_flows = ppu.sum_flows(self.sequences)
        return ppu.drop_component_to_component(summed_flows, self.busses)


class Losses(Calculation):
    depends_on = {"summed_flows": SummedFlows}
    var_name = None

    def _calculate_losses(self, summed_flows):
        r"""
        Calculate losses within components as the difference of summed input
        to output.
        """
        if not self.var_name:
            raise ValueError("var_name has to be set")
        inputs = ppu.get_inputs(summed_flows, self.busses)
        outputs = ppu.get_outputs(summed_flows, self.busses)
        inputs = inputs.groupby("target").sum()
        outputs = outputs.groupby("source").sum()
        losses = inputs - outputs

        # Create MultiIndex:
        losses.index.name = "source"
        losses = losses.reset_index()
        losses["target"] = np.nan
        losses["var_name"] = self.var_name
        losses.set_index(["source", "target", "var_name"], inplace=True)
        return losses[0]  # Return Series instead of DataFrame


class StorageLosses(Losses):
    depends_on = {"summed_flows": SummedFlows}
    var_name = "storage_losses"

    def calculate_result(self):
        summed_flows_storage = ppu.filter_series_by_component_attr(
            self.dependency("summed_flows"),
            scalar_params=self.scalar_params,
            busses=self.busses,
            type="storage",
        )
        return self._calculate_losses(summed_flows_storage)


class TransmissionLosses(Losses):
    depends_on = {"summed_flows": SummedFlows}
    var_name = "transmission_losses"

    def calculate_result(self):
        summed_flows_transmission = ppu.filter_series_by_component_attr(
            self.dependency("summed_flows"),
            scalar_params=self.scalar_params,
            busses=self.busses,
            type="link",
        )
        return self._calculate_losses(summed_flows_transmission)


class Investment(Calculation):
    def calculate_result(self):
        return (
            pd.Series(dtype="object")
            if (self.scalars is None or self.scalars.empty)
            else ppu.filter_by_var_name(self.scalars, "invest")
        )


class EPCosts(Calculation):
    def calculate_result(self):
        ep_costs = ppu.filter_by_var_name(self.scalar_params, "investment_ep_costs")
        try:
            return ep_costs.unstack(2)["investment_ep_costs"]
        except KeyError:
            return pd.Series(dtype="object")


class InvestedCapacity(Calculation):
    """Collect invested (endogenous) capacity (units of power)"""

    depends_on = {"invest": Investment}

    def calculate_result(self):
        if self.dependency("invest").empty:
            return pd.Series(dtype="object")
        target_is_none = self.dependency("invest").index.get_level_values(1).isnull()
        return self.dependency("invest").loc[~target_is_none]


class InvestedStorageCapacity(Calculation):
    """Collect storage capacity (units of energy)"""

    depends_on = {"invest": Investment}

    def calculate_result(self):
        if self.dependency("invest").empty:
            return pd.Series(dtype="object")
        target_is_none = self.dependency("invest").index.get_level_values(1).isnull()
        return self.dependency("invest").loc[target_is_none]


class InvestedCapacityCosts(Calculation):
    depends_on = {"invested_capacity": InvestedCapacity, "ep_costs": EPCosts}

    def calculate_result(self):
        invested_capacity_costs = ppu.multiply_var_with_param(
            self.dependency("invested_capacity"), self.dependency("ep_costs")
        )
        if invested_capacity_costs.empty:
            return pd.Series(dtype="object")
        invested_capacity_costs.index = invested_capacity_costs.index.set_levels(
            invested_capacity_costs.index.levels[2] + "_costs", level=2
        )
        return invested_capacity_costs


class InvestedStorageCapacityCosts(Calculation):
    depends_on = {
        "invested_storage_capacity": InvestedStorageCapacity,
        "ep_costs": EPCosts,
    }

    def calculate_result(self):
        invested_storage_capacity_costs = ppu.multiply_var_with_param(
            self.dependency("invested_storage_capacity"), self.dependency("ep_costs")
        )
        if invested_storage_capacity_costs.empty:
            return pd.Series(dtype="object")
        invested_storage_capacity_costs.index = (
            invested_storage_capacity_costs.index.set_levels(
                invested_storage_capacity_costs.index.levels[2] + "_costs", level=2
            )
        )
        return invested_storage_capacity_costs


class SummedVariableCosts(Calculation):
    depends_on = {"summed_flows": SummedFlows}

    def calculate_result(self):
        variable_costs = ppu.filter_by_var_name(
            self.scalar_params, "variable_costs"
        ).unstack(2)["variable_costs"]
        variable_costs = variable_costs.loc[variable_costs != 0]
        summed_flows = self.dependency("summed_flows").unstack(2).loc[:, "flow"]

        summed_variable_costs = ppu.multiply_var_with_param(
            summed_flows, variable_costs
        )
        summed_variable_costs = ppu.set_index_level(
            summed_variable_costs, level="var_name", value="summed_variable_costs"
        )
        return summed_variable_costs


class SummedCarrierCosts(Calculation):
    """
    Calculates summed carrier costs

    An `oemof.tabular` convention: Carrier costs are on inputs, marginal costs on output
    """

    depends_on = {"summed_var_costs": SummedVariableCosts}

    def calculate_result(self):
        return ppu.get_inputs(self.dependency("summed_var_costs"), self.busses)


class SummedMarginalCosts(Calculation):
    """
    Calculates summed marginal costs

    An `oemof.tabular` convention: Carrier costs are on inputs, marginal costs on output
    """

    depends_on = {"summed_var_costs": SummedVariableCosts}

    def calculate_result(self):
        return ppu.get_outputs(self.dependency("summed_var_costs"), self.busses)


class TotalSystemCosts(Calculation):
    depends_on = {
        "icc": InvestedCapacityCosts,
        "iscc": InvestedStorageCapacityCosts,
        "scc": SummedCarrierCosts,
        "smc": SummedMarginalCosts,
    }

    def calculate_result(self):
        all_costs = pd.concat(
            [
                self.dependency("icc"),
                self.dependency("iscc"),
                self.dependency("scc"),
                self.dependency("smc"),
            ]
        )
        index = pd.MultiIndex.from_tuples([("system", "total_system_cost")])
        total_system_cost = pd.DataFrame({"var_value": [all_costs.sum()]}, index=index)
        return total_system_cost


def run_postprocessing(es):
    # Setup calculations
    calculator = Calculator(es.params, es.results)

    summed_flows = SummedFlows(calculator).result
    storage_losses = StorageLosses(calculator).result
    transmission_losses = TransmissionLosses(calculator).result
    invested_capacity = InvestedCapacity(calculator).result
    invested_storage_capacity = InvestedStorageCapacity(calculator).result
    invested_capacity_costs = InvestedCapacityCosts(calculator).result
    invested_storage_capacity_costs = InvestedStorageCapacityCosts(calculator).result
    summed_carrier_costs = SummedCarrierCosts(calculator).result
    summed_marginal_costs = SummedMarginalCosts(calculator).result
    total_system_costs = TotalSystemCosts(calculator).result

    # # Get flows with emissions
    # carriers_with_emissions = 'ch4'
    #
    # specific_emissions = 1  # TODO: Replace with real data
    #
    # inputs = get_inputs(summed_flows)
    #
    # flows_with_emissions = filter_series_by_component_attr(inputs,
    #                                                        carrier=carriers_with_emissions)
    #
    # # Get emissions
    #
    # summed_emissions = flows_with_emissions * specific_emissions
    #
    # summed_emissions = set_index_level(
    #     summed_emissions,
    #     level='var_name',
    #     value='summed_emissions'
    # )
    #
    # # Get emission costs
    # emission_costs = 1  # TODO: Replace this with real data
    #
    # summed_emission_costs = summed_emissions * emission_costs
    #
    # summed_emission_costs = set_index_level(
    #     summed_emission_costs,
    #     level='var_name',
    #     value='summed_emission_costs'
    # )

    # Combine all results
    all_scalars = [
        summed_flows,
        storage_losses,
        transmission_losses,
        invested_capacity,
        invested_storage_capacity,
        invested_capacity_costs,
        invested_storage_capacity_costs,
        summed_carrier_costs,
        summed_marginal_costs,
    ]
    all_scalars = pd.concat(all_scalars, 0)
    all_scalars = ppu.map_var_names(
        all_scalars, calculator.scalar_params, calculator.busses, calculator.links
    )
    all_scalars = ppu.add_component_info(all_scalars, calculator.scalar_params)

    # Set index to string
    # TODO: Check if this can be done far earlier, also for performance reasons.
    # TODO: To do so, the information drawn from the components in add_component_info has
    # TODO: to be provided differently.
    # all_scalars.index = all_scalars.index.map(lambda x: (x[0].label, x[1]))
    all_scalars = pd.concat([all_scalars, total_system_costs], axis=0)
    all_scalars = all_scalars.sort_values(by=["carrier", "tech", "var_name"])

    return all_scalars
