import copy
import os


def index_same(df_a, df_b):
    return df_a.index.equals(df_a.index)


def data_same(df_a, df_b):
    return df_a.equals(df_b)


def smaller_equal(df_a, df_b):
    return (df_a < df_b).all()


def get_diff(df_a, df_b):
    ## pandas>1.1.0
    # diff = lb_data.compare(ub_data)
    return ~((df_a == df_b) | ((df_a != df_a) & (df_b != df_b)))


def diff_larger_eps(df_a, df_b, eps):
    diff = get_diff(df_a, df_b)
    df_diff = df_a.loc[diff] - df_b.loc[diff]
    return abs(df_diff) > eps


class Sensitivity(object):
    def __init__(self, lb, ub, n, eps=1e6):
        self.lb = lb
        self.ub = ub
        self.n = n
        self.eps = eps

    def sanity_check(self):
        # assert lb, ub.data["component"] exists
        for edp in [self.lb, self.ub]:
            assert (
                "component" in edp.data
            ), f"EnergyDatapackage lb or ub does not contain stacked component data."

        lb_data = self.lb.data["component"]

        ub_data = self.ub.data["component"]

        # assert index same
        assert index_same(lb_data, ub_data), f"Indexes of lb and ub are not the same."

        # Assert that the data is different
        assert not data_same(lb_data, ub_data), f"There is no difference between lb and ub."

        # Assert that the auxiliary columns are the same
        AUX_COLUMNS = ["carrier", "region", "tech", "type"]
        assert data_same(lb_data.loc[:, AUX_COLUMNS], ub_data.loc[:, AUX_COLUMNS])

        # find the parameters that are different (comparing NaN)
        diff = get_diff(lb_data.loc[:, "var_value"], ub_data.loc[:, "var_value"])

        # assert lb <= ub
        assert smaller_equal(lb_data.loc[:, "var_value"], ub_data.loc[:, "var_value"])

        # assert that the difference is larger than eps

        assert diff_larger_eps(lb_data, ub_data, self.eps), \
            f"The difference between lb and ub islower than the defined tolerance of {self.eps}"

    def get_param(self):
        # get the parameters that are varied
        param = []
        return param

    def get_samples_oat(self):

        self.sanity_check()

        # for each param, create n samples
        samples = []

        return samples

    def get_samples_lhs(self):

        self.sanity_check()

        samples = []

        return samples


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
