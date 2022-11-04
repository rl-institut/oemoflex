import numpy as np
import pandas as pd
from oemof.solph import Bus, EnergySystem


def drop_component_to_component(series):
    r"""
    Drops those entries of an oemof_tuple indexed Series
    where both target and source are components.
    """
    _series = series.copy()

    component_to_component_ids = [
        id
        for id in series.index
        if not isinstance(id[0], Bus) and not isinstance(id[1], Bus)
    ]

    result = _series.drop(component_to_component_ids)

    return result


def get_component_id_in_tuple(oemof_tuple):
    r"""
    Returns the id of the component in an oemof tuple.
    If the component is first in the tuple, will return 0,
    if it is second, 1.

    Parameters
    ----------
    oemof_tuple : tuple
        tuple of the form (node, node) or (node, None).

    Returns
    -------
    component_id : int
        Position of the component in the tuple
    """
    if isinstance(oemof_tuple[1], Bus):
        component_id = 0

    elif oemof_tuple[1] is None:
        component_id = 0

    elif oemof_tuple[1] is np.nan:
        component_id = 0

    elif isinstance(oemof_tuple[0], Bus):
        component_id = 1

    return component_id


def get_component_from_oemof_tuple(oemof_tuple):
    r"""
    Gets the component from an oemof_tuple.

    Parameters
    ----------
    oemof_tuple : tuple

    Returns
    -------
    component : oemof.solph component
    """
    component_id = get_component_id_in_tuple(oemof_tuple)

    component = oemof_tuple[component_id]

    return component


def get_bus_from_oemof_tuple(oemof_tuple):
    r"""
    Gets the bus from an oemof_tuple.

    Parameters
    ----------
    oemof_tuple : tuple

    Returns
    -------
    bus : oemof.solph bus
    """
    if isinstance(oemof_tuple[0], Bus):
        bus = oemof_tuple[0]

    elif isinstance(oemof_tuple[1], Bus):
        bus = oemof_tuple[1]

    else:
        bus = None

    return bus


def filter_series_by_component_attr(df, **kwargs):
    r"""
    Filter a series by components attributes.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with oemof_tuple as index.

    kwargs : keyword arguments
        One or more component attributes

    Returns
    -------
    filtered_df : pd.DataFrame
    """
    filtered_index = []
    for id in df.index:
        component = get_component_from_oemof_tuple(id[:2])

        for key, value in kwargs.items():
            if not hasattr(component, key):
                continue

            if getattr(component, key) in value:
                filtered_index.append(id)

    filtered_df = df.loc[filtered_index]

    return filtered_df


def get_inputs(series):
    r"""
    Gets those entries of an oemof_tuple indexed DataFrame
    where the component is the target.
    """
    input_ids = [id for id in series.index if isinstance(id[0], Bus)]

    inputs = series.loc[input_ids]

    return inputs


def get_outputs(series):
    r"""
    Gets those entries of an oemof_tuple indexed DataFrame
    where the component is the source.
    """
    output_ids = [id for id in series.index if isinstance(id[1], Bus)]

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


def get_losses(summed_flows, var_name):
    r"""
    Calculate losses within components as the difference of summed input
    to output.
    """
    inputs = get_inputs(summed_flows)

    outputs = get_outputs(summed_flows)

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


def map_var_names(scalars):
    def get_component_id(id):

        component_id = get_component_id_in_tuple((id[0], id[1]))

        return component_id

    def get_carrier(id):
        bus = get_bus_from_oemof_tuple((id[0], id[1]))

        if bus:
            carrier = str.split(bus.label, "-")[1]

            return carrier

    def get_in_out(id, component_id):

        if not id[1] is np.nan:
            in_out = ["out", "in"][component_id]

            return in_out

    def get_from_to(id, component_id):
        from oemoflex.facades import Link

        if id[1] is np.nan:
            return None

        if not isinstance(id[component_id], Link):
            return None

        from_bus = id[component_id].from_bus

        to_bus = id[component_id].to_bus

        bus = get_bus_from_oemof_tuple(id)

        if bus == to_bus:
            in_out = "to_bus"

        elif bus == from_bus:
            in_out = "from_bus"

        return in_out

    def map_index(id):
        component_id = get_component_id(id)

        component = id[component_id]

        carrier = get_carrier(id)

        in_out = get_in_out(id, component_id)

        from_to = get_from_to(id, component_id)

        var_name = [id[2], in_out, carrier, from_to]

        var_name = [item for item in var_name if item is not None]

        var_name = "_".join(var_name)

        index = (component, None, var_name)

        return index

    scalars.index = scalars.index.map(map_index)

    scalars.index = scalars.index.droplevel(1)

    scalars.index.names = ("name", "var_name")

    return scalars


def add_component_info(scalars):
    def try_get_attr(x, attr):
        try:
            return getattr(x, attr)
        except AttributeError:
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
