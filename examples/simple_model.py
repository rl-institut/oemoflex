import os

import pandas as pd
from oemof.solph import EnergySystem, Model
from oemof.outputlib.processing import parameter_as_dict
# DONT REMOVE THIS LINE!
# pylint: disable=unused-import
from oemof.tabular import datapackage  # noqa
from oemof.tabular.facades import TYPEMAP

from oemoflex.model.datapackage import EnergyDataPackage, ResultsDataPackage

here = os.path.abspath(os.path.dirname(__file__))
preprocessed = os.path.join(here, '01_preprocessed', 'simple_model')
optimized = os.path.join(here, '02_optimized')
postprocessed = os.path.join(here, '03_postprocessed', 'simple_model')

# setup default structure
edp = EnergyDataPackage.setup_default(
    name='simple_model',
    basepath=preprocessed,
    datetimeindex=pd.date_range("1/1/2016", periods=24 * 10, freq="H"),
    components=[
        'ch4-boiler',
        'heat-demand'
    ],
    busses=[
        'ch4',
        'heat',
    ],
    regions=['A', 'B'],
    links=['A-B'],
)

# parametrize
edp.data['heat-demand']['amount'] = 100

edp.data['ch4-boiler']['capacity'] = [200, 300]

edp.data['ch4-boiler']['efficiency'] = 0.9

edp.data['ch4-boiler']['marginal_cost'] = 30

edp.data['heat-demand-profile'].loc[:, :] = [[1, 1]] * 240

# save to csv
edp.to_csv_dir(preprocessed)

# add metadata
edp.infer_metadata()

# create EnergySystem and Model and solve it.
es = EnergySystem.from_datapackage(
    os.path.join(preprocessed, 'datapackage.json'),
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

results_dp.set_scenario_name('simple_model')

results_dp.to_csv_dir(postprocessed)
