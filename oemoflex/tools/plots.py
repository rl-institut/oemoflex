import logging
import os
import warnings
from collections import OrderedDict

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from matplotlib.ticker import EngFormatter

import oemoflex.tools.helpers as helpers

pd.plotting.register_matplotlib_converters()

dir_name = os.path.abspath(os.path.dirname(__file__))

default_labels_dict = helpers.load_yaml(os.path.join(dir_name, "labels.yaml"))

colors_csv = pd.read_csv(
    os.path.join(dir_name, "colors.csv"), header=[0], index_col=[0]
)
colors_csv = colors_csv.T
default_colors_odict = OrderedDict()
for i in colors_csv.columns:
    default_colors_odict[i] = colors_csv.loc["Color", i]


def map_labels(df, labels_dict=None):
    r"""
    Renames columns according to the specifications in the label_dict. The data has multilevel
    column names. Thus, the labels_dict needs a tuple as key. The value is used as the new column
    name.

    Parameters
    ---------------
    df : pandas.DataFrame
        Dataframe with data.
    labels_dict : dictionary
        Contains old and new column names. The new column names are used for the labels in the
        plot.

    Returns
    ----------
    df : pandas.DataFrame
        Edited dataframe with new column names.
    """
    if labels_dict is None:
        labels_dict = default_labels_dict

    # rename columns
    df.columns = df.columns.to_flat_index()

    df.columns = _rename_by_string_matching(df.columns, labels_dict)

    return df


def _check_undefined_colors(labels, color_labels):
    undefined_colors = list(set(labels).difference(color_labels))

    if undefined_colors:
        raise KeyError(f"Undefined colors {undefined_colors}.")


def _rename_by_string_matching(columns, labels_dict):
    r"""
    The generic labels_dict needs to be adapted to the specific region which is investigated
    in order to rename the multilevel column names.

    Parameters
    ---------------
    columns : pandas.Index
        Column names which need to be adapted to a concise name.
    labels_dict : dictionary
        Contains old and new column names. The new column names are used for the labels in the
        plot.

    Returns
    ----------
    renamed_columns : list
        List with new column names.
    """

    def map_tuple(tupl, dictionary):
        r"""
        The corresponding value of the tuple which is supposed to be a key in the dictionary is
        retrieved.

        Parameters
        ---------------
        tuple : tuple
            Multilevel column name as tuple which needs to be adapted to a concise name.
        dictionary : dictionary
            Contains old and new column names. The new column names are used for the labels in the
            plot.

        Returns
        ----------
        mapped : string
            String with new column name.
        """
        mapped = {
            key: value
            for key, value in dictionary.items()
            if any([key in y for y in tupl])
        }

        if not mapped:
            warnings.warn(f"No label matches for {tupl}. Could not map.")
            return str(tupl)
        elif len(mapped) == 1:
            mapped = list(mapped.values())[0]
        elif len(mapped) > 1:
            logging.info(f"Found multiple matches for {tupl}: {mapped.values()}")
            # map to longest key
            longest_key = max(mapped, key=lambda x: len(x))
            mapped = mapped[longest_key]
            logging.info(f"Mapped {tupl} to {mapped}")
        return mapped

    def rename_duplicated(columns_tuple, columns_mapped, dictionary):
        r"""
        Appends a suffix to those columns that are not unique. This happens in
        oemof because a component can appear as the first or second entry in a tuple, which
        signifies the output or input of the component, respectively.
        """
        columns_duplicated = columns_mapped.duplicated(keep=False)

        mapped_where = [
            j
            for tupl in columns_tuple
            for j, x in enumerate(tupl)
            if any([key in x for key in dictionary.keys()])
        ]

        mapped_where = pd.Series(mapped_where)

        if (columns_duplicated & (mapped_where == 0)).any():
            columns_mapped.loc[columns_duplicated & (mapped_where == 0)] += " out"

        if (columns_duplicated & (mapped_where == 1)).any():
            columns_mapped.loc[columns_duplicated & (mapped_where == 1)] += " in"

        return columns_mapped

    def map_str(string, dictionary):

        mapped = [value for key, value in dictionary.items() if key in string]

        if len(mapped) > 1:
            raise ValueError(f"Multiple labels are matching for {string}: {mapped}")
        elif not mapped:
            warnings.warn(f"No label matches for {string}. Could not map.")
            return string
        else:
            mapped = mapped[0]

        return mapped

    # Map column names
    if all([isinstance(col, tuple) for col in columns]):
        renamed_columns = pd.Series(map(lambda x: map_tuple(x, labels_dict), columns))

        # If there are duplicates, append in/out
        renamed_columns = rename_duplicated(columns, renamed_columns, labels_dict)

    elif all([isinstance(col, str) for col in columns]):
        renamed_columns = pd.Series(map(lambda x: map_str(x, labels_dict), columns))

    else:
        raise ValueError("Cannot rename. Columns should be tuples or strings.")

    return renamed_columns


def _group_agg_by_column(df):
    r"""
    Columns with the same name are grouped together and aggregated.
    e.g. needed to group the Import and Export columns if there are
    multiple because the region has electricity transmission with multiple other regions.

    Parameters
    ---------------
    df : pandas.DataFrame
        Dataframe with data.

    Returns
    ----------
    df_grouped : pandas.DataFrame
        Dataframe with grouped data.
    """
    df_grouped = df.groupby(by=df.columns, axis=1).sum()

    return df_grouped


def _replace_near_zeros(df, tolerance=1e-3):
    r"""
    Due to numerical reasons, values are sometime really small, e.g. 1e-8, instead of zero.
    All values which are smaller than a defined tolerance are replaced by 0.0.

    Parameters
    ---------------
    df : pandas.DataFrame
        Dataframe with data.

    Returns
    ----------
    df : pandas.DataFrame
        DataFrame with replaced near zeros.
    """
    df[abs(df) < tolerance] = 0.0
    return df


def prepare_dispatch_data(df, bus_name, demand_name, labels_dict=None):
    r"""
    The data in df is split into a DataFrame with consumers and generators and a DataFrame which
    only contains the demand data. Consumer data is made negative. The multilevel column names are
    replaced by more simple names. Columns the same name are grouped together. Really small
    numerical values which are practically zero are replaced with 0.0.

    Parameters
    ---------------
    df : pandas.DataFrame
        Dataframe with data.
    bus_name : string
        name of the main bus to which all other are connected, e.g. the "BB-electricity" bus.
    demand_name: string
        Name of the bus representing the demand.
    labels_dict : dict
        Dictionary to map the column labels.

    Returns
    ----------
    df : pandas.DataFrame
        DataFrame with prepared data for dispatch plotting of consumers and generators.
    df_demand: pandas.DataFrame
        DataFrame with prepared data for dispatch plotting of demand.
    """
    _df = df.copy()

    if labels_dict is None:
        labels_dict = default_labels_dict

    # identify consumers, which shall be plotted negative and
    # isolate column with demand and make its data positive again
    _df.columns = _df.columns.to_flat_index()
    for i in _df.columns:
        if i[0] == bus_name:
            _df[i] = _df[i] * -1
        if demand_name in i[1]:
            df_demand = (_df[i] * -1).to_frame()
            _df.drop(columns=[i], inplace=True)

    # rename column names to match labels
    _df = map_labels(_df, labels_dict)
    df_demand = map_labels(df_demand, labels_dict)

    # group columns with the same name, e.g. transmission busses by import and export
    _df = _group_agg_by_column(_df)
    # check columns on numeric values which are practical zero and replace them with 0.0
    _df = _replace_near_zeros(_df)

    return _df, df_demand


def filter_timeseries(df, start_date=None, end_date=None):
    r"""
    Filters a dataframe with a timeseries from a start date to an end date.
    If start_date or end_date are not given, filtering is done from the first
    available date or to the last available date.

    Parameters
    ---------------
    df : pandas.DataFrame
        Dataframe with timeseries.
    start_date : string
        String with the start date for filtering in the format 'YYYY-MM-DD hh:mm:ss'.
    end_date : string
        String with the end date for filtering in the format 'YYYY-MM-DD hh:mm:ss'.

    Returns
    ----------
    df_filtered : pandas.DataFrame
        Filtered dataframe.
    """
    assert isinstance(df.index, pd.DatetimeIndex), "Index should be DatetimeIndex"
    df_filtered = df.copy()
    df_filtered = df_filtered.loc[start_date:end_date]

    return df_filtered


def _assign_stackgroup(key, values):
    r"""
    This function decides if data is supposed to be plotted on the positive or negative side of
    the stackplot. If values has both negative and positive values, a value error is raised.

    Parameters
    ---------------
    key : string
        Column name.
    values: pandas.Series
        Values of column.

    Returns
    ----------
    stackgroup : string
        String with keyword positive or negative.
    """
    if all(values <= 0):
        stackgroup = "negative"
    elif all(values >= 0):
        stackgroup = "positive"
    elif all(values == 0):
        stackgroup = "positive"
    else:
        raise ValueError(
            key,
            " has both, negative and positive values. But it should only have either one",
        )

    return stackgroup


def stackplot(ax, df, colors_odict):
    r"""
    Plots data as a stackplot. The stacking order is determined by the order
    of labels in the colors_odict. It is stacked beginning with the x-axis as
    the bottom.

    Parameters
    ---------------
    ax : matplotlib.AxesSubplot
        Axis on which data is plotted.
    df : pandas.DataFrame
        Dataframe with data.
    colors_odict : collections.OrderedDictionary
        Ordered dictionary with labels as keys and colourcodes as values.
    """
    assert not df.empty, "Dataframe is empty."

    _check_undefined_colors(df.columns, colors_odict.keys())

    # y is a list which gets the correct stack order from colors file
    colors = []
    labels = []
    y = []

    order = list(colors_odict)

    for i in order:
        if i not in df.columns:
            continue
        labels.append(i)
        colors.append(colors_odict[i])
        y.append(df[i])

    y = np.vstack(y)
    ax.stackplot(df.index, y, colors=colors, labels=labels)


def lineplot(ax, df, colors_odict, linewidth=1):
    r"""
    Plots data as a lineplot.

    Parameters
    ---------------
    ax : matplotlib.AxesSubplot
        Axis on which data is plotted.
    df : pandas.DataFrame
        Dataframe with data.
    colors_odict : collections.OrderedDictionary
        Ordered dictionary with labels as keys and colourcodes as values.
    linewidth: float
        Width of the line - set by default to 1.
    """
    _check_undefined_colors(df.columns, colors_odict.keys())

    for i in df.columns:
        ax.plot(df.index, df[i], color=colors_odict[i], linewidth=linewidth, label=i)


def plot_dispatch(ax, df, df_demand, unit, colors_odict=None, linewidth=1):
    r"""
    Plots data as a dispatch plot. The demand is plotted as a line plot and
    suppliers and other consumers are plotted with a stackplot. Columns with negative vlaues
    are stacked below the x axis and columns with positive values above.

    Parameters
    ---------------
    ax : matplotlib.AxesSubplot
        Axis on which data is plotted.
    df : pandas.DataFrame
        Dataframe with data except demand.
    df_demand : pandas.DataFrame
        Dataframe with demand data.
    unit: string
        String with unit sign of plotted data on y-axis.
    colors_odict : collections.OrderedDictionary
        Ordered dictionary with labels as keys and colourcodes as values.
    linewidth: float
        Width of the line - set by default to 1.
    """
    assert not df.empty, "DataFrame is empty. Cannot plot empty data."
    assert (
        not df.columns.duplicated().any()
    ), "Cannot plot DataFrame with duplicate columns."

    if colors_odict is None:
        colors_odict = default_colors_odict

    _check_undefined_colors(df.columns, colors_odict.keys())

    # apply EngFormatter on axis
    ax = _eng_format(ax, unit=unit)

    # plot stackplot, differentiate between positive and negative stacked data
    y_stack_pos = []
    y_stack_neg = []

    # assign data to positive or negative stackplot
    for key, values in df.items():
        stackgroup = _assign_stackgroup(key, values)
        if stackgroup == "negative":
            y_stack_neg.append(key)
        elif stackgroup == "positive":
            y_stack_pos.append(key)

    for i in y_stack_pos:
        if df[i].isin([0]).all():
            y_stack_pos.remove(i)

    # plot if there is positive data
    if not df[y_stack_pos].empty:
        stackplot(ax, df[y_stack_pos], colors_odict)

    # plot if there is negative data
    if not df[y_stack_neg].empty:
        stackplot(ax, df[y_stack_neg], colors_odict)

    # plot lineplot (demand)
    lineplot(ax, df_demand, colors_odict, linewidth)


def plot_dispatch_plotly(
    df,
    df_demand,
    unit,
    colors_odict=None,
):
    r"""
    Plots data as a dispatch plot in an interactive plotly plot. The demand is plotted as a
    line plot and suppliers and other consumers are plotted with a stackplot.

    Parameters
    ---------------
    df : pandas.DataFrame
        Dataframe with data except demand.
    df_demand : pandas.DataFrame
        Dataframe with demand data.
    unit: string
        String with unit sign of plotted data on y-axis.
    colors_odict : collections.OrderedDictionary
        Ordered dictionary with labels as keys and colourcodes as values.

    Returns
    ----------
    fig : plotly.graph_objs._figure.Figure
        Interactive plotly dispatch plot
    """
    if colors_odict is None:
        colors_odict = default_colors_odict

    _check_undefined_colors(df.columns, colors_odict.keys())

    # make sure to obey order as definded in colors_odict
    generic_order = list(colors_odict)
    concrete_order = generic_order.copy()
    for i in generic_order:
        if i not in df.columns:
            concrete_order.remove(i)
    df = df[concrete_order]

    # plotly figure
    fig = go.Figure()

    # plot stacked generators and consumers
    df = df[[c for c in df.columns if not isinstance(c, tuple)]]
    for key, values in df.items():
        stackgroup = _assign_stackgroup(key, values)

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=values,
                mode="lines",
                stackgroup=stackgroup,
                line=dict(width=0, color=colors_odict[key]),
                name=key,
            )
        )

    # plot demand line
    fig.add_traces(
        go.Scatter(
            x=df_demand.index,
            y=df_demand.iloc[:, 0],
            mode="lines",
            line=dict(width=2, color=colors_odict[df_demand.columns[0]]),
            name=df_demand.columns[0],
        )
    )

    fig.update_layout(
        hovermode="x unified",
        font=dict(family="Aleo"),
        xaxis=dict(
            rangeselector=dict(
                buttons=list(
                    [
                        dict(count=1, label="1m", step="month", stepmode="backward"),
                        dict(count=6, label="6m", step="month", stepmode="backward"),
                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                        dict(count=1, label="1y", step="year", stepmode="backward"),
                        dict(step="all"),
                    ]
                )
            ),
            rangeslider=dict(visible=True),
            type="date",
        ),
        xaxis_title="Date",
        yaxis_title="Power",
    )

    # Scale power data on y axis with SI exponents
    fig.update_yaxes(exponentformat="SI", ticksuffix=unit)

    return fig


def _eng_format(ax, unit):
    r"""
    Applies the EngFormatter to y-axis.

    Parameters
    ---------------
    ax : matplotlib.AxesSubplot
        Axis on which data is plotted.
    unit : string
        Unit which is plotted on y-axis

    Returns
    ----------
    ax : matplotlib.AxesSubplot
        Axis with formatter set to EngFormatter
    """
    formatter0 = EngFormatter(unit=unit)
    ax.yaxis.set_major_formatter(formatter0)
    return ax


def plot_grouped_bar(ax, df, color_dict, unit, stacked=False):
    r"""
    This function plots scalar data as grouped bar plot. The index of the DataFrame
    will be interpreted as groups (e.g. regions), the columns as different categories (e.g. energy
    carriers) within the groups which will be plotted in different colors.

    Parameters
    ----------
    ax: matplotlib Axes object
        Axes to draw the plot.
    df: pd.DataFrame
        DataFrame with an index defining the groups and columns defining the bars of different color
        within the group.
    color_dict: dict
        Dictionary defining colors of the categories
    unit: str
        Unit of the variables.
    stacked : boolean
        Stack bars of a group. False by default.
    """
    alpha = 0.3
    # apply EngFormatter if power is plotted
    ax = _eng_format(ax, unit)

    df.plot.bar(
        ax=ax,
        color=[color_dict[key] for key in df.columns],
        width=0.8,
        zorder=2,
        stacked=stacked,
        rot=0,
    )

    ax.minorticks_on()
    ax.tick_params(axis="both", which="both", length=0, pad=7)

    ax.grid(axis="y", zorder=1, color="black", alpha=alpha)
    ax.grid(axis="y", which="minor", zorder=1, color="darkgrey", alpha=alpha)
    ax.set_xlabel(xlabel=None)
    ax.legend()
    ax.legend(title=None, frameon=True, framealpha=1)

    return ax
