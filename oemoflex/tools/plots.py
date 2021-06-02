import numpy as np
import pandas as pd
import os
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


def adapt_labels_data(bus_name, labels_dict=general_labels_dict):
    r"""
    The generic labels_dict needs to be adapted to the specific region which is investigated
    in order to rename the multilevel column names.

    Parameters
    ---------------
    bus_name : string
        name of the main bus to which all other are connected, e.g. the "BB-electricity" bus.
    labels_dict : dictionary
        Contains generic template to rename the given column names of the postprocessed data.

    Returns
    ----------
    specific_labels_dict : dictionary
        Contains region specific old and new column names. The new column names are used for the labels in the plot.
    """
    labels_dict = labels_dict.copy()
    # identify region
    region = bus_name.split("-")[0]
    # adapt keys of labels_dict to specific region
    general_keys = labels_dict.keys()
    specific_keys = {}

    for general_key in general_keys:
        specific_key = list(general_key)
        for i in range(0, len(specific_key)):
            specific_key[i] = specific_key[i].replace("region", region)
        specific_key = tuple(specific_key)
        specific_keys[general_key] = specific_key

    for general_key in specific_keys:
        labels_dict[specific_keys[general_key]] = labels_dict.pop(general_key)

    return labels_dict


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

    df.columns = map_columns(df.columns, labels_dict)

    return df


def map_columns(columns, labels_dict):

    def map_tuple(tuple, dictionary):

        mapped = None

        for key, value in dictionary.items():

            if concrete_in_generic(tuple, key):
                mapped = value

            else:
                continue

        if not mapped:
            raise KeyError(f"Mappling {col}")

        return mapped

    def concrete_in_generic(concrete_tuple, generic_tuple):
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


def group_transmission(df):
    r"""
    Columns with the same name are grouped together and aggregated. This is needed to
    group the Import and Export columns if there are multiple because the region has
    electricity transmission with multiple other regions.

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
    # specific_labels_dict = adapt_labels_data(bus_name)
    df = map_labels(df, general_labels_dict)
    df_demand = map_labels(df_demand, general_labels_dict)

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
