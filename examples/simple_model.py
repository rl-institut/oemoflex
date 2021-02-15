from oemof.solph import EnergySystem, Model
from oemoflex import EnergyDataPackage, postprocess


edp = EnergyDataPackage.setup_default(
    datetimeindex=None,
    select_components=None,
    select_busses=None,
    select_regions=None,
    select_links=None,
    dummy_sequences=False,
)

edp.infer_metadata()

edp.to_csv_dir()

es = EnergySystem.from_datapackage()

om = Model(es)

om.solve()

es_restored = EnergySystem()

es_restored.restore()

results_dp = postprocess(es_restored)

results_dp.to_csv_dir()
