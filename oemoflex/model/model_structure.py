import os

import pandas as pd

from oemoflex.tools.helpers import load_yaml

module_path = os.path.dirname(os.path.abspath(__file__))


class FacadeAttrs:
    r"""
    A class representing facade attributes specified in .csv files.

    Parameters
    ----------
    dir_facade_attrs : path
        Path of the directory containing specifications as .csv files

    Attributes
    ---------
    paths : dict
        Dictionary mapping facade type to absolute paths
    specs : dict
        Dictionary mapping facade type to pd.DataFrame containing specs
    """

    def __init__(self, dir_facade_attrs):
        self.paths = {}
        self.specs = {}
        self.update(dir_facade_attrs)

    def get_facade_attr(self, type):
        return self.specs[type]

    def update(self, dir_facade_attrs):
        self._update_paths(dir_facade_attrs)
        self._update_specs()

    def _update_paths(self, dir_facade_attrs):
        paths = {
            os.path.splitext(path)[0]: os.path.join(dir_facade_attrs, path)
            for path in os.listdir(dir_facade_attrs)
            if path
        }

        self.paths.update(paths)

    def _update_specs(self):
        for type, path in self.paths.items():
            self.specs[type] = pd.read_csv(
                self.paths[type],
                index_col=0,
                header=0,
            )


def create_default_data(
    select_regions,
    select_links,
    datetimeindex=None,
    select_components=None,
    select_busses=None,
    dummy_sequences=False,
    bus_attrs_file=os.path.join(module_path, "busses.yml"),
    component_attrs_file=os.path.join(module_path, "component_attrs.yml"),
    facade_attrs_dir=os.path.join(module_path, "facade_attrs"),
    bus_attrs_update=None,
    component_attrs_update=None,
    facade_attrs_update=None,
    elements_subdir="elements",
    sequences_subdir="sequences",
):
    r"""
    Prepares oemoef.tabluar input CSV files:
    * includes headers according to definitions in CSVs in directory 'component_attrs_dir'
    * pre-define all oemof elements (along CSV rows) without actual dimensions/values

    Parameters
    ----------
    select_regions : list
        List of regions.

    select_links : list
        List of links.

    datetimeindex : pd.DateTimeIndex
        Timeindex for sequences.

    select_components : list
        List of components.

    select_busses : list
        List of busses.

    dummy_sequences : True/False
        Create dummy sequences.

    busses_file : path
        Path to a YAML file that defines the busses

    component_attrs_file : path
        Path to a YAML file that defines the component_attributes

    elements_subdir : str
        oemof.tabular definition.

    sequences_subdir : str
        oemof.tabular definition.

    Returns
    -------
    data : dict
        Dictionary containing pd.DataFrames for elements and sequences

    rel_paths : dict
        Dictionary containing relative file paths.
    """
    # load component, bus and facade specifications
    component_attrs = load_yaml(component_attrs_file)

    bus_attrs = load_yaml(bus_attrs_file)

    facade_attrs = FacadeAttrs(facade_attrs_dir)

    # update
    if component_attrs_update:
        component_attrs.update(component_attrs_update)

    if bus_attrs_update:
        bus_attrs.update(bus_attrs_update)

    if facade_attrs_update:
        facade_attrs.update(facade_attrs_update)

    # TODO: Use only the busses necessary or defined.
    selected_bus_attrs = select_from_node_attrs(bus_attrs, select_busses)

    # select components or choose all if selection is None
    selected_component_attrs = select_from_node_attrs(
        component_attrs, select_components
    )

    transmissions_without_link = [
        comp.get("tech")
        for comp in selected_component_attrs.values()
        if (("type", "link") in comp.items() and select_links is None)
    ]

    if transmissions_without_link:
        raise ValueError(
            f"You don't have a link, but you have at least one component, that requires a link. "
            f"This affects component(s) with the following 'tech': {transmissions_without_link}. "
            "Please define link(s)."
        )

    # Create empty dictionaries for the dataframes and their relative paths in the datapackage.
    data = {}

    rel_paths = {}

    # Create bus df
    data["bus"] = create_bus_element(selected_bus_attrs, select_regions)

    rel_paths["bus"] = os.path.join("data", elements_subdir, "bus" + ".csv")

    # Create component dfs
    for component, attrs in selected_component_attrs.items():

        data[component] = create_component_element(
            attrs, select_regions, select_links, facade_attrs
        )

        rel_paths[component] = os.path.join("data", elements_subdir, component + ".csv")

    # Create profile dfs
    def get_profile_rel_path(name):

        file_name = name.replace("-profile", "_profile") + ".csv"

        path = os.path.join("data", sequences_subdir, file_name)

        return path

    for component, attrs in selected_component_attrs.items():

        profile_data = create_component_sequences(
            attrs,
            select_regions,
            datetimeindex,
            dummy_sequences=dummy_sequences,
        )

        data.update(profile_data)

        rel_paths.update(
            {key: get_profile_rel_path(key) for key in profile_data.keys()}
        )

    return data, rel_paths


def select_from_node_attrs(node_attrs, select_nodes):
    def filter_dict_keys_by_list(dictionary, lst):
        result = {}
        for key in lst:
            result[key] = dictionary[key]
        return result

    if select_nodes is not None:
        undefined_nodes = set(select_nodes).difference(set(node_attrs))

        assert not undefined_nodes, f"Selected nodes {undefined_nodes} are not defined."

        selected_components = filter_dict_keys_by_list(node_attrs, select_nodes)

    else:
        selected_components = node_attrs

    return selected_components


def create_bus_element(bus_attrs, select_regions):
    r"""

    Parameters
    ----------
    busses_file : path
        Path to busses file.

    Returns
    -------
    bus_df : pd.DataFrame
        Bus element DataFrame
    """
    regions = []
    carriers = []
    balanced = []

    for region in select_regions:
        for carrier, attrs in bus_attrs.items():
            regions.append(region)
            carriers.append(region + "-" + carrier)
            balanced.append(attrs["balanced"])

    bus_df = pd.DataFrame(
        {"region": regions, "name": carriers, "type": "bus", "balanced": balanced}
    )

    bus_df = bus_df.set_index("name")

    return bus_df


def create_component_element(
    component_attrs, select_regions, select_links, facade_attrs
):
    r"""
    Takes dictionary for component attributes and returns a pd.DataFrame with the regions,
    links, names, references to profiles and default values.

    Parameters
    ----------
    component_attrs : dict
        Dcitionary with component attribute specifications.

    Returns
    -------
    component_df : pd.DataFrame
        DataFrame for the given component with default values filled.

    """
    # Collect default values and suffices for the component
    foreign_keys = component_attrs["foreign_keys"]

    def pop_keys(dictionary, keys):
        popped = {}

        for key in keys:
            popped[key] = dictionary.pop(key)

        return popped

    simple = ["carrier", "type", "tech"]

    simple_keys = pop_keys(component_attrs, simple)

    defaults = {}
    if "defaults" in component_attrs:
        defaults = component_attrs["defaults"]

    # load facade attrs
    facade_attr = facade_attrs.get_facade_attr(simple_keys["type"])

    comp_data = {key: None for key in facade_attr.index}

    comp_data.update(simple_keys)

    # Create dict for component data
    if simple_keys["type"] == "link":
        # TODO: Check the diverging conventions of '-' and '_' and think about unifying.
        comp_data["region"] = [link.replace("-", "_") for link in select_links]
        comp_data["name"] = [
            "-".join([link, simple_keys["carrier"], simple_keys["tech"]])
            for link in select_links
        ]
        comp_data["from_bus"] = [
            link.split("-")[0] + "-" + foreign_keys["from_bus"] for link in select_links
        ]
        comp_data["to_bus"] = [
            link.split("-")[1] + "-" + foreign_keys["to_bus"] for link in select_links
        ]

    else:
        comp_data["region"] = select_regions
        comp_data["name"] = [
            "-".join([region, simple_keys["carrier"], simple_keys["tech"]])
            for region in select_regions
        ]

        for key, value in foreign_keys.items():
            comp_data[key] = [region + "-" + value for region in select_regions]

    for key, value in defaults.items():
        comp_data[key] = value

    # sort the columns for comparability
    component_df = pd.DataFrame(comp_data).set_index("name")

    component_df = component_df[sorted(component_df.columns)]

    return component_df


def create_component_sequences(
    component_attrs,
    select_regions,
    datetimeindex,
    dummy_sequences=False,
    dummy_value=0,
):
    r"""

    Parameters
    ----------
    component_attrs : dict
        Dictionary describing the components' attributes

    select_regions : path
        Path where sequences are saved.

    datetimeindex : pd.DateTimeIndex
        Timeindex of the sequences

    dummy_sequences : bool
        If True, create a short timeindex and dummy values.

    dummy_value : numeric
        Dummy value for sequences.

    Returns
    -------
    profile_data : dict
        Dictionary containing profile DataFrames.
    """
    foreign_keys = component_attrs["foreign_keys"]

    profile_names = {k: v for k, v in foreign_keys.items() if "profile" in v}

    profile_data = {}

    for profile_name in profile_names.values():

        profile_columns = []

        profile_columns.extend(
            ["-".join([region, profile_name]) for region in select_regions]
        )

        if dummy_sequences:
            datetimeindex = pd.date_range(start="2020-10-20", periods=3, freq="H")

            profile_df = pd.DataFrame(
                dummy_value, index=datetimeindex, columns=profile_columns
            )

            dummy_msg = "dummy"

        else:
            profile_df = pd.DataFrame(columns=profile_columns, index=datetimeindex)

            dummy_msg = "empty"

        profile_df.index.name = "timeindex"

        profile_data[profile_name] = profile_df

        print(f"Created {dummy_msg} profile: '{profile_name}'.")

    return profile_data
