import abc
import logging
import inspect
from dataclasses import dataclass

import pandas as pd
from typing import Dict, Union, Optional, Type


class CalculationError(Exception):
    """Raised if something is wrong in calculation"""


@dataclass
class Dependency:
    calculation: Type["Calculation"]
    parameters: Optional[dict] = None


def get_dependency_name(dependency: Union[Dependency, "Calculation"]):
    if isinstance(dependency, Calculation):
        # Get name from instance
        signiture = inspect.signature(dependency.__init__)
        return "_".join(
            [dependency.name]
            + [
                f"{parameter}={getattr(dependency, parameter)}"
                for parameter in signiture.parameters
                if parameter not in ("self", "calculator")
            ]
        )
    if dependency.parameters:
        # Get name from class and parameters
        return "_".join(
            [dependency.calculation.name]
            + [
                f"{parameter}={value}"
                for parameter, value in dependency.parameters.items()
                if parameter not in ("self", "calculator")
            ]
        )
    # Get name from class and default parameters in class
    signiture = inspect.signature(dependency.calculation.__init__)
    return "_".join(
        [dependency.calculation.name]
        + [
            f"{name}={parameter.default}"
            for name, parameter in signiture.parameters.items()
            if name not in ("self", "calculator")
        ]
    )


class Calculator:
    """Entity to gather calculations and their results"""

    def __init__(self, input_parameters, output_parameters):
        self.calculations = {}
        self.scalar_params = self.__init_df(input_parameters, "scalars")
        self.scalars = self.__init_df(output_parameters, "scalars")
        self.sequences_params = self.__init_df(input_parameters, "sequences")
        self.sequences = self.__init_df(output_parameters, "sequences")
        self.busses = self.__filter_type("bus")
        self.links = self.__filter_type("link")
        logging.info("Successfully set up calculator")

    @staticmethod
    def __init_df(oemof_data, data_type="scalars"):
        r"""
        Converts scalars/sequences dictionary to a multi-indexed
        DataFrame.
        """
        data = {
            tuple(str(k) if k is not None else None for k in key): (
                value[data_type]
                if isinstance(
                    value[data_type],
                    pd.Series if data_type == "scalars" else pd.DataFrame,
                )
                else (
                    pd.Series(value[data_type], dtype="object")
                    if data_type == "scalars"
                    else pd.DataFrame.from_dict(value[data_type], dtype="object")
                )
            )
            for key, value in oemof_data.items()
        }
        results = []
        for key, series in data.items():
            if series.empty:
                continue
            mindex = pd.MultiIndex.from_tuples(
                [
                    (*key, entry)
                    for entry in (
                        series.index if data_type == "scalars" else series.columns
                    )
                ],
                names=["source", "target", "var_name"],
            )
            if data_type == "scalars":
                series.index = mindex
            else:
                series.columns = mindex
            results.append(series)
        if results:
            return pd.concat(results, axis=(0 if data_type == "scalars" else 1))
        return (
            pd.Series(dtype="object")
            if data_type == "scalars"
            else pd.DataFrame(dtype="object")
        )

    def __filter_type(self, type_: str):
        return tuple(
            self.scalar_params[:, :, "type"][
                self.scalar_params[:, :, "type"] == type_
            ].index.get_level_values(0)
        )

    def add(self, dependency: Union[Dependency, "Calculation"]):
        """Adds calculation to calculations 'tree' if not yet present"""
        dependency_name = get_dependency_name(dependency)
        if isinstance(dependency, Calculation):
            if dependency_name in self.calculations:
                raise CalculationError(
                    f"Calculation '{dependency.__class__.__name__}' already exists in calculator"
                )
            self.calculations[dependency_name] = dependency
        else:
            if dependency_name in self.calculations:
                return
            if issubclass(dependency.calculation, Calculation):
                if dependency.parameters:
                    self.calculations[dependency_name] = dependency.calculation(
                        self, **dependency.parameters
                    )
                else:
                    self.calculations[dependency_name] = dependency.calculation(self)
                return
            raise CalculationError("Can only add Calculation instances or classes")

    def get_result(self, dependency_name):
        """Returns result of given dependency"""
        if dependency_name not in self.calculations:
            raise KeyError(f"Could not find calculation named '{dependency_name}'.")
        return self.calculations[dependency_name].result


class Calculation(abc.ABC):
    """
    Abstract class for calculations

    Dependent calculations are defined in `depends_on` and automatically added to
    calculation 'tree' if not yet present.
    Function `calculate_result` is abstract and must be implemented by child class.
    """

    name = None
    parameters = ()
    depends_on: Dict[str, Dependency] = None

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
        dependency_name = get_dependency_name(self.depends_on[name])
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
