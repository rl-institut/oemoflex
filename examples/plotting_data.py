import pandas as pd
import matplotlib.pyplot as plt
import oemoflex.tools.plots as plots

# import data and yaml files
input_data = r'C:\Users\meinm\Documents\Git\oemof-B3-Ergebnisdaten\03_postprocessed\simple_model\sequences\bus\BB-electricity.csv'
data = pd.read_csv(input_data, header=[0,1,2], parse_dates=[0], index_col=[0])


fig, ax = plt.subplots(figsize=(12,5))
data = plots.eng_format(ax, data, 'W', 1000)

start_date = '2019-12-01 00:00:00'
end_date = '2019-12-13 23:00:00'
plots.plot_dispatch(ax, data, start_date=start_date, end_date=end_date,
                    y_stack_pos=['Biomass', 'CH4', 'Wind', 'PV', 'BAT discharge', 'Import'],
                    y_stack_neg=['Export', 'BAT charge'], y_line=['Demand'],
                    bus_name='BB-electricity', demand_name='BB-electricity-demand')

# ax.set_ylim(ymin=-1e+7, ymax=1.8e+7) # bottom, es gibt noch Fehlerwerte in den Daten (extrem große kurze Produktion)
plt.legend(loc='best')
plt.tight_layout()
plt.show()
