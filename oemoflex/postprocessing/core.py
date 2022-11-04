import abc
from typing import Dict


class CalculationError(Exception):
    """Raised if something is wrong in calculation"""


class Calculator:
    """Entity to gather calculations and their results"""

    def __init__(self, scalar_params, scalars, sequences_params, sequences):
        self.calculations = {}
        self.scalar_params = scalar_params
        self.scalars = scalars
        self.sequences_params = sequences_params
        self.sequences = sequences

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
