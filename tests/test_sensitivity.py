from oemoflex.model.datapackage import EnergyDataPackage
from oemoflex.model.variations import Sensitivity
import os
import copy
import pytest

here = os.path.dirname(__file__)
path_edp_lb = os.path.join(here, "_files", "edp_lb")
path_edp_ub = os.path.join(here, "_files", "edp_ub")

lb = EnergyDataPackage.from_csv_dir(path_edp_lb)
ub = EnergyDataPackage.from_csv_dir(path_edp_ub)


def test_sanity_check():

    sens = Sensitivity(lb, ub, n=4)
    n = sens.sanity_check()


def test_sanity_check_not_stacked():
    lb_unstacked = copy.deepcopy(lb)
    ub_unstacked = copy.deepcopy(ub)
    lb_unstacked.unstack_components()
    ub_unstacked.unstack_components()
    sens = Sensitivity(lb_unstacked, ub_unstacked, n=4)
    with pytest.raises(AssertionError):
        n = sens.sanity_check()


def test_sanity_check_index_different():
    lb_unstacked = copy.deepcopy(lb)
    ub_unstacked = copy.deepcopy(ub)
    lb_unstacked.unstack_components()
    ub_unstacked.unstack_components()
    sens = Sensitivity(lb_unstacked, ub_unstacked, n=4)
    with pytest.raises(AssertionError):
        n = sens.sanity_check()


if __name__ == "__main__":
    test_sanity_check()
    test_sanity_check_not_stacked()
