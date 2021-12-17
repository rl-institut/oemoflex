from oemoflex.model.datapackage import EnergyDataPackage
from oemoflex.model.variations import Sensitivity, EDPSensitivity
import os
import copy
import pytest

here = os.path.dirname(__file__)
path_edp_lb = os.path.join(here, "_files", "edp_lb")
path_edp_ub = os.path.join(here, "_files", "edp_ub")

edp_lb = EnergyDataPackage.from_csv_dir(path_edp_lb)
edp_ub = EnergyDataPackage.from_csv_dir(path_edp_ub)


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
