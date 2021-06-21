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
data = plots.eng_format(ax, data, "W", 1000)

start_date = "2019-12-01 00:00:00"
end_date = "2019-12-13 23:00:00"
plots.plot_dispatch(
    ax=ax,
    df=data,
    bus_name="A-electricity",
)

plt.legend(loc="best")
plt.tight_layout()
plt.show()
