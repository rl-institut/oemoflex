import os
import numpy as np
import pandas as pd
from oemof.solph import EnergySystem, Model
from oemof.solph.processing import parameter_as_dict

# DONT REMOVE THIS LINE!
# pylint: disable=unused-import
from oemof.tabular import datapackage  # noqa
from oemof.tabular.facades import TYPEMAP

from oemoflex.model.datapackage import EnergyDataPackage, ResultsDataPackage

here = os.path.abspath(os.path.dirname(__file__))
preprocessed = os.path.join(here, "01_preprocessed", "simple_model")
optimized = os.path.join(here, "02_optimized")
postprocessed = os.path.join(here, "03_postprocessed", "simple_model")

# setup default structure
edp = EnergyDataPackage.setup_default(
    name="simple_model",
    basepath=preprocessed,
    datetimeindex=pd.date_range("1/1/2016", periods=24 * 10, freq="H"),
    components=["ch4-gt", "biomass-gt", "electricity-demand"],
    busses=[
        "ch4",
        "biomass",
        "electricity",
    ],
    regions=["A", "B"],
    links=["A-B"],
)

# parametrize scalars
edp.parametrize("electricity-demand", "amount", 10)

edp.parametrize("biomass-gt", "capacity", [12, 12])

edp.parametrize("biomass-gt", "efficiency", 0.4)

edp.parametrize("ch4-gt", "carrier_cost", 30)

edp.parametrize("ch4-gt", "capacity", [10, 12])

edp.parametrize("ch4-gt", "efficiency", 0.6)

edp.parametrize("ch4-gt", "carrier_cost", 60)

# parametrize timeseries
profile = 1 + np.sin(np.linspace(0, 2 * np.pi, 240))

edp.parametrize("electricity-demand-profile", "A-electricity-demand-profile", profile)

edp.parametrize("electricity-demand-profile", "B-electricity-demand-profile", profile)

# save to csv
edp.to_csv_dir(preprocessed, overwrite=True)

# add metadata
edp.infer_metadata()

# create EnergySystem and Model and solve it.
es = EnergySystem.from_datapackage(
    os.path.join(preprocessed, "datapackage.json"),
    attributemap={},
    typemap=TYPEMAP,
)

om = Model(es)

om.solve()

# save EnergySystem with results
es.results = om.results()
es.params = parameter_as_dict(es)

if not os.path.exists(optimized):
    os.makedirs(optimized)

es.dump(optimized)

# restore and postprocess
es_restored = EnergySystem()

es_restored.restore(optimized)

results_dp = ResultsDataPackage.from_energysytem(es_restored)

results_dp.set_scenario_name("simple_model")

results_dp.to_csv_dir(postprocessed, overwrite=True)
