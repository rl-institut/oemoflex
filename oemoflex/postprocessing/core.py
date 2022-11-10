import abc
import logging

import pandas as pd
import enum
from typing import Dict


class CalculationError(Exception):
    """Raised if something is wrong in calculation"""


class Calculator:
    """Entity to gather calculations and their results"""

    def __init__(self, input_parameters, output_parameters):
        self.calculations = {}
        self.scalar_params = self.__init_scalars_df(input_parameters)
        self.scalars = self.__init_scalars_df(output_parameters)
        self.sequences_params = self.__init_sequences_df(input_parameters)
        self.sequences = self.__init_sequences_df(output_parameters)
        self.busses = self.__filter_type("bus")
        self.links = self.__filter_type("link")
        logging.info("Successfully set up calculator")

    @staticmethod
    def __init_scalars_df(oemof_data):
        r"""
        Converts scalars dictionary to a multi-indexed
        DataFrame.
        """
        data = {
            tuple(str(k) if k is not None else None for k in key): (
                value["scalars"]
                if isinstance(value["scalars"], pd.Series)
                else pd.Series(value["scalars"])
            )
            for key, value in oemof_data.items()
        }
        results = []
        for key, series in data.items():
            if series.empty:
                continue
            series.index.name = "var_name"
            df = pd.DataFrame(series)
            df["source"] = key[0]
            df["target"] = key[1]
            df = df.set_index(["source", "target"], append=True)
            df = df.reorder_levels(["source", "target", "var_name"])
            results.append(df.iloc[:, 0])
        if results:
            return pd.concat(results)
        return pd.Series()

    @staticmethod
    def __init_sequences_df(oemof_data):
        r"""
        Converts sequences dictionary to a multi-indexed
        DataFrame.
        """
        data = {
            tuple(str(k) if k is not None else None for k in key): (
                value["sequences"]
                if isinstance(value["sequences"], pd.DataFrame)
                else pd.DataFrame.from_dict(value["sequences"])
            )
            for key, value in oemof_data.items()
        }

        results = []
        for key, series in data.items():
            if series.empty:
                continue
            series.columns = pd.MultiIndex.from_tuples(
                [(*key, column) for column in series.columns],
                names=["source", "target", "var_name"],
            )
            results.append(series)
        return pd.concat(results, axis=1)

    def __filter_type(self, type_: str):
        return tuple(
            self.scalar_params[:, :, "type"][
                self.scalar_params[:, :, "type"] == type_
            ].index.get_level_values(0)
        )

    def add(self, calculation):
        """Adds calculation to calculations 'tree' if not yet present"""
        if isinstance(calculation, Calculation):
            if calculation.__class__.__name__ in self.calculations:
                raise CalculationError(
                    f"Calculation '{calculation.__class__.__name__}' already exists in calculator"
                )
            self.calculations[calculation.__class__.__name__] = calculation
        else:
            if calculation.__name__ in self.calculations:
                return
            if issubclass(calculation, Calculation):
                self.calculations[calculation.__name__] = calculation(self)
                return
            raise CalculationError("Can only add Calculation instances or classes")

    def get_result(self, dependency_name):
        """Returns result of given dependency"""
        return self.calculations[dependency_name].result


class Calculation(abc.ABC):
    """
    Abstract class for calculations

    Dependent calculations are defined in `depends_on` and automatically added to
    calculation 'tree' if not yet present.
    Function `calculate_result` is abstract and must be implemented by child class.
    """

    depends_on: Dict[str, "Calculation"] = None

    def __init__(self, calculator: Calculator):
        super(Calculation, self).__init__()
        self.calculator = calculator
        self.calculator.add(self)
        self.__add_dependencies()
        self.__result = None

    def __add_dependencies(self):
        if not self.depends_on:
            return
        for dependency in self.depends_on.values():
            self.calculator.add(dependency)

    def dependency(self, name):
        dependency_name = self.depends_on[name].__name__
        return self.calculator.get_result(dependency_name)

    @abc.abstractmethod
    def calculate_result(self):
        """This method must be implemented in child class"""

    @property
    def result(self):
        if self.__result is None:
            self.__result = self.calculate_result()
        return self.__result

    @property
    def scalar_params(self):
        return self.calculator.scalar_params

    @property
    def scalars(self):
        return self.calculator.scalars

    @property
    def sequences_params(self):
        return self.calculator.sequences_params

    @property
    def sequences(self):
        return self.calculator.sequences

    @property
    def busses(self):
        return self.calculator.busses

    @property
    def links(self):
        return self.calculator.links
