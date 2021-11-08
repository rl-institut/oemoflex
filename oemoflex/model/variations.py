import copy
import os


class Sensitivity(object):
    def __init__(self, lb, ub, n):
        self.lb = lb
        self.ub = ub
        self.n = n

    def sanity_check(self):
        # assert lb, ub.data["component"] exists
        # assert index same
        # find the parameters that are different
        self.get_param()
        # assert that the difference is larger than eps
        # assert lb <= ub
        # n_param is the number parameters that is varied
        n_param = 0

        return n_param

    def get_param(self):
        # get the parameters that are varied
        param = []
        return param

    def get_samples_oat(self):

        n_param = self.sanity_check()

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
