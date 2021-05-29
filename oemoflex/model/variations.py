import os


class VariationGenerator:

    def __init__(self, datapackage):

        self.base_datapackage = datapackage

    def create_variations(self, variation_df, destination):

        assert variation_df.index.name == 'variation_id', \
            "The variations defined in variation_df must be indexed with 'variation_id'"

        assert variation_df.columns.names == ['component', 'var_name'], \
            "The variations defined in variation_df must have columns specifying" \
            "'component and 'var_name'."

        for id, changes in variation_df.iterrows():

            dp = self.create_var(self.base_datapackage, changes)

            variation_dir = os.path.join(destination, str(id))

            dp.to_csv_dir(variation_dir)

    def create_var(self, dp, changes):

        _dp = dp.copy()

        changes = changes.to_dict()

        for (resource, var_name), var_value in changes.items():

            _dp.parametrize(frame=resource, column=var_name, values=var_value)

        return _dp
