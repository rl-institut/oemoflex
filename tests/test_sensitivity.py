import pandas as pd

from oemoflex.model.datapackage import EnergyDataPackage
from oemoflex.model.variations import Sensitivity, EDPSensitivity, diff_larger_eps, get_diff
import os
import copy
import pytest

here = os.path.dirname(__file__)
path_lb = os.path.join(here, "_files", "lb.csv")
path_ub = os.path.join(here, "_files", "ub.csv")
path_edp_lb = os.path.join(here, "_files", "edp_lb")
path_edp_ub = os.path.join(here, "_files", "edp_ub")

lb = pd.read_csv(path_lb, header=0)
ub = pd.read_csv(path_ub, header=0)
edp_lb = EnergyDataPackage.from_csv_dir(path_edp_lb)
edp_ub = EnergyDataPackage.from_csv_dir(path_edp_ub)


def test_get_diff():
    assert (get_diff(lb["var_value"], ub["var_value"]) == pd.Series([True, True, False, False])).all()


def test_diff_larger_eps():
    assert diff_larger_eps(lb["var_value"], ub["var_value"], 1e-3).all()


def test_init():
    sens = Sensitivity(lb, ub)


def test_sanity_check():
    sens = EDPSensitivity(edp_lb, edp_ub)
    sens.sanity_check()


def test_sanity_check_not_stacked():
    lb_unstacked = copy.deepcopy(edp_lb)
    ub_unstacked = copy.deepcopy(edp_ub)
    lb_unstacked.unstack_components()
    ub_unstacked.unstack_components()
    sens = EDPSensitivity(lb_unstacked, ub_unstacked)
    with pytest.raises(AssertionError):
        sens.sanity_check()


def test_sanity_check_index_different():
    edp_lb.data["component"].reset_index(inplace=True, drop=True)

    sens = EDPSensitivity(edp_lb, edp_ub)

    with pytest.raises(AssertionError):
        sens.sanity_check()


if __name__ == "__main__":
    test_sanity_check()
