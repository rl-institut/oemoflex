import pandas as pd


def drop_component_to_component(series, busses):
    r"""
    Drops those entries of an oemof_tuple indexed Series
    where both target and source are components.
    """
    component_to_component_ids = [
        node for node in series.index if node[0] not in busses and node[1] not in busses
    ]
    result = series.drop(component_to_component_ids)
    return result


def get_component_id_in_tuple(oemof_tuple, busses):
    r"""
    Returns the id of the component in an oemof tuple.
    If the component is first in the tuple, will return 0,
    if it is second, 1.

    Parameters
    ----------
    oemof_tuple : tuple
        tuple of the form (node, node) or (node, None).
    busses : tuple
        tuple of bus names.

    Returns
    -------
    component_id : int
        Position of the component in the tuple
    """
    if oemof_tuple[0] in busses:
        return 1
    return 0


def get_component_from_oemof_tuple(oemof_tuple, busses):
    r"""
    Gets the component from an oemof_tuple.

    Parameters
    ----------
    oemof_tuple : tuple
    busses : tuple
        tuple of bus names.

    Returns
    -------
    component : oemof.solph component
    """
    component_id = get_component_id_in_tuple(oemof_tuple, busses)
    component = oemof_tuple[component_id]
    return component


def get_bus_from_oemof_tuple(oemof_tuple, busses):
    r"""
    Gets the bus from an oemof_tuple.

    Parameters
    ----------
    oemof_tuple : tuple
    busses : tuple

    Returns
    -------
    bus : oemof.solph bus
    """
    if oemof_tuple[0] in busses:
        return oemof_tuple[0]
    if oemof_tuple[1] in busses:
        return oemof_tuple[1]


def filter_series_by_component_attr(df, scalar_params, busses, **kwargs):
    r"""
    Filter a series by components attributes.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with oemof_tuple as index.
    scalar_params : pd.DataFrame
        DataFrame holding scalar params from oemof simulation.
    busses : tuple

    kwargs : keyword arguments
        One or more component attributes

    Returns
    -------
    filtered_df : pd.DataFrame
    """
    filtered_index = []
    for com in df.index:
        component = get_component_from_oemof_tuple(com[:2], busses)

        for key, value in kwargs.items():
            try:
                com_value = scalar_params[component, None, key]
            except IndexError:
                continue
            if com_value in value:
                filtered_index.append(com)

    filtered_df = df.loc[filtered_index]

    return filtered_df


def get_inputs(series, busses):
    r"""
    Gets those entries of an oemof_tuple indexed DataFrame
    where the component is the target.
    """
    input_ids = [node for node in series.index if node[0] in busses]
    inputs = series.loc[input_ids]
    return inputs


def get_outputs(series, busses):
    r"""
    Gets those entries of an oemof_tuple indexed DataFrame
    where the component is the source.
    """
    output_ids = [node for node in series.index if node[1] in busses]
    outputs = series.loc[output_ids]
    return outputs


def sum_flows(df):
    r"""
    Takes a multi-indexed DataFrame and returns the sum of
    the flows.
    """
    is_flow = df.columns.get_level_values(2) == "flow"
    df = df.loc[:, is_flow]
    df = df.sum()
    return df


def multiply_var_with_param(var, param):
    r"""
    Multiplies a variable (a result from oemof) with a
    parameter.
    """
    if param.empty or var.empty:
        return pd.Series(dtype="object")
    result = param * var
    result = result.loc[~result.isna()]
    return result


def set_index_level(series, level, value):
    r"""
    Sets a value to a multiindex level. If the level does not exist, it
    is appended.

    Parameters
    ----------
    series : pd.Series

    level : str
        Name of the level

    value : str
        Value to set

    Returns
    -------
    series : pd.Series
        Series with level set to value or appended level with value.
    """
    level_names = list(series.index.names)

    series.index.names = level_names

    df = pd.DataFrame(series)

    df.reset_index(inplace=True)

    df[level] = value

    if level not in level_names:
        level_names.append(level)

    df.set_index(level_names, inplace=True)

    series = df.loc[:, 0]

    return series


def filter_by_var_name(series, var_name):
    filtered_ids = series.index.get_level_values(2) == var_name
    filtered_series = series.loc[filtered_ids]
    return filtered_series


def group_by_element(scalars):
    elements = {}
    for group, df in scalars.groupby(["carrier", "tech"]):
        name = "-".join(group)

        df = df.reset_index()

        df = df.pivot(
            index=["name", "type", "carrier", "tech"],
            columns="var_name",
            values="var_value",
        )

        elements[name] = df

    return elements
