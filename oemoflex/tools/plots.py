import numpy as np
import pandas as pd
import os
from collections import OrderedDict
from matplotlib.ticker import EngFormatter
import oemoflex.tools.helpers as helpers

dir_name = os.path.abspath(os.path.dirname(__file__))

labels_dict = helpers.load_yaml(os.path.join(dir_name,'labels.yaml'))

colors_csv = pd.read_csv(os.path.join(dir_name, 'colors.csv'), header=[0], index_col=[0])
colors_csv = colors_csv.T
colors_odict = OrderedDict()
for i in colors_csv.columns:
    colors_odict[i] = colors_csv.loc['Color',i]


def map_labels(df, labels_dict=labels_dict):
    r"""
    Renames columns according to the specifications in the label_dict. The data has multilevel
    column names. Thus, the labels_dict need a tuple as key. The value is used as the new column
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
    df.columns = df.columns.to_flat_index()
    df.rename(columns=labels_dict, inplace=True)

    return df


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
    colors=[]
    labels=[]
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


def plot_dispatch(ax, df, bus_name, demand_name, start_date=None, end_date=None):

    df = filter_timeseries(df, start_date, end_date)

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
    df = map_labels(df)
    df_demand = map_labels(df_demand)

    # plot stackplot, differentiate between positive and negative stacked data
    y_stack_pos=[]
    y_stack_neg=[]
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
    df[df.select_dtypes(include=['number']).columns] *= conv_number
    return df
