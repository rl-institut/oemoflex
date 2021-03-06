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
        """
        rel_paths = cls._get_rel_paths(dir, '.csv')

        data = cls._load_csv(cls, dir, rel_paths)

        return cls(dir, data, rel_paths)

    @classmethod
    def from_metadata(cls, json_file_path):
        r"""
        Initialize a DataFramePackage from the metadata string,
        usually named datapackage.json
        """
        dp = Package(json_file_path)

        dir = os.path.split(json_file_path)[0]

        rel_paths = {r['name']: r['path'] for r in dp.resources}

        data = cls._load_csv(cls, dir, rel_paths)

        return cls(dir, data, rel_paths)

    def to_csv_dir(self, destination):
        r"""
        Save the DataFramePackage to csv files.
        """
        for name, data in self.data.items():
            path = self.rel_paths[name]
            full_path = os.path.join(destination, path)
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
                    name = file.strip(file_ext)
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


class EnergyDataPackage(DataFramePackage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.name = kwargs.get("name")

        self.components = kwargs.get("components")


    @classmethod
    def setup_default(
            cls,
            name,
            basepath,
            datetimeindex,
            components,
            busses,
            regions,
            links,
    ):

        data, rel_paths = create_default_data(
            select_regions=regions,
            select_links=links,
            datetimeindex=datetimeindex,
            select_components=components,
            select_busses=busses,
        )

        return cls(
            name=name,
            basepath=basepath,
            rel_paths=rel_paths,
            data=data,
            components=components
        )

    def infer_metadata(self):
        infer(
            select_components=self.components,
            package_name=self.name,
            path=self.basepath,
        )


class ResultsDataPackage(DataFramePackage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def from_energysytem(cls, es):

        basepath = None

        data, rel_paths = cls.get_results(cls, es)

        return cls(basepath, data, rel_paths)

    def get_results(self, es):

        data = {}

        rel_paths = {}

        # data_scal, rel_paths_scal = self.get_scalars(self, es)

        data_seq, rel_paths_seq = self.get_sequences(self, es)

        data.update(data_seq)

        # data.update(data_scal)

        rel_paths.update(rel_paths_seq)

        # rel_paths.update(rel_paths_scal)

        return data, rel_paths

    def get_sequences(self, es):

        data_seq, rel_paths_seq = self.get_bus_sequences(es)

        return data_seq, rel_paths_seq

    @staticmethod
    def get_bus_sequences(es):

        bus_results = tabular_pp.bus_results(es, es.results)

        bus_results = {key: value for key, value in bus_results.items() if not value.empty}

        rel_paths = {
            key: os.path.join('sequences', 'bus', key + '.csv')
            for key in bus_results.keys()
        }

        return bus_results, rel_paths

    def get_scalars(self, es):
        # TODO: Import functions for scalar postprocessing from separate module.

        all_scalars = run_postprocessing(es)

        data_scal = group_by_element(all_scalars)

        rel_paths_scal = {key: os.path.join('scalars', key + '.csv') for key in data_scal.keys()}

        return data_scal, rel_paths_scal
