import abc
import logging

import pandas as pd
import enum
from typing import Dict


class CalculationError(Exception):
    """Raised if something is wrong in calculation"""


class DataType(enum.Enum):
    Scalars = "scalars"
    Sequences = "sequences"


class Calculator:
    """Entity to gather calculations and their results"""

    def __init__(self, input_parameters, output_parameters):
        self.calculations = {}
        self.scalar_params = self.__init_df_from_oemof_data(
            input_parameters, DataType.Scalars
        )
        self.scalars = self.__init_df_from_oemof_data(
            output_parameters, DataType.Scalars
        )
        self.sequences_params = self.__init_df_from_oemof_data(
            input_parameters, DataType.Sequences
        )
        self.sequences = self.__init_df_from_oemof_data(
            output_parameters, DataType.Sequences
        )
        self.busses = self.__filter_type("bus")
        self.links = self.__filter_type("link")
        logging.info("Successfully set up calculator")

    @staticmethod
    def __init_df_from_oemof_data(oemof_data, filter_: DataType):
        r"""
        Converts sequences dictionary to a multi-indexed
        DataFrame.
        """
        data = {
            tuple(str(k) if k is not None else None for k in key): value[filter_.value]
            for key, value in oemof_data.items()
            if filter_.value in value
        }
        result = pd.concat(data.values(), 0 if filter_ == DataType.Scalars else 1)

        if result.empty:
            return None

        # adapted from oemof.solph.views' node() function
        tuples = {
            key: list(value.index if filter_ == DataType.Scalars else value.columns)
            for key, value in data.items()
        }
        tuples = [tuple((*k, m) for m in v) for k, v in tuples.items()]
        tuples = [c for sublist in tuples for c in sublist]
        if filter_ == DataType.Scalars:
            result.index = pd.MultiIndex.from_tuples(tuples)
            result.index.names = ("source", "target", "var_name")
        else:
            result.columns = pd.MultiIndex.from_tuples(tuples)
            result.columns.names = ("source", "target", "var_name")

        return result

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
