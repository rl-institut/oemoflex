import os
import pandas as pd
import matplotlib.pyplot as plt
import oemoflex.tools.plots as plots

# import data and yaml files
here = os.path.abspath(os.path.dirname(__file__))
input_path = os.path.join(
    here, "03_postprocessed", "simple_model", "sequences", "bus", "A-electricity.csv"
)
data = pd.read_csv(input_path, header=[0, 1, 2], parse_dates=[0], index_col=[0])

# prepare data
# convert data to SI-unit
conv_number = 1000
data = data * conv_number
df, df_demand = plots.prepare_dispatch_data(
    data, bus_name="A-electricity", demand_name="demand"
)

# interactive plotly dispatch plot
fig = plots.plot_dispatch_plotly(
    df=df,
    df_demand=df_demand,
    unit="W",
)

fig.write_html(
    file=os.path.join(here, "dispatch_interactive.html"),
    # include_plotlyjs=False,
    # full_html=False
)

# static dispatch plot
fig, ax = plt.subplots(figsize=(12, 5))

start_date = "2016-01-01 00:00:00"
end_date = "2016-01-10 23:00:00"
df_time_filtered = plots.filter_timeseries(df, start_date, end_date)
df_demand_time_filtered = plots.filter_timeseries(df_demand, start_date, end_date)

plots.plot_dispatch(ax=ax, df=df_time_filtered, df_demand=df_demand_time_filtered, unit="W")

plt.legend(loc="best")
plt.tight_layout()
plt.show()

