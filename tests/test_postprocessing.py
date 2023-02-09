import pandas
import pathlib

from unittest import mock

from oemof.tabular import datapackage  # noqa: F401
from oemof.solph import EnergySystem, Model, processing, constraints
from oemof.tabular.facades import TYPEMAP
from oemoflex.postprocessing import core, postprocessing

import helpers


TEST_FILES_DIR = pathlib.Path(__file__).parent / "_files"


class ParametrizedCalculation(postprocessing.Calculation):
    name = "pc"

    def __init__(self, calculator, a=2, b=4):
        self.a = a
        self.b = b
        super().__init__(calculator)

    def calculate_result(self):
        return


def test_dependency_name():
    calculator = mock.MagicMock()
    summed_flows = postprocessing.SummedFlows(calculator)
    name = core.get_dependency_name(summed_flows)
    assert name == "summed_flows"

    dep = core.ParametrizedCalculation(postprocessing.SummedFlows)
    name = core.get_dependency_name(dep)
    assert name == "summed_flows"

    name = core.get_dependency_name(ParametrizedCalculation(calculator, a=2, b=2))
    assert name == "pc_a=2_b=2"

    dep = core.ParametrizedCalculation(ParametrizedCalculation)
    name = core.get_dependency_name(dep)
    assert name == "pc_a=2_b=4"


def test_postprocessing_with_constraints():
    scenarios = ("Test_scenario",)

    for scenario in scenarios:
        dump_folder = TEST_FILES_DIR / scenario / "optimized"

        if not (dump_folder / "es_dump.oemof").exists():
            es = EnergySystem.from_datapackage(
                str(TEST_FILES_DIR / scenario / "preprocessed" / "datapackage.json"),
                attributemap={},
                typemap=TYPEMAP,
            )
            # get additional scalars, set to None at first
            emission_limit = None
            el_gas_relations = None
            bpchp_out = None
            additional_scalars = helpers.get_additional_scalars(scenario)
            if additional_scalars is not None:
                emission_limit = helpers.get_emission_limit(additional_scalars)
                el_gas_relations = helpers.get_electricity_gas_relations(
                    additional_scalars
                )
                bpchp_out = helpers.get_bpchp_output_parameters(additional_scalars)

            if bpchp_out is not None:
                es = helpers.add_output_parameters_to_bpchp(
                    parameters=bpchp_out, energysystem=es
                )

            m = Model(es)

            if emission_limit is not None:
                constraints.emission_limit(m, limit=emission_limit)
            if el_gas_relations is not None:
                helpers.add_electricity_gas_relation_constraints(
                    model=m, relations=el_gas_relations
                )

            m.receive_duals()
            m.solve()
            es.meta_results = processing.meta_results(m)
            es.results = processing.results(m)
            es.params = processing.parameter_as_dict(es)
            es.dump(str(TEST_FILES_DIR / scenario / "optimized"))
        else:
            es = EnergySystem()
            es.restore(dump_folder)
        results: pandas.DataFrame = postprocessing.run_postprocessing(es)
        results["scenario"] = scenario
        results = results.reset_index()
        results = results.astype({"var_value": "float64"})
        results = results.sort_values(["name", "var_name"])
        results = results.reset_index(drop=True)

        original_results = pandas.read_csv(
            TEST_FILES_DIR / scenario / "postprocessed" / "scalars.csv"
        )
        original_results = original_results[results.columns]
        original_results = original_results.sort_values(["name", "var_name"])
        original_results = original_results.reset_index(drop=True)

        assert len(set(results) ^ set(original_results)) == 0
        pandas.testing.assert_frame_equal(results, original_results)
