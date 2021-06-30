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


def replace_near_zeros(df):
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
    tolerance = 1e-3
    df[abs(df) < tolerance] = 0.0
    return df


def prepare_dispatch_data(df, bus_name, demand_name):
    r"""
    The data in df is split into a DataFrame with consumers and generators and a DataFrame which only
    contains the demand data. Consumer data is made negative. The multilevel column names are replaced
    by more simple names. Columns the same name are grouped together. Really small numerical values which
    are practically zero are replaced with 0.0.

    Parameters
    ---------------
    df : pandas.DataFrame
        Dataframe with data.
    bus_name : string
        name of the main bus to which all other are connected, e.g. the "BB-electricity" bus.
    demand_name: string
        Name of the bus representing the demand.

    Returns
    ----------
    df : pandas.DataFrame
        DataFrame with prepared data for dispatch plotting of consumers and generators.
    df_demand: pandas.DataFrame
        DataFrame with prepared data for dispatch plotting of demand.
    """
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

    # group columns with the same name, e.g. transmission busses by import and export
    df = group_agg_by_column(df)
    # check columns on numeric values which are practical zero and replace them with 0.0
    df = replace_near_zeros(df)

    return df, df_demand


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


def assign_stackgroup(key, values):
    r"""
    This function decides if data is supposed to be plotted on the positive or negative side of the
    stackplot. If values has both negative and positive values, a value error is raised.

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


def plot_dispatch_plotly(
    df, bus_name, demand_name="demand", colors_odict=colors_odict, conv_number=1000
):
    r"""
    Plots data as a dispatch plot in an interactive plotly plot. The demand is plotted as a line plot and
    suppliers and other consumers are plotted with a stackplot.

    Parameters
    ---------------
    df : pandas.DataFrame
        Dataframe with data.
    bus_name : string
        name of the main bus to which all other are connected, e.g. the "BB-electricity" bus.
    demand_name: string
        Name of the bus representing the demand.
    colors_odict : collections.OrderedDictionary
        Ordered dictionary with labels as keys and colourcodes as values.

    Returns
    ----------
    fig : plotly.graph_objs._figure.Figure
        Interactive plotly dispatch plot
    """
    # convert data to SI-unit
    df = df * conv_number

    # prepare dispatch data
    df, df_demand = prepare_dispatch_data(df, bus_name, demand_name)

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
    for key, values in df.iteritems():
        stackgroup = assign_stackgroup(key, values)

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
        xaxis_title = "Date",
        yaxis_title = "Power",
    )

    # Scale power data on y axis with SI exponents
    fig.update_yaxes(exponentformat="SI",
                     ticksuffix="W")

    return fig


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
    suppliers and other consumers are plotted with a stackplot.

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

    # prepare dispatch data
    df, df_demand = prepare_dispatch_data(df, bus_name, demand_name)

    # plot stackplot, differentiate between positive and negative stacked data
    y_stack_pos = []
    y_stack_neg = []

    # assign data to positive or negative stackplot
    for key, values in df.iteritems():
        stackgroup = assign_stackgroup(key, values)
        if stackgroup == "negative":
            y_stack_neg.append(key)
        elif stackgroup == "positive":
            y_stack_pos.append(key)

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
