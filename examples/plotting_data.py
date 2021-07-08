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


fig, ax = plt.subplots(figsize=(12, 5))
ax, data = plots.eng_format(ax, data, "W", 1000)

start_date = "2016-01-01 00:00:00"
end_date = "2016-01-10 23:00:00"
# filter timeseries
df = data.copy()
df = plots.filter_timeseries(df, start_date, end_date)
# prepare dispatch data
df, df_demand = plots.prepare_dispatch_data(
    df, bus_name="A-electricity", demand_name="demand"
)

plots.plot_dispatch(ax=ax, df=df, df_demand=df_demand)

plt.legend(loc="best")
plt.tight_layout()
plt.show()

# interactive plotly plot
df = data.copy()
# convert data to SI-unit
conv_number = 1000
df = df * conv_number

# prepare dispatch data
df, df_demand = plots.prepare_dispatch_data(
    df, bus_name="A-electricity", demand_name="A-electricity-demand"
)


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
