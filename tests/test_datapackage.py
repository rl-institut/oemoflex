import os
from shutil import rmtree

from oemof.tools.helpers import extend_basic_path

from oemoflex.model.datapackage import DataFramePackage, EnergyDataPackage
from oemoflex.tools.helpers import check_if_csv_dirs_equal


def clean_path(path):
    if os.path.exists(path):
        rmtree(path)


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

    here = os.path.dirname(__file__)
    defaultpath = os.path.join(here, '_files', 'default_edp')
    tmp = extend_basic_path('tmp')

    name = 'test_edp'
    basepath = os.path.join(tmp, name)
    datetimeindex = None
    regions = ['A', 'B']
    links = ['A-B']

    edp = EnergyDataPackage.setup_default(
        name=name,
        components=None,
        busses=None,
        basepath=basepath,
        datetimeindex=datetimeindex,
        regions=regions,
        links=links,
    )

    clean_path(basepath)

    edp.to_csv_dir(basepath)

    check_if_csv_dirs_equal(basepath, defaultpath)


def test_edp_setup_default_select():

    tmp = extend_basic_path('tmp')

    name = 'test_edp'
    components = ['electricity-heatpump', 'ch4-boiler']
    busses = ['ch4', 'electricity', 'heat']
    basepath = os.path.join(tmp, name)
    datetimeindex = None
    regions = ['A', 'B']
    links = ['A-B']

    EnergyDataPackage.setup_default(
        name=name,
        components=components,
        busses=busses,
        basepath=basepath,
        datetimeindex=datetimeindex,
        regions=regions,
        links=links,
    )


def test_edp_stack_unstack():

    tmp = extend_basic_path('tmp')
    before = os.path.join(tmp, 'before')
    after = os.path.join(tmp, 'after')

    name = 'test_edp'    
    datetimeindex = None
    regions = ['A', 'B']
    links = ['A-B']

    edp = EnergyDataPackage.setup_default(
        name=name,
        components=None,
        busses=None,
        basepath=None,
        datetimeindex=datetimeindex,
        regions=regions,
        links=links,
    )

    clean_path(before)

    clean_path(after)

    edp.to_csv_dir(before)
                   
    edp.stack_components()
    
    edp.unstack_components()

    edp.to_csv_dir(after)

    check_if_csv_dirs_equal(before, after)
