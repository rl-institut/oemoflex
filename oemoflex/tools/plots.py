import numpy as np
import pandas as pd
from matplotlib.ticker import EngFormatter
#from pandas.plotting import register_matplotlib_converters
#register_matplotlib_converters()


def map_labels(df, labels_dict, bus_name, demand_name):
    r"""
    Changes the column names and makes electricity consumers negative except demand.

    Parameters
    ---------------
    'df' : pandas.DataFrame
        Dataframe with electricity data.
    'labels_dict' : dictionary
        Contains old and new column names. The new column names are used for the labels in the plot.
    'bus_name' : string
        Name of the bus to identify columns where electricty goes from the bus to a consumer.
    'demand_name' : string
        Name of the demand bus to identify the column where demand is the consumer.

    Returns
    ----------
    'df' : pandas.DataFrame
        Edited dataframe with new column names and negative sign for consumer columns.
    """
    df.columns = df.columns.to_flat_index()
    for i in df.columns:
        if i[0] == bus_name and not (i[1] == demand_name):
            df[i] = df[i] * -1
            df.rename(columns={i: labels_dict[i]}, inplace=True)
        else:
            df.rename(columns={i: labels_dict[i]}, inplace=True)

    return df

def filter_timeseries(df, start_date, end_date):
    r"""
    Filters a dataframe with a timeseries from a start date to an end date.

    Parameters
    ---------------
    'df' : pandas.DataFrame
        Dataframe with timeseries.
    'start_date' : string
        String with the start date for filtering in the format 'YYYY-MM-DD hh:mm:ss'.
    'end_date' : string
        String with the end date for filtering in the format 'YYYY-MM-DD hh:mm:ss'.

    Returns
    ----------
    'df_filtered' : pandas.DataFrame
        Filtered dataframe.
    """
    assert isinstance(df.index, pd.DatetimeIndex), "Index should be DatetimeIndex"
    df_filtered = df.copy()
    df_filtered = df_filtered.loc[start_date:end_date]

    return df_filtered


def stackplot(ax, df, colors_dict, y_stack_pos, y_stack_neg):
    # pos_stack and neg_stack determine the stack order
    colors=[]
    labels=[]
    y_pos = []

    for i in y_stack_pos:
        labels.append(i)
        colors.append(colors_dict[i])
        y_pos.append(df[i])

    y_pos = np.vstack(y_pos)
    ax.stackplot(df.index, y_pos, colors=colors, labels=labels)

    colors = []
    labels = []
    y_neg = []

    for i in y_stack_neg:
        labels.append(i)
        colors.append(colors_dict[i])
        y_neg.append(df[i])

    y_neg = np.vstack(y_neg)
    ax.stackplot(df.index, y_neg, colors=colors, labels=labels)


def lineplot(ax, df, colors_dict, y_line):
    y = y_line
    for i in y:
        ax.plot(df.index, df[i], color=colors_dict[i], label=i)


def plot_dispatch(ax, df, colors_dict, labels_dict, start_date, end_date,
                  y_stack_pos, y_stack_neg, y_line, bus_name, demand_name):
    df = map_labels(df, labels_dict, bus_name=bus_name, demand_name=demand_name)
    if not (start_date is None and end_date is None):
        df = filter_timeseries(df, start_date, end_date)

    stackplot(ax, df, colors_dict=colors_dict,
              y_stack_pos=y_stack_pos, y_stack_neg=y_stack_neg)
    lineplot(ax, df, colors_dict=colors_dict, y_line=y_line)


def eng_format(ax, df, unit, conv_number):
    formatter0 = EngFormatter(unit=unit)
    ax.yaxis.set_major_formatter(formatter0)
    df[df.select_dtypes(include=['number']).columns] *= conv_number
    return df
