
import sys
import pandas
import pathlib

from oemof.solph import EnergySystem

import oemoflex.postprocessing.postprocessing
from oemoflex.postprocessing import core

path_to_oemof_b3 = str(pathlib.Path(__file__).parent.parent.parent / "oemof-B3")
sys.path.append(path_to_oemof_b3)  # FIXME: Workaround to restore dump from oemof-B3

TEST_FILES_DIR = pathlib.Path(__file__).parent / "_files"


def test_postprocessing_with_dump():
    scenarios = ("example_more_re_less_fossil", "2050-100-gas_moreCH4")

    for scenario in scenarios:
        es = EnergySystem()
        es.restore(TEST_FILES_DIR / "es_dumps", filename=f"{scenario}.oemof")
        results: pandas.DataFrame = oemoflex.postprocessing.postprocessing.run_postprocessing(es)
        results["scenario"] = scenario
        results = results.reset_index()
        results = results.astype({"var_value": "float64"})
        results = results.sort_values(["name", "var_name"])
        results = results.reset_index(drop=True)

        original_results = pandas.read_csv(TEST_FILES_DIR / "postprocessed_results" / f"{scenario}.csv")
        original_results = original_results[results.columns]
        original_results = original_results.sort_values(["name", "var_name"])
        original_results = original_results.reset_index(drop=True)

        assert len(set(results) ^ set(original_results)) == 0
        pandas.testing.assert_frame_equal(results, original_results)
