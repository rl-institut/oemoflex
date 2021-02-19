from oemoflex.model.datapackage import DataFramePackage, EnergyDataPackage


def test_datapackage():

    data = {'a': 0, 'b': 0}

    rel_paths = {'a': 'a.csv', 'b': 'b.csv'}

    dfp = DataFramePackage(basepath='path', data=data, rel_paths=rel_paths)

    assert dfp.basepath == 'path'

    assert dfp.data == data

    assert dfp.rel_paths == rel_paths


def test_edp():
    EnergyDataPackage(basepath='path', data={}, rel_paths={})


def test_edp_setup_default():
    
    datetimeindex = None
    components = None
    busses = None
    regions = None
    links = None

    EnergyDataPackage.setup_default(
        datetimeindex=datetimeindex,
        components=components,
        busses=busses,
        regions=regions,
        links=links,
    )
