import numpy as np
import pandas as pd
import os
import plotly.graph_objects as go
from collections import OrderedDict
from matplotlib.ticker import EngFormatter
import oemoflex.tools.helpers as helpers

pd.plotting.register_matplotlib_converters()

dir_name = os.path.abspath(os.path.dirname(__file__))

general_labels_dict = helpers.load_yaml(os.path.join(dir_name, "labels.yaml"))

colors_csv = pd.read_csv(
    os.path.join(dir_name, "colors.csv"), header=[0], index_col=[0]
)
colors_csv = colors_csv.T
colors_odict = OrderedDict()
for i in colors_csv.columns:
    colors_odict[i] = colors_csv.loc["Color", i]


def map_labels(df, labels_dict):
    r"""
    Renames columns according to the specifications in the label_dict. The data has multilevel
    column names. Thus, the labels_dict needs a tuple as key. The value is used as the new column
    name.

    Parameters
    ---------------
    df : pandas.DataFrame
        Dataframe with data.
    labels_dict : dictionary
        Contains old and new column names. The new column names are used for the labels in the plot.

    Returns
    ----------
    df : pandas.DataFrame
        Edited dataframe with new column names.
    """
    # rename columns
    df.columns = df.columns.to_flat_index()

    df.columns = rename_by_string_matching(df.columns, labels_dict)

    return df


def rename_by_string_matching(columns, labels_dict):
    r"""
    The generic labels_dict needs to be adapted to the specific region which is investigated
    in order to rename the multilevel column names.

    Parameters
    ---------------
    columns : pandas.Index
        Column names which need to be adapted to a concise name.
    labels_dict : dictionary
        Contains old and new column names. The new column names are used for the labels in the plot.

    Returns
    ----------
    renamed_columns : list
        List with new column names.
    """
    def map_tuple(tuple, dictionary):
        r"""
        The corresponding value of the tuple which is supposed to be a key in the dictionary is retrieved.

        Parameters
        ---------------
        tuple : tuple
            Multilevel column name as tuple which needs to be adapted to a concise name.
        dictionary : dictionary
            Contains old and new column names. The new column names are used for the labels in the plot.

        Returns
        ----------
        mapped : string
            String with new column name.
        """
        mapped = None

        for key, value in dictionary.items():

            if concrete_in_generic(tuple, key):
                mapped = value

            else:
                continue

        if not mapped:
            raise KeyError(f"No mapping defined for {col}.")

        return mapped

    def concrete_in_generic(concrete_tuple, generic_tuple):
        r"""
        It is checked if the concrete_tuple is contained in the generic_tuple which is a key of
        the labels_dict. Thus, it is checked if a multilevel column name is contained in the labels_dict.

        Parameters
        ---------------
        concrete_tuple : tuple
            Column names which need to be adapted to a concise name.
        generic_tuple : tuple
            Contains old and new column names. The new column names are used for the labels in the plot.

        Returns
        ----------
        True or False : Boolean
            Boolean whether concrete_tuple is contained in generic_tuple.
        """
        for concrete, generic in zip(concrete_tuple, generic_tuple):
            if generic in concrete:
                continue

            else:
                return False

        return True

    renamed_columns = list()

    for col in columns:

        renamed_col = map_tuple(col, labels_dict)

        renamed_columns.append(renamed_col)

    return renamed_columns


def group_agg_by_column(df):
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


def stackplot(ax, df, colors_odict=colors_odict):
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


def plot_dispatch_plotly(df, bus_name, demand_name, colors_odict=colors_odict):

    # identify consumers, which shall be plotted negative and
    # isolate column with demand and make its data positive again
    df.columns = df.columns.to_flat_index()
    for i in df.columns:
        if i[0] == bus_name:
            df[i] = df[i] * -1
        if i[1] == demand_name:
            df_demand = (df[i] * -1).to_frame()
            df.drop(columns=[i], inplace=True)

    # rename column names to match labels
    df = map_labels(df, general_labels_dict)
    df_demand = map_labels(df_demand, general_labels_dict)

    # group transmission busses by import and export
    df = group_agg_by_column(df)

    traces = list()

    df = df[[c for c in df.columns if not isinstance(c, tuple)]]
    print(df)
    print(df_demand)
    for key, values in df.iteritems():

        traces.append(
            dict(
                x=df.index,
                y=values,
                mode='lines',
                stackgroup='one',
                line=dict(
                    width=1, color=colors_odict[key]
                ),
                name=key,
                # fill_color=colors_odict[key]
            )
        )
    # plot demand line
    traces.append(
        dict(
            x=df_demand.index,
            y=df_demand.iloc[:,0],
            mode='lines',
            line=dict(
                width=1, color=colors_odict[df_demand.columns[0]]
            ),
            name=df_demand.columns[0],
            # fill_color=colors_odict[key]
        )
    )

    layout = dict(font=dict(family='Aleo'))

    fig = dict(data=traces, layout=layout)

    fig = go.Figure(fig)

    return fig


def lineplot(ax, df, colors_odict=colors_odict):
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
    """
    for i in df.columns:
        ax.plot(df.index, df[i], color=colors_odict[i], label=i)


def plot_dispatch(
    ax, df, bus_name, start_date=None, end_date=None, demand_name="demand"
):
    r"""
    Plots data as a dispatch plot. The demand is plotted as a line plot and
    suppliers and other consumers are plottes with a stackplot.

    Parameters
    ---------------
    ax : matplotlib.AxesSubplot
        Axis on which data is plotted.
    df : pandas.DataFrame
        Dataframe with data.
    bus_name : string
        name of the main bus to which all other are connected, e.g. the "BB-electricity" bus.
    start_date : string
        String with the start date for filtering in the format 'YYYY-MM-DD hh:mm:ss'.
    end_date : string
        String with the end date for filtering in the format 'YYYY-MM-DD hh:mm:ss'.
    demand_name: string
        Name of the bus representing the demand.
    """
    df = filter_timeseries(df, start_date, end_date)

    # identify consumers, which shall be plotted negative and
    # isolate column with demand and make its data positive again
    df.columns = df.columns.to_flat_index()
    for i in df.columns:
        if i[0] == bus_name:
            df[i] = df[i] * -1
        if demand_name in i[1]:
            df_demand = (df[i] * -1).to_frame()
            df.drop(columns=[i], inplace=True)

    # rename column names to match labels
    df = map_labels(df, general_labels_dict)
    df_demand = map_labels(df_demand, general_labels_dict)

    # group transmission busses by import and export
    df = group_agg_by_column(df)

    # plot stackplot, differentiate between positive and negative stacked data
    y_stack_pos = []
    y_stack_neg = []
    for index, value in (df < 0).any().items():
        if value == True:
            y_stack_neg.append(index)
        else:
            y_stack_pos.append(index)
    for i in y_stack_pos:
        if df[i].isin([0]).all():
            y_stack_pos.remove(i)
    stackplot(ax, df[y_stack_pos])
    # check whether the list y_stack_neg is filled
    if y_stack_neg != []:
        stackplot(ax, df[y_stack_neg])

    # plot lineplot (demand)
    lineplot(ax, df_demand)


def eng_format(ax, df, unit, conv_number):
    r"""
    Applies the EngFormatter to y-axis.

    Parameters
    ---------------
    ax : matplotlib.AxesSubplot
        Axis on which data is plotted.
    df : pandas.DataFrame
        Dataframe with data.
    unit : string
        Unit which is plotted on y-axis
    conv_number : int
        Conversion number to convert data to given unit.

    Returns
    ----------
    df : pandas.DataFrame
        Adjusted dataframe to unit.
    """
    formatter0 = EngFormatter(unit=unit)
    ax.yaxis.set_major_formatter(formatter0)
    df[df.select_dtypes(include=["number"]).columns] *= conv_number
    return df
