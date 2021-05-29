import os


class VariationGenerator:
    r"""
    A simple class that creates and saves several copies of a DataFramePackage given
    a definition of what to vary.

    Attributes
    ----------

    base_datapackage : DataFramepackage
        DataFramePackage to be used as a basis for variations.
    """
    def __init__(self, datapackage):

        self.base_datapackage = datapackage

    def create_variations(self, variation_df, destination):
        r"""
        Creates variations and stores them in a specified destination.

        Parameters
        ----------
        variation_df : pd.DataFrame
            DataFrame defining the parameter variations.

        destination : path
            Path to directory where varied DataFramePackages are saved to.
        """
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
        r"""
        Creates a single variation of a DataPackage given a Series that defines what to change.

        Parameters
        ----------
        dp : DataFramePackage
            Base DataFramePackage to vary.

        changes : pd.Series
            Series defining what to change.

        Returns
        -------
        _dp : DataFramePackage
            Altered DataFramePackage.
        """
        _dp = dp.copy()

        changes = changes.to_dict()

        for (resource, var_name), var_value in changes.items():

            _dp.parametrize(frame=resource, column=var_name, values=var_value)

        return _dp
