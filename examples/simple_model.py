import os

import pandas as pd
from oemof.solph import EnergySystem, Model
# DONT REMOVE THIS LINE!
# pylint: disable=unused-import
from oemof.tabular import datapackage  # noqa

from oemoflex.model.datapackage import EnergyDataPackage  # , postprocess

destination = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'simple_model')

edp = EnergyDataPackage.setup_default(
    name='simple_model',
    basepath=destination,
    datetimeindex=pd.date_range("1/1/2016", periods=24 * 10, freq="H"),
    components=['heat-demand'],
    busses=['heat'],
    regions=['A', 'B'],
    links=['A-B'],
)

edp.infer_metadata()

edp.to_csv_dir(destination)

es = EnergySystem.from_datapackage(os.path.join(destination, 'datapackage.json'))

om = Model(es)

om.solve()

es_restored = EnergySystem()

es_restored.restore()

results_dp = postprocess(es_restored)

results_dp.to_csv_dir()
