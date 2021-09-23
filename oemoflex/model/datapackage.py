import os

import pandas as pd
from frictionless import Package

from oemoflex.model.model_structure import create_default_data
from oemoflex.model.inferring import infer
from oemoflex.model.postprocessing import run_postprocessing, group_by_element
import oemof.tabular.tools.postprocessing as tabular_pp


class DataFramePackage:
    r"""
    Provides a representation of frictionless datapackages as a collection
    of pandas.DataFrames.
    """

    def __init__(self, basepath, data, rel_paths, *args, **kwargs):

        self.basepath = basepath

        self.rel_paths = rel_paths

        self.data = data

    @classmethod
    def from_csv_dir(cls, dir):
        r"""
        Initialize a DataFramePackage from a csv directory

        Parameters
        ----------
        dir : str
            Path to csv directory
        """
        rel_paths = cls._get_rel_paths(dir, ".csv")

        data = cls._load_csv(cls, dir, rel_paths)

        return cls(dir, data, rel_paths)

    def to_csv_dir(self, destination):
        r"""
        Save the DataFramePackage to csv files.

        Parameters
        ----------
        destination : str
            Path to store data to
        """
        for name, data in self.data.items():
            path = self.rel_paths[name]

            full_path = os.path.join(destination, path)

            dir_full_path = os.path.expanduser(os.path.dirname(full_path))

            if not os.path.exists(dir_full_path):

                os.makedirs(dir_full_path)

            self._write_resource(data, full_path)

    @staticmethod
    def _get_rel_paths(dir, file_ext):
        r"""
        Get paths to all files in a given directory relative
        to the root with a given file extension.
        """
        rel_paths = {}
        for root, dirs, files in os.walk(dir):

            rel_path = os.path.relpath(root, dir)

            for file in files:
                if file.endswith(file_ext):
                    name = os.path.splitext(file)[0]
                    rel_paths[name] = os.path.join(rel_path, file)

        return rel_paths

    def _load_csv(self, basepath, rel_paths):
        r"""
        Load a DataFramePackage from csv files.
        """
        data = {}

        for name, path in rel_paths.items():
            full_path = os.path.join(basepath, path)
            data[name] = self._read_resource(full_path)

        return data

    @staticmethod
    def _read_resource(path):
        return pd.read_csv(path, index_col=0)

    @staticmethod
    def _write_resource(data, path):
        root = os.path.split(path)[0]

        if not os.path.exists(root):
            os.makedirs(root)

        data.to_csv(path)

    def _separate_stacked_frame(self, frame_name, target_dir, group_by):

        assert frame_name in self.data, (
            "Cannot group by component if stacked frame is " "missing."
        )

        frame_to_separate = self.data.pop(frame_name)

        self.rel_paths.pop(frame_name)

        separate_dfs = group_by_pivot(frame_to_separate, group_by=group_by)

        self.data.update(separate_dfs)

        self.rel_paths.update(
            {key: os.path.join(target_dir, key + ".csv") for key in separate_dfs.keys()}
        )

    def _stack_frames(
        self, frame_names, target_name, target_dir, unstacked_vars, index_vars
    ):

        assert frame_names, "Cannot stack scalars if frames are not in ."

        frames_to_stack = {}
        for name in frame_names:
            frames_to_stack[name] = self.data.pop(name)

            self.rel_paths.pop(name)

        self.data[target_name] = stack_frames(
            frames_to_stack, unstacked_vars, index_vars
        )

        self.rel_paths[target_name] = os.path.join(target_dir, target_name + ".csv")


class EnergyDataPackage(DataFramePackage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.name = kwargs.get("name")

        self.components = kwargs.get("components")

    @classmethod
    def setup_default(
        cls, name, basepath, datetimeindex, components, busses, regions, links, **kwargs
    ):
        r"""
        Initializes an EnergyDataPackage with a specific structure, but without the values of
        parameters being set.

        Parameters
        ----------
        name : str
            Name of the EnergyDataPackage
        basepath : str
            Path where EnergyDataPackage is stored
        datetimeindex : pandas.DatetimeIndex
            A valid timeindex
        components : list
            List of components
        busses : list
            List of busses
        regions : list
            List of regions
        links : list
            List of links between regions

        Other Parameters
        ----------------
        bus_attrs_update : dict
            Update with custom-defined busses
        component_attrs_update : dict
            Update with custom-defined components
        """
        data, rel_paths = create_default_data(
            select_regions=regions,
            select_links=links,
            datetimeindex=datetimeindex,
            select_components=components,
            select_busses=busses,
            **kwargs,
        )

        return cls(
            name=name,
            basepath=basepath,
            rel_paths=rel_paths,
            data=data,
            components=components,
        )

    @classmethod
    def from_metadata(cls, json_file_path):
        r"""
        Initialize a DataFramePackage from the metadata string,
        usually named datapackage.json

        Parameters
        ----------
        json_file_path : str
            Path to metadata
        """
        dp = Package(json_file_path)

        dir = os.path.split(json_file_path)[0]

        rel_paths = {r["name"]: r["path"] for r in dp.resources}

        data = cls._load_csv(cls, dir, rel_paths)

        return cls(dir, data, rel_paths)

    def infer_metadata(self, foreign_keys_update=None):
        r"""
        Infers metadata of the EnergyDataPackage and save it
        in basepath as `datapackage.json`.

        Parameters
        ----------
        foreign_keys_update

        Returns
        -------

        """
        infer(
            select_components=self.components,
            package_name=self.name,
            path=self.basepath,
            foreign_keys_update=foreign_keys_update,
        )

    def parametrize(self, frame, column, values):
        r"""
        Sets the values of parameters.

        Parameters
        ----------
        frame : str
            Name of the DataFrame in the Package.
        column :
            Name of the columns within the DataFrame
        values : str or numeric
            Values with the correct index to be set to the DataFrame
        """
        assert column in self.data[frame].columns, f"Column '{column}' is not defined!"

        self.data[frame].loc[:, column] = values

    def stack_components(self):
        r"""
        Stacks the component DataFrames into a single DataFrame.
        """

        def is_element(rel_path):
            directory = os.path.split(rel_path)[0]
            return "elements" in directory

        component_names = [
            key
            for key, rel_path in self.rel_paths.items()
            if is_element(rel_path) and not key == "bus"
        ]

        self._stack_frames(
            component_names,
            target_name="component",
            target_dir=os.path.join("data", "elements"),
            unstacked_vars=["name", "region", "carrier", "tech", "type"],
            index_vars=["name", "var_name"],
        )

    def unstack_components(self):
        r"""
        Unstacks a single component DataFrame into separate DataFrames for each component.
        """
        self._separate_stacked_frame(
            frame_name="component",
            target_dir=os.path.join("data", "elements"),
            group_by=["carrier", "tech"],
        )


class ResultsDataPackage(DataFramePackage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def from_energysytem(cls, es):
        r"""
        Initializes a ResultsDataPackage from an EnergySystem with optimization results.

        Parameters
        ----------
        es : oemof.solph.EnergySystem
            EnergySystem with results.
        """

        basepath = None

        data, rel_paths = cls._get_results(cls, es)

        return cls(basepath, data, rel_paths)

    def _get_results(self, es):

        data = {}

        rel_paths = {}

        data_scal, rel_paths_scal = self._get_scalars(self, es)

        data_seq, rel_paths_seq = self._get_sequences(self, es)

        data.update(data_seq)

        data.update(data_scal)

        rel_paths.update(rel_paths_seq)

        rel_paths.update(rel_paths_scal)

        return data, rel_paths

    def _get_sequences(self, es):

        data_seq, rel_paths_seq = self._get_bus_sequences(es)

        return data_seq, rel_paths_seq

    @staticmethod
    def _get_bus_sequences(es):

        bus_results = tabular_pp.bus_results(es, es.results)

        bus_results = {
            key: value for key, value in bus_results.items() if not value.empty
        }

        rel_paths = {
            key: os.path.join("sequences", "bus", key + ".csv")
            for key in bus_results.keys()
        }

        return bus_results, rel_paths

    def _get_scalars(self, es, by_element=False):

        all_scalars = run_postprocessing(es)

        all_scalars = all_scalars[sorted(all_scalars.columns)]

        if by_element:

            data_scal = group_by_element(all_scalars)

            rel_paths_scal = {
                key: os.path.join("scalars", key + ".csv") for key in data_scal.keys()
            }

        else:

            data_scal = {"scalars": all_scalars}

            rel_paths_scal = {"scalars": "scalars.csv"}

        return data_scal, rel_paths_scal

    def set_scenario_name(self, scenario_name):
        r"""
        Prepends the given scenario name to the scalar results' index.

        Parameters
        ----------
        scenario_name : str
            Name of the scenario
        """

        def prepend_index(df, level_name, values):
            return pd.concat([df], keys=[values], names=[level_name])

        assert (
            "scalars" in self.data
        ), "Scenario name can only be set when scalars are stacked."

        self.data["scalars"] = prepend_index(
            self.data["scalars"], "scenario", scenario_name
        )

    def to_element_dfs(self):
        r"""
        Separates scalar results such that each component is represented by one DataFrame.
        """
        self._separate_stacked_frame(
            frame_name="scalars", target_dir="elements", group_by=["carrier", "tech"]
        )

    def to_stacked_scalars(self):
        r"""
        Stacks all scalar results such into a single DataFrame named 'scalars'.
        """

        def is_element(rel_path):
            directory = os.path.split(rel_path)[0]
            return directory == "elements"

        element_names = [
            key for key, rel_path in self.rel_paths.items() if is_element(rel_path)
        ]

        self._stack_frames(
            frame_names=element_names,
            target_name="scalars",
            target_dir="",
            unstacked_vars=["scenario", "name", "region", "carrier", "tech", "type"],
            index_vars=["scenario", "name", "var_name"],
        )


def group_by_pivot(stacked_frame, group_by):
    def pivot_pandas_0_25_3_compatible(df, index, columns, values):
        _df = df.copy()

        _index = list(index)

        _index.remove(values)

        _df_piv = _df.set_index(_index).unstack(columns)

        _df_piv.columns = _df_piv.columns.droplevel(0)

        return _df_piv

    elements = {}
    for group, df in stacked_frame.groupby(group_by):
        name = "-".join(group)

        df = df.reset_index()

        index = df.columns

        df = pivot_pandas_0_25_3_compatible(
            df, index=index, columns="var_name", values="var_value"
        )

        # set index and sort columns for comparability
        df = df.reset_index()

        df = df.set_index("name")

        df = df[sorted(df.columns)]

        elements[name] = df

    return elements


def stack_frames(frames_to_stack, unstacked_vars, index_vars):

    stacked = []

    for key, df in frames_to_stack.items():

        df.reset_index(inplace=True)

        df = df.melt(unstacked_vars, var_name="var_name", value_name="var_value")

        stacked.append(df)

    stacked_frame = pd.concat(stacked)

    stacked_frame.set_index(index_vars, inplace=True)

    scalars = stacked_frame[sorted(stacked_frame.columns)]

    return scalars
