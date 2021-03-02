import os

import pandas as pd
from oemof.solph import EnergySystem, Model
# DONT REMOVE THIS LINE!
# pylint: disable=unused-import
from oemof.tabular import datapackage  # noqa
from oemof.tabular.facades import TYPEMAP

from oemoflex.model.datapackage import EnergyDataPackage  # , postprocess

here = os.path.abspath(os.path.dirname(__file__))
preprocessed = os.path.join(here, 'simple_model')
optimized = here

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

edp.data['ch4-boiler']['capacity'] = [1, 2]

edp.data['ch4-boiler']['efficiency'] = 0.9

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

es.dump(here)

# restore and postprocess
es_restored = EnergySystem()

es_restored.restore(here)

results_dp = postprocess(es_restored)

results_dp.to_csv_dir()
