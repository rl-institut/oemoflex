import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import yaml

from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()


# eine Funktion für stackplot
# eine Funktion für Linien
# eine Funktion, die alles auf einmal erstellt
# at first, the stackplot has to be created, then its axis is used to plot the line plots
# es gibt noch Fehlerwerte in den Daten (extrem große kurze Produktion)
# cool wäre, wenn es egal ist, ob man zuerst stackplot oder lineplot erstellt und beides auch alleine
# verwenden kann

def map_labels(df, labels_dict):
    # changes column names
    df.columns = data.columns.to_flat_index()
    for i in df.columns:
        df.rename(columns={i: labels_dict[i]}, inplace=True)


def filter_timeseries(df, timestamp_col, start_date, end_date):
    mask = (df[timestamp_col] >= start_date) & (df[timestamp_col] <= end_date)
    df = df.loc[mask]
    df = df.copy()
    return df


def stackplot(df, colors_dict, x, y_stack):
    # y_stack determine the stack order
    colors=[]
    labels=[]
    y = []

    for i in y_stack:
        labels.append(i)
        colors.append(colors_dict[i])
        y.append(df[i])

    x = df[x]
    y = np.vstack(y)

    fig, ax = plt.subplots(figsize=(12,5))
    ax.stackplot(x, y, colors=colors, labels=labels)

    ax.set_ylim(ymin=-1e+7, ymax=1.8e+7) # bottom, es gibt noch Fehlerwerte in den Daten (extrem große kurze Produktion)

    return fig, ax


def lineplot(ax, df, colors_dict, x, y_line):
    y = y_line
    for i in y:
        ax.plot(df[x], df[i], color=colors_dict[i], label=i)


def plot_dispatch(df, timestamp_col, colors_dict, labels_dict, start_date, end_date, x, y_stack, y_line):
    map_labels(df, labels_dict)
    if not (start_date is None and end_date is None):
        df = filter_timeseries(df, timestamp_col, start_date, end_date)

    # ????????????????????????????????
    df.BAT_charge = df.BAT_charge * -1
    df.Export = df.Export * -1

    fig, ax = stackplot(df, colors_dict=colors_dict, x=x,
                        y_stack=y_stack)
    lineplot(ax, df, colors_dict=colors_dict, x=x, y_line=y_line)


# import data and yaml files
input_data = r'\\FS01\RL-Institut\04_Projekte\305_UMAS_Gasspeicher\09-Stud_Ordner\Julius\oemof-B3-Ergebnisdaten\03_postprocessed\simple_model\sequences\bus\BB-electricity.csv'
data = pd.read_csv(input_data, header=[0,1,2,3], parse_dates=[0])

colors_yaml = open('colors.yaml', "r")
colors_dict = yaml.load(colors_yaml, Loader=yaml.FullLoader)
labels_yaml = open('labels.yaml', "r")
labels_dict = yaml.load(labels_yaml, Loader=yaml.FullLoader)

start_date = '2019-12-01 00:00:00'
end_date = '2019-12-13 23:00:00'
plot_dispatch(data, 'Timestamp', colors_dict, labels_dict, start_date=start_date, end_date=end_date,
              x='Timestamp', y_stack=['Biomass', 'CH4', 'Wind', 'PV', 'BAT_discharge', 'Import'],
              y_line=['Demand', 'Export', 'BAT_charge'])

plt.legend(loc='best')
plt.tight_layout()
plt.show()
