import os

import pandas as pd

from oemoflex.tools.helpers import load_yaml

module_path = os.path.dirname(os.path.abspath(__file__))


def create_default_data(
        select_regions,
        select_links,
        datetimeindex=None,
        select_components=None,
        select_busses=None,
        dummy_sequences=False,
        busses_file=os.path.join(module_path, 'busses.csv'),
        component_attrs_file=os.path.join(module_path, 'component_attrs.yml'),
        elements_subdir='elements',
        sequences_subdir='sequences',
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
        Path to a CSV file that defines the busses

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
    # load definitions
    component_attrs = load_yaml(component_attrs_file)

    defined_components = component_attrs.keys()

    defined_busses = pd.read_csv(busses_file, index_col='carrier')

    # TODO: Use only the busses necessary or defined.
    select_busses = select_from_df(select_busses, defined_busses)

    # select components or choose all if selection is None
    select_components = select_from_list(select_components, defined_components)

    # Create empty dictionaries for the dataframes and their relative paths in the datapackage.
    data = {}

    rel_paths = {}

    # Create bus df
    data['bus'] = create_bus_element(select_busses, select_regions)

    rel_paths['bus'] = os.path.join('data', elements_subdir, 'bus' + '.csv')

    # Create component dfs
    for component in select_components:

        specs = component_attrs[component]

        data[component] = create_component_element(specs, select_regions, select_links)

        rel_paths[component] = os.path.join('data', elements_subdir, component + '.csv')

    # Create profile dfs
    def get_profile_rel_path(name):

        file_name = name.replace('-profile', '_profile') + '.csv'

        path = os.path.join('data', sequences_subdir, file_name)

        return path

    for component in select_components:

        specs = component_attrs[component]

        profile_data = create_component_sequences(
            specs,
            select_regions,
            datetimeindex,
            dummy_sequences=dummy_sequences,
        )

        data.update(profile_data)

        rel_paths.update(
            {key: get_profile_rel_path(key) for key in profile_data.keys()}
        )

    return data, rel_paths


def select_from_df(select_busses, defined_busses):
    if select_busses:
        try:
            select_busses = defined_busses.loc[select_busses]
        except:
            print(f"Selected busses not defined.")
    else:
        select_busses = defined_busses

    return select_busses


def select_from_list(selected_components, defined_components):
    if selected_components is not None:
        undefined_nodes = set(selected_components).difference(set(defined_components))

        assert not undefined_nodes, \
            f"Selected nodes {undefined_nodes} are not defined."

    else:
        selected_components = defined_components

    return selected_components


def create_bus_element(select_busses, select_regions):
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
        for carrier, row in select_busses.iterrows():
            regions.append(region)
            carriers.append(region + '-' + carrier)
            balanced.append(row['balanced'])

    bus_df = pd.DataFrame({
        'region': regions,
        'name': carriers,
        'type': 'bus',
        'balanced': balanced
    })

    bus_df = bus_df.set_index('region')

    return bus_df


def create_component_element(component_attrs, select_regions, select_links):
    r"""
    Takes dictionary for component attribute specs and returns a pd.DataFrame with the regions,
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
    foreign_keys = component_attrs['foreign_keys']

    def pop_keys(dictionary, keys):
        popped = {}

        for key in keys:
            popped[key] = dictionary.pop(key)

        return popped

    simple = ['carrier', 'type', 'tech']

    simple_keys = pop_keys(component_attrs, simple)

    defaults = {}
    if 'defaults' in component_attrs:
        defaults = component_attrs['defaults']

    facade_attrs = pd.read_csv(
        os.path.join(module_path, 'facade_attrs', simple_keys['type'] + '.csv'),
        index_col=0,
        header=0
    )

    comp_data = {key: None for key in facade_attrs.index}

    comp_data.update(simple_keys)

    # Create dict for component data
    if simple_keys['type'] == 'link':
        # TODO: Check the diverging conventions of '-' and '_' and think about unifying.
        comp_data['region'] = [link.replace('-', '_') for link in select_links]
        comp_data['name'] = ['-'.join([link, simple_keys['carrier'], simple_keys['tech']]) for link in select_links]
        comp_data['from_bus'] = [link.split('-')[0] + '-' + foreign_keys['from_bus'] for link in select_links]
        comp_data['to_bus'] = [link.split('-')[1] + '-' + foreign_keys['to_bus'] for link in select_links]

    else:
        comp_data['region'] = select_regions
        comp_data['name'] = ['-'.join([region, simple_keys['carrier'], simple_keys['tech']]) for region in select_regions]

        for key, value in foreign_keys.items():
            comp_data[key] = [region + '-' + value for region in select_regions]

    for key, value in defaults.items():
        comp_data[key] = value

    component_df = pd.DataFrame(comp_data).set_index('region')

    return component_df


def create_component_sequences(
        component_attrs, select_regions, datetimeindex,
        dummy_sequences=False, dummy_value=0,
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
    foreign_keys = component_attrs['foreign_keys']

    profile_names = {k: v for k, v in foreign_keys.items() if 'profile' in v}

    profile_data = {}

    for profile_name in profile_names.values():

        profile_columns = []

        profile_columns.extend(['-'.join([region, profile_name]) for region in select_regions])

        if dummy_sequences:
            datetimeindex = pd.date_range(start='2020-10-20', periods=3, freq='H')

            profile_df = pd.DataFrame(dummy_value, index=datetimeindex, columns=profile_columns)

            dummy_msg = 'dummy'

        else:
            profile_df = pd.DataFrame(columns=profile_columns, index=datetimeindex)

            dummy_msg = 'empty'

        profile_df.index.name = 'timeindex'

        profile_data[profile_name] = profile_df

        print(f"Created {dummy_msg} profile: '{profile_name}'.")

    return profile_data
