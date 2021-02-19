import os

# DONT REMOVE THIS LINE!
# pylint: disable=unused-import
from oemof.tabular import datapackage  # noqa
from oemof.solph import EnergySystem, Model
from oemoflex.model.datapackage import EnergyDataPackage#, postprocess


destination = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'simple_model')

edp = EnergyDataPackage.setup_default(
    datetimeindex=None,
    select_components=None,
    select_busses=None,
    select_regions=None,
    select_links=None,
    dummy_sequences=False,
)

edp.infer_metadata()

edp.to_csv_dir(destination)

es = EnergySystem.from_datapackage(destination)

om = Model(es)

om.solve()

es_restored = EnergySystem()

es_restored.restore()

results_dp = postprocess(es_restored)

results_dp.to_csv_dir()
