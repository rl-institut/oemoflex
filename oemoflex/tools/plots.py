import numpy as np
import pandas as pd
from matplotlib.ticker import EngFormatter
import oemoflex.tools.helpers as helpers


colors_dict = helpers.load_yaml('colors.yaml')
labels_dict = helpers.load_yaml('labels.yaml')


def map_labels(df, labels_dict=labels_dict):
    r"""
    Renames columns

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
    for i in df.columns:
        df.rename(columns={i: labels_dict[i]}, inplace=True)

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


def stackplot(ax, df, colors_dict=colors_dict):
    r"""
    Plots data as a stackplot. The stacking order is determined by the order
    of labels in the colors_dict. It is stacked beginning with the x-axis as
    the bottom.

    Parameters
    ---------------
    ax : matplotlib.AxesSubplot
        Axis on which data is plotted.
    df : pandas.DataFrame
        Dataframe with data.
    colors_dict : dictionary
        Dictionary with labels as keys and colourcodes as keys.
    """
    # y is a list which gets the correct stack order from colors file
    colors=[]
    labels=[]
    y = []

    order = list(colors_dict)

    for i in order:
        if i not in df.columns:
            continue
        labels.append(i)
        colors.append(colors_dict[i])
        y.append(df[i])

    y = np.vstack(y)
    ax.stackplot(df.index, y, colors=colors, labels=labels)


def lineplot(ax, df, colors_dict=colors_dict):
    r"""
    Plots data as a lineplot.

    Parameters
    ---------------
    ax : matplotlib.AxesSubplot
        Axis on which data is plotted.
    df : pandas.DataFrame
        Dataframe with data.
    colors_dict : dictionary
        Dictionary with labels as keys and colourcodes as keys.
    """
    for i in df.columns:
        ax.plot(df.index, df[i], color=colors_dict[i], label=i)


def plot_dispatch(ax, df, bus_name, demand_name, start_date=None, end_date=None):
    # identify consumers, which shall be plotted negative
    df.columns = df.columns.to_flat_index()
    for i in df.columns:
        if i[0] == bus_name:
            df[i] = df[i] * -1

    df = map_labels(df)

    df = filter_timeseries(df, start_date, end_date)

    # isolate column with demand and make the data positive again
    df_demand = (df[demand_name] * -1).to_frame()
    df.drop(columns=[demand_name], inplace=True)

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
