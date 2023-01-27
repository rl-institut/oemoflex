import os

import numpy as np
import pandas
from pyomo import environ as po

import test_postprocessing


def equate_flows(model, flows1, flows2, factor1=1, name="equate_flows"):
    r"""
    Adds a constraint to the given model that sets the sum of two groups of
    flows equal or proportional by a factor.
    """

    def _equate_flow_groups_rule(m):
        for ts in m.TIMESTEPS:
            sum1_t = sum(m.flow[fi, fo, ts] for fi, fo in flows1)
            sum2_t = sum(m.flow[fi, fo, ts] for fi, fo in flows2)
            expr = sum1_t * factor1 == sum2_t
            if expr is not True:
                getattr(m, name).add(ts, expr)

    setattr(
        model,
        name,
        po.Constraint(model.TIMESTEPS, noruleinit=True),
    )
    setattr(
        model,
        name + "_build",
        po.BuildAction(rule=_equate_flow_groups_rule),
    )

    return model


def equate_flows_by_keyword(model, keyword1, keyword2, factor1=1, name="equate_flows"):
    r"""
    This wrapper for equate_flows allows to equate groups of flows by using a
    keyword instead of a list of flows.
    """
    flows = {}
    for n, keyword in enumerate([keyword1, keyword2]):
        flows[n] = []
        for (i, o) in model.flows:
            if hasattr(model.flows[i, o], keyword):
                flows[n].append((i, o))

    return equate_flows(model, flows[0], flows[1], factor1=factor1, name=name)


def drop_values_by_keyword(df, keyword="None"):
    """drops row if `var_value` is None"""
    drop_indices = df.loc[df.var_value == keyword].index
    df = df.drop(drop_indices)
    return df


def get_emission_limit(scalars):
    """Gets emission limit from scalars and returns None if it is missing or None."""
    emission_df_raw = scalars.loc[scalars["carrier"] == "emission"].set_index(
        "var_name"
    )
    emission_df = drop_values_by_keyword(emission_df_raw)

    # return None if no emission limit is given ('None' or entry missing)
    if emission_df.empty or emission_df.at["emission_limit", "var_value"] is np.nan:
        return None
    else:
        limit = emission_df.at["emission_limit", "var_value"]
        return limit


def get_electricity_gas_relations(scalars):
    r"""
    Gets electricity/gas relations from scalars. Returns None if no relations are given.
    Returns
    -------
    pd.DataFrame
        Contains rows of scalars with 'var_name' `EL_GAS_RELATION`
    If no relation is given returns None.
    """
    relations_raw = scalars.loc[scalars.var_name == "electricity_gas_relation"]
    # drop relations that are None
    relations = drop_values_by_keyword(relations_raw)
    if relations.empty:
        return None
    else:
        busses = relations.carrier.drop_duplicates().values  # noqaF841
        return relations


def get_bpchp_output_parameters(scalars):
    r"""Gets 'output_parameters' of backpressure CHPs from scalars and
    returns None if it is missing or None."""
    bpchp_outs_raw = scalars.loc[
        (scalars.tech == "bpchp") & (scalars.var_name == "output_parameters")
    ]

    # drop rows that have empty dict as var_value
    bpchp_outs = drop_values_by_keyword(bpchp_outs_raw, "{}")
    if bpchp_outs.empty:
        return None
    else:
        return bpchp_outs


def add_output_parameters_to_bpchp(parameters, energysystem):
    r"""
    Adds keywords for electricity-gas relation constraint to backpressure CHPs.
    This is necessary as oemof.tabular does not support `output_parameters` of these components,
    yet. The keywords are set as attributes of the output flow towards `heat_bus`.
    Parameters
    ----------
    parameters : pd.DataFrame
        Contains output_parameters of backpressure CHP scalars.
    energysystem : oemof.solph.network.EnergySystem
        The energy system
    """
    # rename column 'name' as is collides with iterrows()
    parameters.rename(columns={"name": "name_"}, inplace=True)
    for i, element in parameters.iterrows():
        if element.name_ in energysystem.groups:
            # get heat bus the component is connected to
            bus = energysystem.groups[element.name_].heat_bus

            # get keyword and boolean value
            split_str = element.var_value.split('"')
            keyword = split_str[1]
            value = bool(split_str[2].split("}")[0].split()[1])

            # set keyword as attribute with value
            setattr(
                energysystem.groups[element.name_].outputs.data[bus], keyword, value
            )
    return energysystem


def add_electricity_gas_relation_constraints(model, relations):
    r"""
    Adds constraint `equate_flows_by_keyword` to `model`.
    The components belonging to 'electricity' or 'gas' are selected by keywords. The keywords of
    components powered by gas start with `esys_conf.settings.optimize.gas_key` and such powered by
    electricity with `esys_conf.settings.optimize.el_key`, followed by `carrier` and `region` e.g.
    <`GAS_KEY`>-<carrier>-<region>.
    Parameters
    ----------
    model : oemof.solph.Model
        optmization model
    relations : pd.DataFrame
        Contains electricity/gas relations in column 'var_value'. Further contains at least columns
        'carrier' and 'region'.
    """
    for index, row in relations.iterrows():
        # Formulate suffix for keywords <carrier>-<region>
        suffix = f"{row.carrier}-{row.region}"
        equate_flows_by_keyword(
            model=model,
            keyword1=f"gas-{suffix}",
            keyword2=f"electricity-{suffix}",
            factor1=row.var_value,
            name=f"equate_flows_{suffix}",
        )


def get_additional_scalars(scenario):
    """Returns additional scalars as pd.DataFrame or None if file does not exist"""
    filename_add_scalars = str(
        test_postprocessing.TEST_FILES_DIR
        / scenario
        / "preprocessed"
        / "additional_scalars.csv"
    )
    if os.path.exists(filename_add_scalars):
        scalars = pandas.read_csv(filename_add_scalars, sep=";")
        scalars["var_value"] = pandas.to_numeric(
            scalars["var_value"], errors="coerce"
        ).fillna(scalars["var_value"])
        return scalars
    else:
        return None
