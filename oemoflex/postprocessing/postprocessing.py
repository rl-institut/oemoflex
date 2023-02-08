import pandas as pd
import numpy as np
from abc import abstractmethod

from oemoflex.postprocessing import naming, helper as ppu
from oemoflex.postprocessing.core import Calculation, Calculator, Dependency


class SummedFlows(Calculation):
    name = "summed_flows"

    def calculate_result(self):
        summed_flows = ppu.sum_flows(self.sequences)
        return ppu.drop_component_to_component(summed_flows, self.busses)


class Losses(Calculation):
    name = "losses"
    depends_on = {"summed_flows": Dependency(SummedFlows)}
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

    @abstractmethod
    def calculate_result(self):
        raise NotImplementedError


class StorageLosses(Losses):
    name = "storage_losses"
    depends_on = {"summed_flows": Dependency(SummedFlows)}
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
    name = "transmission_losses"
    depends_on = {"summed_flows": Dependency(SummedFlows)}
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
    name = "investment"

    def calculate_result(self):
        return (
            pd.Series(dtype="object")
            if (self.scalars is None or self.scalars.empty)
            else ppu.filter_by_var_name(self.scalars, "invest")
        )


class EPCosts(Calculation):
    name = "ep_costs"

    def calculate_result(self):
        ep_costs = ppu.filter_by_var_name(self.scalar_params, "investment_ep_costs")
        try:
            return ep_costs.unstack(2)["investment_ep_costs"]
        except KeyError:
            return pd.Series(dtype="object")


class InvestedCapacity(Calculation):
    """Collect invested (endogenous) capacity (units of power)"""

    name = "invested_capacity"
    depends_on = {"investment": Dependency(Investment)}

    def calculate_result(self):
        if self.dependency("investment").empty:
            return pd.Series(dtype="object")
        target_is_none = (
            self.dependency("investment").index.get_level_values(1).isnull()
        )
        return self.dependency("investment").loc[~target_is_none]


class InvestedStorageCapacity(Calculation):
    """Collect storage capacity (units of energy)"""

    name = "invested_storage_capacity"
    depends_on = {"investment": Dependency(Investment)}

    def calculate_result(self):
        if self.dependency("investment").empty:
            return pd.Series(dtype="object")
        target_is_none = (
            self.dependency("investment").index.get_level_values(1).isnull()
        )
        return self.dependency("investment").loc[target_is_none]


class InvestedCapacityCosts(Calculation):
    name = "invested_capacity_costs"
    depends_on = {
        "invested_capacity": Dependency(InvestedCapacity),
        "ep_costs": Dependency(EPCosts)
    }

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
    name = "invested_storage_capacity_costs"
    depends_on = {
        "invested_storage_capacity": Dependency(InvestedStorageCapacity),
        "ep_costs": Dependency(EPCosts)
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
    name = "summed_variable_costs"
    depends_on = {"summed_flows": Dependency(SummedFlows)}

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

    name = "summed_carrier_costs"
    depends_on = {"summed_variable_costs": Dependency(SummedVariableCosts)}

    def calculate_result(self):
        return ppu.get_inputs(self.dependency("summed_variable_costs"), self.busses)


class SummedMarginalCosts(Calculation):
    """
    Calculates summed marginal costs

    An `oemof.tabular` convention: Carrier costs are on inputs, marginal costs on output
    """

    name = "summed_marginal_costs"
    depends_on = {"summed_variable_costs": Dependency(SummedVariableCosts)}

    def calculate_result(self):
        return ppu.get_outputs(self.dependency("summed_variable_costs"), self.busses)


class TotalSystemCosts(Calculation):
    name = "total_system_costs"
    depends_on = {
        "invested_capacity_costs": Dependency(InvestedCapacityCosts),
        "invested_storage_capacity_costs": Dependency(InvestedStorageCapacityCosts),
        "summed_carrier_costs": Dependency(SummedCarrierCosts),
        "summed_marginal_costs": Dependency(SummedMarginalCosts),
    }

    def calculate_result(self):
        all_costs = pd.concat(
            [
                self.dependency("invested_capacity_costs"),
                self.dependency("invested_storage_capacity_costs"),
                self.dependency("summed_carrier_costs"),
                self.dependency("summed_marginal_costs"),
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
    all_scalars = naming.map_var_names(
        all_scalars, calculator.scalar_params, calculator.busses, calculator.links
    )
    all_scalars = naming.add_component_info(all_scalars, calculator.scalar_params)
    all_scalars = pd.concat([all_scalars, total_system_costs], axis=0)
    all_scalars = all_scalars.sort_values(by=["carrier", "tech", "var_name"])

    return all_scalars
