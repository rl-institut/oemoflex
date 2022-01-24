import logging
import os
import re
from difflib import unified_diff

import pandas as pd

from oemof.network import Node
from oemof.tools import helpers
import oemof.solph as solph
import oemof.tabular.facades as tabular_facades

import oemoflex.facades as oemoflex_facades


def chop_trailing_whitespace(lines):
    return [re.sub(r"\s*$", "", line) for line in lines]


def remove(pattern, lines):
    if not pattern:
        return lines
    return re.subn(pattern, "", "\n".join(lines))[0].split("\n")


def normalize_to_positive_results(lines):
    negative_result_indices = [
        n for n, line in enumerate(lines) if re.match("^= -", line)
    ]
    equation_start_indices = [
        [n for n in reversed(range(0, nri)) if re.match(".*:$", lines[n])][0] + 1
        for nri in negative_result_indices
    ]
    for (start, end) in zip(equation_start_indices, negative_result_indices):
        for n in range(start, end):
            lines[n] = (
                "-"
                if lines[n] and lines[n][0] == "+"
                else "+"
                if lines[n]
                else lines[n]
            ) + lines[n][1:]
        lines[end] = "= " + lines[end][3:]
    return lines


def compare_lp_files(lp_file_1, lp_file_2, ignored=None):
    lines_1 = remove(ignored, chop_trailing_whitespace(lp_file_1.readlines()))
    lines_2 = remove(ignored, chop_trailing_whitespace(lp_file_2.readlines()))

    lines_1 = normalize_to_positive_results(lines_1)
    lines_2 = normalize_to_positive_results(lines_2)

    if not lines_1 == lines_2:
        raise AssertionError(
            "Failed matching lp_file_1 with lp_file_2:\n"
            + "\n".join(
                unified_diff(
                    lines_1,
                    lines_2,
                    fromfile=os.path.relpath(lp_file_1.name),
                    tofile=os.path.basename(lp_file_2.name),
                    lineterm="",
                )
            )
        )


class TestConstraints:
    @classmethod
    def setup_class(cls):
        cls.objective_pattern = re.compile(
            r"^objective.*(?=s\.t\.)", re.DOTALL | re.MULTILINE
        )

        cls.date_time_index = pd.date_range("1/1/2012", periods=3, freq="H")

        cls.tmpdir = helpers.extend_basic_path("tmp")
        logging.info(cls.tmpdir)

    @classmethod
    def setup(cls):
        cls.energysystem = solph.EnergySystem(
            groupings=solph.GROUPINGS, timeindex=cls.date_time_index
        )
        Node.registry = cls.energysystem

    def get_om(self):
        return solph.Model(self.energysystem, timeindex=self.energysystem.timeindex)

    def compare_to_reference_lp(self, ref_filename, my_om=None):
        if my_om is None:
            om = self.get_om()
        else:
            om = my_om

        tmp_filename = ref_filename.replace(".lp", "") + "_tmp.lp"

        new_filepath = os.path.join(self.tmpdir, tmp_filename)

        om.write(new_filepath, io_options={"symbolic_solver_labels": True})

        ref_filepath = os.path.join(
            os.path.dirname(__file__), "_files", "lp_files", ref_filename
        )

        with open(new_filepath) as new_file:
            with open(ref_filepath) as ref_file:
                compare_lp_files(new_file, ref_file)

    def test_storage_investment_green_field(self):
        r"""
        Storage investment without existing capacities.
        """
        el_bus = solph.Bus(label="electricity")

        tabular_facades.Storage(
            label="storage",
            carrier="electricity",
            tech="storage",
            bus=el_bus,
            efficiency=0.9,
            expandable=True,
            storage_capacity=0,  # No initially installed storage capacity
            storage_capacity_potential=10,
            storage_capacity_cost=1300,
            capacity=0,  # No initially installed capacity
            capacity_cost=240,
            capacity_potential=3,
        )

        self.compare_to_reference_lp("storage_investment_green_field.lp")

    def test_storage_investment_brown_field(self):
        r"""
        Storage investment with existing capacities.
        """
        bus_el = solph.Bus(label="electricity")

        tabular_facades.Storage(
            label="storage",
            carrier="electricity",
            tech="storage",
            bus=bus_el,
            efficiency=0.9,
            expandable=True,
            storage_capacity=2,  # Existing storage capacity
            storage_capacity_potential=10,
            storage_capacity_cost=1300,
            capacity=1,  # Existing capacity
            capacity_cost=240,
            capacity_potential=5,
        )

        self.compare_to_reference_lp("storage_investment_brown_field.lp")

    def test_asymmetric_storage_investment_green_field(self):
        r"""
        Investment of asymmetric storage without existing capacities.
        """
        bus_el = solph.Bus(label="electricity")

        oemoflex_facades.AsymmetricStorage(
            label="storage",
            carrier="electricity",
            tech="storage",
            type="storage",
            bus=bus_el,
            efficiency_charge=0.9,
            efficiency_discharge=0.64,
            expandable=True,
            storage_capacity=0,  # No inital storage capacity
            storage_capacity_potential=10,
            storage_capacity_cost=1300,
            capacity_charge=0,  # No inital capacities
            capacity_discharge=0,  # No inital capacities
            capacity_cost_charge=130,
            capacity_cost_discharge=260,
            capacity_potential_charge=5,
            capacity_potential_discharge=7,
        )

        self.compare_to_reference_lp("asymmetric_storage_investment_green_field.lp")

    def test_asymmetric_storage_investment_brown_field(self):
        r"""
        Investment of asymmetric storage with existing capacities.
        """
        bus_el = solph.Bus(label="electricity")

        oemoflex_facades.AsymmetricStorage(
            label="storage",
            carrier="electricity",
            tech="storage",
            type="storage",
            bus=bus_el,
            efficiency_charge=0.9,
            efficiency_discharge=0.64,
            expandable=True,
            storage_capacity=6,  # Existing storage capacity
            storage_capacity_potential=10,
            storage_capacity_cost=1300,
            capacity_charge=2,  # Existing capacity
            capacity_discharge=3,  # Existing capacity
            capacity_cost_charge=130,
            capacity_cost_discharge=260,
            capacity_potential_charge=5,
            capacity_potential_discharge=7,
        )

        self.compare_to_reference_lp("asymmetric_storage_investment_brown_field.lp")
