import copy
import os


def index_same(df_a, df_b):
    return df_a.index.equals(df_b.index)


def data_same(df_a, df_b):
    return df_a.equals(df_b)


def smaller_equal(df_a, df_b):
    return (df_a < df_b).all()


def get_diff(df_a, df_b):
    # # pandas>1.1.0
    # diff = self.lb.compare(self.ub)
    return ~((df_a == df_b) | ((df_a != df_a) & (df_b != df_b)))


def diff_larger_eps(df_a, df_b, eps):
    diff = get_diff(df_a, df_b)
    df_diff = df_a.loc[diff] - df_b.loc[diff]
    return abs(df_diff) > eps


class Sensitivity(object):
    r"""
    Accepts two DataFrames that are the same in index and most columns, but have different entries
    in the column 'var_value'. The DataFrames describe lower and upper bound of a variation. With
    these intervals, different sampling methods can be invoked.
    """
    AUX_COLUMNS = ["carrier", "region", "tech", "type"]
    VAR_VALUE = "var_value"

    def __init__(self, lb, ub, eps=1e-6):
        self.lb = lb
        self.ub = ub
        self.eps = eps
        self.sanity_check()

    def sanity_check(self):
        # assert index same
        assert index_same(self.lb, self.ub), "Indexes of lb and ub are not the same."

        # Assert that the data is different
        assert not data_same(
            self.lb, self.ub
        ), "There is no difference between lb and ub."

        # Assert that the auxiliary columns are the same
        assert data_same(
            self.lb.loc[:, self.AUX_COLUMNS], self.ub.loc[:, self.AUX_COLUMNS]
        )

        # find the parameters that are different (comparing NaN)
        diff = self.get_diff()

        # assert lb <= ub
        assert smaller_equal(
            self.lb.loc[diff, self.VAR_VALUE], self.ub.loc[diff, self.VAR_VALUE]
        )

        # assert that the difference is larger than eps

        assert diff_larger_eps(
            self.lb.loc[diff, self.VAR_VALUE],
            self.ub.loc[diff, self.VAR_VALUE],
            self.eps,
        ).all(), f"The difference between lb and ub is lower than the defined minimum of {self.eps}"

    def get_diff(self):
        return get_diff(self.lb.loc[:, self.VAR_VALUE], self.ub.loc[:, self.VAR_VALUE])

    def get_param(self):
        # get the parameters that are varied
        param = self.lb.index[self.get_diff()]
        return param

    def get_samples_oat(self):

        params = self.get_param()

        # for each param, create n samples
        samples = []
        for param in params:
            sample = self.lb.copy()
            sample.loc[param] = self.ub.loc[param]
            samples.append(sample)

        return samples

    def get_samples_lhs(self):

        self.sanity_check()

        samples = []

        return samples


class EDPSensitivity(Sensitivity):
    r"""
    Accepts two EnergyDataPackages that are have different values. The Packages describe lower and
    upper bound of a variation. With these intervals, different sampling methods can be invoked.
    """

    def __init__(self, lb_edp, ub_edp, eps=1e-6):
        self.lb_edp = lb_edp
        self.ub_edp = ub_edp
        self.eps = eps
        self.check_if_stacked()
        self.sanity_check()

    def check_if_stacked(self):
        if not (self.lb_edp.stacked and self.ub_edp.stacked):
            raise AssertionError("EnergyDataPackages have to be stacked")

    def get_lb(self):
        return self.lb_edp.data["component"]

    def set_lb(self, value):
        self.lb_edp.data["component"] = value

    def del_lb(self):
        del self.lb_edp

    def get_ub(self):
        return self.ub_edp.data["component"]

    def set_ub(self, value):
        self.ub_edp.data["component"] = value

    def del_ub(self):
        del self.ub_edp

    lb = property(get_lb, set_lb, del_lb)
    ub = property(get_ub, set_ub, del_ub)


class VariationGenerator:
    def __init__(self, datapackage):

        self.base_datapackage = datapackage

    def create_variations(self, variations, destination):

        for id, changes in variations.iterrows():

            dp = self.create_var(self.base_datapackage, changes)

            variation_dir = os.path.join(destination, str(id))

            dp.to_csv_dir(variation_dir)

    def create_var(self, dp, changes):

        _dp = copy.deepcopy(dp)

        changes = changes.to_dict()

        for (resource, var_name), var_value in changes.items():

            _dp.data[resource].loc[:, var_name] = var_value

        return _dp
