import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import yaml
from matplotlib.ticker import EngFormatter

from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()


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
    df.columns = data.columns.to_flat_index()
    for i in df.columns:
        if i[0] == bus_name and not (i[1] == demand_name):
            df[i] = df[i] * -1
            df.rename(columns={i: labels_dict[i]}, inplace=True)
        else:
            df.rename(columns={i: labels_dict[i]}, inplace=True)

    return df

def filter_timeseries(df, timestamp_col, start_date, end_date):
    r"""
    Filters a dataframe with a timeseries from a start date to an end date.

    Parameters
    ---------------
    'df' : pandas.DataFrame
        Dataframe with timeseries.
    'timestamp_col' : string
        Column name of the column which contains the timestamps.
    'start_date' : string
        String with the start date for filtering in the format 'YYYY-MM-DD hh:mm:ss'.
    'end_date' : string
        String with the end date for filtering in the format 'YYYY-MM-DD hh:mm:ss'.

    Returns
    ----------
    'df' : pandas.DataFrame
        Filtered dataframe.
    """
    mask = (df[timestamp_col] >= start_date) & (df[timestamp_col] <= end_date)
    df = df.loc[mask]
    df = df.copy()

    return df


def stackplot(ax, df, colors_dict, x, y_stack_pos, y_stack_neg):
    # pos_stack and neg_stack determine the stack order
    colors=[]
    labels=[]
    y_pos = []

    for i in y_stack_pos:
        labels.append(i)
        colors.append(colors_dict[i])
        y_pos.append(df[i])

    x = df[x]

    y_pos = np.vstack(y_pos)
    ax.stackplot(x, y_pos, colors=colors, labels=labels)

    colors = []
    labels = []
    y_neg = []

    for i in y_stack_neg:
        labels.append(i)
        colors.append(colors_dict[i])
        y_neg.append(df[i])

    y_neg = np.vstack(y_neg)
    ax.stackplot(x, y_neg, colors=colors, labels=labels)


def lineplot(ax, df, colors_dict, x, y_line):
    y = y_line
    for i in y:
        ax.plot(df[x], df[i], color=colors_dict[i], label=i)


def plot_dispatch(ax, df, colors_dict, labels_dict, start_date, end_date, x_timestamp,
                  y_stack_pos, y_stack_neg, y_line, bus_name, demand_name):
    df = map_labels(df, labels_dict, bus_name=bus_name, demand_name=demand_name)
    if not (start_date is None and end_date is None):
        df = filter_timeseries(df, x_timestamp, start_date, end_date)

    stackplot(ax, df, colors_dict=colors_dict, x=x_timestamp,
              y_stack_pos=y_stack_pos, y_stack_neg=y_stack_neg)
    lineplot(ax, df, colors_dict=colors_dict, x=x_timestamp, y_line=y_line)


def eng_format(ax, df, unit, conv_number):
    formatter0 = EngFormatter(unit=unit)
    ax.yaxis.set_major_formatter(formatter0)
    df[df.select_dtypes(include=['number']).columns] *= conv_number
    return df


# import data and yaml files
input_data = r'C:\Users\meinm\Documents\Git\oemof-B3-Ergebnisdaten\03_postprocessed\simple_model\sequences\bus\BB-electricity.csv'
data = pd.read_csv(input_data, header=[0,1,2,3], parse_dates=[0])

colors_yaml = open('colors.yaml', "r")
colors_dict = yaml.load(colors_yaml, Loader=yaml.FullLoader)
labels_yaml = open('labels.yaml', "r")
labels_dict = yaml.load(labels_yaml, Loader=yaml.FullLoader)


fig, ax = plt.subplots(figsize=(12,5))
data = eng_format(ax, data, 'W', 1000)

start_date = '2019-12-01 00:00:00'
end_date = '2019-12-13 23:00:00'
plot_dispatch(ax, data, colors_dict, labels_dict, start_date=start_date, end_date=end_date,
              x_timestamp='Timestamp', y_stack_pos=['Biomass', 'CH4', 'Wind', 'PV', 'BAT discharge', 'Import'],
              y_stack_neg=['Export', 'BAT charge'], y_line=['Demand'],
              bus_name='BB-electricity', demand_name='BB-electricity-demand')

# ax.set_ylim(ymin=-1e+7, ymax=1.8e+7) # bottom, es gibt noch Fehlerwerte in den Daten (extrem große kurze Produktion)
plt.legend(loc='best')
plt.tight_layout()
plt.show()
