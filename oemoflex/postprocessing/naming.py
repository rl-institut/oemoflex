import numpy as np
import pandas as pd

from oemoflex.postprocessing.helper import get_bus_from_oemof_tuple, get_component_id_in_tuple


DEFAULT_COMPONENT_INFOS = ("region", "type", "carrier", "tech")


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


def add_component_info(scalars, scalar_params, attributes=DEFAULT_COMPONENT_INFOS):
    def try_get_attr(x, attr):
        try:
            return scalar_params[x, None, attr]
        except IndexError:
            return None

    scalars.name = "var_value"
    scalars = pd.DataFrame(scalars)

    for attribute in attributes:
        scalars[attribute] = scalars.index.get_level_values(0).map(
            lambda x: try_get_attr(x, attribute)
        )

    return scalars
