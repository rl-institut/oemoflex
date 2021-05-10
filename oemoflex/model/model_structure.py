import os

import pandas as pd

module_path = os.path.dirname(os.path.abspath(__file__))


def create_default_data(
        select_regions,
        select_links,
        datetimeindex=None,
        select_components=None,
        select_busses=None,
        dummy_sequences=False,
        busses_file=os.path.join(module_path, 'busses.csv'),
        components_file=os.path.join(module_path, 'components.csv'),
        component_attrs_dir=os.path.join(module_path, 'component_attrs'),
        elements_subdir='elements',
        sequences_subdir='sequences',
):
    r"""
    Prepares oemoef.tabluar input CSV files:
    * includes headers according to definitions in CSVs in directory 'component_attrs_dir'
    * pre-define all oemof elements (along CSV rows) without actual dimensions/values

    Parameters
    ----------
    destination : str (dir path)
        target directory where to put the prepared CSVs

    components_file : str (file path)
        CSV where to read the components from

    component_attrs_dir : str (dir path)
        CSV where to read the components' attributes from

    select_components : list
        List of default elements to create

    Returns
    -------
    None
    """
    components_file = os.path.join(module_path, components_file)

    # TODO Better put this as another field into the components.csv as well?
    component_attrs_dir = os.path.join(module_path, component_attrs_dir)

    components = pd.read_csv(components_file).name.values

    if select_components is not None:
        undefined_components = set(select_components).difference(set(components))

        assert not undefined_components,\
            f"Selected components {undefined_components} are not in components."

        components = [c for c in components if c in select_components]

    data = {}

    bus_df = create_bus_element(busses_file, select_busses, select_regions)

    data['bus'] = bus_df

    for component in components:
        component_attrs_file = os.path.join(component_attrs_dir, component + '.csv')

        df = create_component_element(component_attrs_file, select_regions, select_links)

        # Write to target directory
        data[component] = df

    rel_paths = {key: os.path.join('data', elements_subdir, key + '.csv') for key in data.keys()}

    for component in components:
        component_attrs_file = os.path.join(component_attrs_dir, component + '.csv')

        profile_data = create_component_sequences(
            component_attrs_file,
            select_regions,
            datetimeindex,
            dummy_sequences=dummy_sequences,
        )

        def get_profile_rel_path(name):

            file_name = name.replace('-profile', '_profile') + '.csv'

            path = os.path.join('data', sequences_subdir, file_name)

            return path

        rel_paths.update(
            {key: get_profile_rel_path(key) for key in profile_data.keys()}
        )

        data.update(profile_data)

    return data, rel_paths


def create_bus_element(busses_file, select_busses, select_regions):
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
    busses = pd.read_csv(busses_file, index_col='carrier')

    if select_busses:
        busses = busses.loc[select_busses]

    regions = []
    carriers = []
    balanced = []

    for region in select_regions:
        for carrier, row in busses.iterrows():
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


def create_component_element(component_attrs_file, select_regions, select_links):
    r"""
    Loads file for component attribute specs and returns a pd.DataFrame with the right regions,
    links, names, references to profiles and default values.

    Parameters
    ----------
    component_attrs_file : path
        Path to file with component attribute specifications.

    Returns
    -------
    component_df : pd.DataFrame
        DataFrame for the given component with default values filled.

    """
    try:
        component_attrs = pd.read_csv(component_attrs_file, index_col=0)

    except FileNotFoundError as e:
        raise FileNotFoundError(f"There is no file {component_attrs_file}") from e

    # Collect default values and suffices for the component
    defaults = component_attrs.loc[component_attrs['default'].notna(), 'default'].to_dict()

    suffices = component_attrs.loc[component_attrs['suffix'].notna(), 'suffix'].to_dict()

    comp_data = {key: None for key in component_attrs.index}

    # Create dict for component data
    if defaults['type'] == 'link':
        # TODO: Check the diverging conventions of '-' and '_' and think about unifying.
        comp_data['region'] = [link.replace('-', '_') for link in select_links]
        comp_data['name'] = select_links
        comp_data['from_bus'] = [link.split('-')[0] + suffices['from_bus'] for link in select_links]
        comp_data['to_bus'] = [link.split('-')[1] + suffices['to_bus'] for link in select_links]

    else:
        comp_data['region'] = select_regions
        comp_data['name'] = [region + suffices['name'] for region in select_regions]

        for key, value in suffices.items():
            comp_data[key] = [region + value for region in select_regions]

    for key, value in defaults.items():
        comp_data[key] = value

    component_df = pd.DataFrame(comp_data).set_index('region')

    return component_df


def create_component_sequences(
        component_attrs_file, select_regions, datetimeindex,
        dummy_sequences=False, dummy_value=0,
):
    r"""

    Parameters
    ----------
    component_attrs_file : path
        Path to file describing the components' attributes

    destination : path
        Path where sequences are saved.

    dummy_sequences : bool
        If True, create a short timeindex and dummy values.

    dummy_value : numeric
        Dummy value for sequences.

    Returns
    -------
    None
    """
    try:
        component_attrs = pd.read_csv(component_attrs_file, index_col=0)

    except FileNotFoundError as e:
        raise FileNotFoundError(f"There is no file {component_attrs_file}") from e

    suffices = component_attrs.loc[component_attrs['suffix'].notna(), 'suffix'].to_dict()

    def remove_prefix(string, prefix):
        if string.startswith(prefix):
            return string[len(prefix):]

    def remove_suffix(string, suffix):
        if string.endswith(suffix):
            return string[:-len(suffix)]

    profile_names = {k: remove_prefix(v, '-') for k, v in suffices.items() if 'profile' in v}

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
