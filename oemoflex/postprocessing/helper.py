import numpy as np
import pandas as pd
from functools import partial
from oemof.solph import Bus, EnergySystem


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


def substract_output_from_input(inputs, outputs, var_name):
    r"""
    Calculates the differences of output from input.
    """

    def reduce_component_index(series, level):

        _series = series.copy()

        _series.name = "var_value"

        _df = pd.DataFrame(_series)

        _df.reset_index(inplace=True)

        _df = _df[[level, "var_value"]]

        _df.set_index(level, inplace=True)

        return _df

    _inputs = reduce_component_index(inputs, "target")

    _outputs = reduce_component_index(outputs, "source")

    losses = _inputs - _outputs

    losses.index.name = "source"

    losses.reset_index(inplace=True)

    losses["target"] = np.nan

    losses["var_name"] = var_name

    losses.set_index(["source", "target", "var_name"], inplace=True)

    losses = losses["var_value"]  # Switching back to series.
    # TODO: Use DataFrame or Series more consistently.

    return losses


def get_losses(summed_flows, var_name, busses):
    r"""
    Calculate losses within components as the difference of summed input
    to output.
    """
    inputs = get_inputs(summed_flows, busses)
    outputs = get_outputs(summed_flows, busses)
    inputs = inputs.groupby("target").sum()
    outputs = outputs.groupby("source").sum()
    losses = substract_output_from_input(inputs, outputs, var_name)
    return losses


def index_to_str(index):
    r"""
    Converts multiindex labels to string.
    """
    index = index.map(lambda tupl: tuple(str(node) for node in tupl))
    return index


def reindex_series_on_index(series, index_b):
    r"""
    Reindexes series on new index containing objects that have the same string
    representation. A workaround necessary because oemof.solph results and params
    have differences in the objects of the indices, even if their label is the same.
    """
    _index_b = index_b.copy()

    _series = series.copy()

    _index_b = index_to_str(_index_b)

    _series.index = index_to_str(_series.index)

    _series = _series.reindex(_index_b)

    _series.index = index_b

    _series = _series.loc[~_series.isna()]

    return _series


def multiply_var_with_param(var, param):
    r"""
    Multiplies a variable (a result from oemof) with a
    parameter.
    """
    param = reindex_series_on_index(param, var.index)

    result = param * var

    result = result.loc[~result.isna()]

    return result


def get_summed_variable_costs(summed_flows, scalar_params):

    variable_costs = filter_by_var_name(scalar_params, "variable_costs").unstack(2)[
        "variable_costs"
    ]

    variable_costs = variable_costs.loc[variable_costs != 0]

    summed_flows = summed_flows.unstack(2).loc[:, "flow"]

    summed_variable_costs = multiply_var_with_param(summed_flows, variable_costs)

    summed_variable_costs = set_index_level(
        summed_variable_costs, level="var_name", value="summed_variable_costs"
    )

    return summed_variable_costs


def get_total_system_cost(*args):

    all_costs = pd.concat(args)

    index = pd.MultiIndex.from_tuples([("system", "total_system_cost")])

    total_system_cost = pd.DataFrame({"var_value": [all_costs.sum()]}, index=index)

    return total_system_cost


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


def map_var_names(scalars, scalar_params, busses, links):
    def get_carrier(node):
        bus = get_bus_from_oemof_tuple((node[0], node[1]), busses)
        if bus:
            carrier = str.split(bus, "-")[1]
            return carrier

    def get_in_out(node, component_id):
        if not node[1] is np.nan:
            in_out = ["out", "in"][component_id]

            return in_out

    def get_from_to(node, component_id):
        if node[1] is np.nan:
            return None
        if node[component_id] not in links:
            return None

        from_bus = scalar_params[node[component_id], None, "from_bus"].label
        to_bus = scalar_params[node[component_id], None, "to_bus"].label
        bus = get_bus_from_oemof_tuple(node, busses)
        if bus == to_bus:
            return "to_bus"
        if bus == from_bus:
            return "from_bus"

    def map_index(node):
        component_id = get_component_id_in_tuple(node, busses)

        component = node[component_id]

        carrier = get_carrier(node)

        in_out = get_in_out(node, component_id)

        from_to = get_from_to(node, component_id)

        var_name = [node[2], in_out, carrier, from_to]

        var_name = [item for item in var_name if item is not None]

        var_name = "_".join(var_name)

        index = (component, None, var_name)

        return index

    scalars.index = scalars.index.map(map_index)
    scalars.index = scalars.index.droplevel(1)
    scalars.index.names = ("name", "var_name")
    return scalars


def add_component_info(scalars, scalar_params):
    def try_get_attr(x, attr):
        try:
            return scalar_params[x, None, attr]
        except IndexError:
            return None

    scalars.name = "var_value"

    scalars = pd.DataFrame(scalars)

    for attribute in ["region", "type", "carrier", "tech"]:
        scalars[attribute] = scalars.index.get_level_values(0).map(
            lambda x: try_get_attr(x, attribute)
        )

    return scalars


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


def sort_scalars(scalars):

    scalars = scalars.sort_values(by=["carrier", "tech", "var_name"])

    return scalars


def restore_es(path):
    r"""
    Restore EnergySystem with results
    """
    es = EnergySystem()

    es.restore(path)

    return es
