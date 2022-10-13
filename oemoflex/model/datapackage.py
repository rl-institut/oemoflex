import copy
import os

import oemof.tabular.tools.postprocessing as tabular_pp
from oemof.tabular.datapackage.building import infer_metadata
import pandas as pd
from frictionless import Package
from oemof.solph.views import convert_to_multiindex

from oemoflex.model.model_structure import create_default_data
from oemoflex.model.postprocessing import group_by_element, run_postprocessing
from oemoflex.tools.helpers import load_yaml
from oemoflex.config.config import settings


module_path = os.path.dirname(os.path.abspath(__file__))

FOREIGN_KEYS = "foreign_keys.yml"

foreign_keys = load_yaml(os.path.join(module_path, FOREIGN_KEYS))


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

    def to_csv_dir(self, destination, overwrite=False):
        r"""
        Save the DataFramePackage to csv files. Warns if overwrite is False and the destination is
        not empty. If overwrite is True, all existing contents in destination will be deleted.

        Parameters
        ----------
        destination : str
            Path to store data to
        overwrite : bool
            Decides if any existing files will be overwritten.
        """
        # Check if path exists and is non-empty
        if os.path.exists(destination) and os.listdir(destination):
            # If overwrite is False, throw a warning
            if not overwrite:
                raise UserWarning(
                    "The path is not empty. Might overwrite existing data. "
                    "Pass 'overwrite=True' to ignore"
                )

            # If overwrite is True delete any contents
            elif overwrite:
                import shutil

                shutil.rmtree(destination)

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
        return pd.read_csv(path, index_col=0, sep=settings.SEPARATOR)

    @staticmethod
    def _write_resource(data, path):
        root = os.path.split(path)[0]

        if not os.path.exists(root):
            os.makedirs(root)

        data.to_csv(path, sep=settings.SEPARATOR)


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
        """
        if foreign_keys_update:
            for key, value in foreign_keys_update.items():
                if key in foreign_keys:
                    foreign_keys[key].extend(value)
                    print(f"Updated foreign keys for {key}.")
                else:
                    foreign_keys[key] = value
                    print(f"Added foreign key for {key}.")

        infer_metadata(
            package_name=self.name,
            path=self.basepath,
            foreign_keys=foreign_keys,
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

        _stack_frames(
            self,
            component_names,
            target_name="component",
            target_dir=os.path.join("data", "elements"),
            vars_to_stack=["name", "region", "carrier", "tech", "type"],
            index_vars=["name", "var_name"],
        )

    def unstack_components(self):
        r"""
        Unstacks a single component DataFrame into separate DataFrames for each component.
        """
        _separate_stacked_frame(
            self,
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

    def _get_sequences(self, es, kind=("bus", "component", "by_variable")):
        def get_rel_paths(keys, *subdirs, file_ext=".csv"):
            return {key: os.path.join(*subdirs, key + file_ext) for key in keys}

        def drop_empty_dfs(dictionary):
            return {key: value for key, value in dictionary.items() if not value.empty}

        methods = {
            "bus": tabular_pp.bus_results,
            "component": tabular_pp.component_results,
            "by_variable": self._get_seq_by_var,
        }

        methods = {k: v for k, v in methods.items() if k in kind}

        data_seq = {}
        rel_paths_seq = {}

        for name, method in methods.items():
            data = method(es, es.results)

            data = drop_empty_dfs(data)

            rel_paths = get_rel_paths(data, "sequences", name)

            data_seq.update(data)

            rel_paths_seq.update(rel_paths)

        return data_seq, rel_paths_seq

    @staticmethod
    def _get_seq_by_var(es, results):

        # copy to avoid manipulating the data in es.results
        sequences = copy.deepcopy(
            {
                key: value["sequences"]
                for key, value in results.items()
                if value["sequences"] is not None
            }
        )

        sequences = convert_to_multiindex(sequences)

        idx = pd.IndexSlice

        variables = list(set(sequences.columns.get_level_values(2)))

        sequences_by_variable = {}

        for variable in variables:

            var_results = sequences.loc[:, idx[:, :, variable]]

            sequences_by_variable[variable] = var_results

        return sequences_by_variable

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
        _separate_stacked_frame(
            self,
            frame_name="scalars",
            target_dir="elements",
            group_by=["carrier", "tech"],
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

        _stack_frames(
            self,
            frame_names=element_names,
            target_name="scalars",
            target_dir="",
            vars_to_stack=["scenario", "name", "region", "carrier", "tech", "type"],
            index_vars=["scenario", "name", "var_name"],
        )


def _separate_stacked_frame(dfp, frame_name, target_dir, group_by):
    r"""
    Separates a frame of the DataFramepackage with the structure
    "name", "var_name", "var_value" into several frames according
    to groupby into a target directory
    """
    assert frame_name in dfp.data, (
        "Cannot group by component if stacked frame is " "missing."
    )
    # TODO: The method assumes a certain structure but does not assert it.

    frame_to_separate = dfp.data.pop(frame_name)  # pop frame from data

    dfp.rel_paths.pop(frame_name)  # pop path of frame from paths

    separate_dfs = group_by_pivot(frame_to_separate, group_by=group_by)

    dfp.data.update(separate_dfs)  # add separate frames to data

    # add paths of separate frames
    dfp.rel_paths.update(
        {key: os.path.join(target_dir, key + ".csv") for key in separate_dfs.keys()}
    )


def group_by_pivot(stacked_frame, group_by):
    def pivot_pandas_0_25_3_compatible(df, index, columns, values):
        _df = df.copy()

        _index = list(index)

        _index.remove(values)

        _df_piv = _df.set_index(_index).unstack(columns)

        _df_piv.columns = _df_piv.columns.droplevel(0)

        return _df_piv

    separated_dfs = {}
    for group, df in stacked_frame.groupby(group_by):
        name = "-".join(group)  # This ain't necessary - it is a convention.

        df = df.reset_index()

        df = pivot_pandas_0_25_3_compatible(
            df, index=df.columns, columns="var_name", values="var_value"
        )

        # set index and sort columns for comparability
        df = df.reset_index()

        df = df.set_index("name")

        df = df[sorted(df.columns)]

        separated_dfs[name] = df

    return separated_dfs


def _stack_frames(dfp, frame_names, target_name, target_dir, vars_to_stack, index_vars):
    r"""
    Stacks given frames of a DataFramePackage into a single frame with a target name
    and directory. The columns of the frames fall in two categories: index_vars that
    remain unstack and vars_to_stack that will be stacked.
    """
    assert frame_names, "Cannot stack scalars if frames are not in ."

    dfs_to_stack = []
    for name in frame_names:
        # pop the frames that should be stacked
        dfs_to_stack.append(dfp.data.pop(name))

        # pop the paths of the frames that should be stacked
        dfp.rel_paths.pop(name)

    # stack data
    stacked_frame = stack_dataframes(dfs_to_stack, vars_to_stack, index_vars)

    # Write stacked data
    dfp.data[target_name] = stacked_frame

    # set path for stacked data
    dfp.rel_paths[target_name] = os.path.join(target_dir, target_name + ".csv")


def stack_dataframes(dfs_to_stack, vars_to_stack, index_vars):
    r"""
    Takes a list of pd.DataFrames, a set of vars_to_stack and stacks them.
    An index is set.
    The columns are sorted.
    """
    stacked = []

    for df in dfs_to_stack:

        df.reset_index(inplace=True)

        df = df.melt(vars_to_stack, var_name="var_name", value_name="var_value")

        stacked.append(df)

    stacked_frame = pd.concat(stacked)

    # TODO: Is it necessary to set the index, or could this be performed outside of the function?
    # Maybe it is only done to avoid sorting these in the next step?
    stacked_frame.set_index(index_vars, inplace=True)

    # TODO: Is it necessary to sort the columns, and could the order be other than alphabetic?
    scalars = stacked_frame[sorted(stacked_frame.columns)]

    return scalars
