import os
import pandas as pd
import matplotlib.pyplot as plt
import oemoflex.tools.plots as plots

# import data and yaml files
here = os.path.abspath(os.path.dirname(__file__))
input_path = os.path.join(
    here, "03_postprocessed", "simple_model", "sequences", "bus", "BB-electricity.csv"
)
data = pd.read_csv(input_path, header=[0, 1, 2], parse_dates=[0], index_col=[0])


fig, ax = plt.subplots(figsize=(12, 5))
data = plots.eng_format(ax, data, "W", 1000)

start_date = "2019-12-01 00:00:00"
end_date = "2019-12-13 23:00:00"
plots.plot_dispatch(
    ax=ax,
    df=data,
    start_date=start_date,
    end_date=end_date,
    bus_name="BB-electricity",
    demand_name="BB-electricity-demand",
)

plt.legend(loc="best")
plt.tight_layout()
plt.show()

fig = plots.plot_dispatch_plotly(
    df=data,
    bus_name="BB-electricity",
    demand_name="BB-electricity-demand",
)

fig.write_html(
    file=os.path.join(here, 'dispatch_interactive.html'),
    # include_plotlyjs=False,
    # full_html=False
)