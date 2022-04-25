import os
from shutil import rmtree

from oemof.solph.helpers import extend_basic_path

from oemoflex.model.datapackage import DataFramePackage, EnergyDataPackage
from oemoflex.tools.helpers import check_if_csv_dirs_equal, load_yaml


def clean_path(path):
    if os.path.exists(path):
        rmtree(path)


def test_datapackage():

    data = {"a": 0, "b": 0}

    rel_paths = {"a": "a.csv", "b": "b.csv"}

    dfp = DataFramePackage(basepath="path", data=data, rel_paths=rel_paths)

    assert dfp.basepath == "path"

    assert dfp.data == data

    assert dfp.rel_paths == rel_paths


def test_edp():
    EnergyDataPackage(basepath="path", data={}, rel_paths={})


def test_edp_setup_default():

    here = os.path.dirname(__file__)
    defaultpath = os.path.join(here, "_files", "default_edp")
    tmp = extend_basic_path("tmp")

    name = "test_edp"
    basepath = os.path.join(tmp, name)
    datetimeindex = None
    regions = ["A", "B"]
    links = ["A-B"]

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

    edp.to_csv_dir(basepath, overwrite=True)

    check_if_csv_dirs_equal(basepath, defaultpath)


def test_edp_setup_default_select():

    tmp = extend_basic_path("tmp")

    name = "test_edp"
    components = ["electricity-heatpump", "ch4-boiler"]
    busses = ["ch4", "electricity", "heat"]
    basepath = os.path.join(tmp, name)
    datetimeindex = None
    regions = ["A", "B"]
    links = ["A-B"]

    EnergyDataPackage.setup_default(
        name=name,
        components=components,
        busses=busses,
        basepath=basepath,
        datetimeindex=datetimeindex,
        regions=regions,
        links=links,
    )


def test_edp_setup_default_with_updates():

    # Define the name of the datapackage
    name = "test_edp_with_updates"

    # Define some paths
    here = os.path.dirname(__file__)
    defaultpath = os.path.join(here, "_files", "default_edp_with_updates")
    tmp = extend_basic_path("tmp")
    basepath = os.path.join(tmp, name)

    components = ["h2-fuel_cell", "electricity-heatpump", "ch4-boiler"]
    busses = ["h2", "electricity", "heat"]
    regions = ["A", "B"]
    links = ["A-B"]

    # Define the attributes of some custom busses, components and facades
    bus_attrs_update = {"h2": {"balanced": True}}

    component_attrs_update = {
        "h2-fuel_cell": {
            "carrier": "h2",
            "tech": "fuel_cell",
            "type": "fuel_cell",
            "foreign_keys": {
                "h2_bus": "h2",
                "electricity_bus": "electricity",
                "heat_bus": "heat",
            },
            "defaults": {
                "input_parameters": "{}",
                "output_parameters": "{}",
            },
        },
    }

    facade_attrs_update = os.path.join(here, "_files", "facade_attrs_update")

    # Setup the energy datapackage
    edp = EnergyDataPackage.setup_default(
        name=name,
        components=components,
        busses=busses,
        basepath=basepath,
        datetimeindex=None,
        regions=regions,
        links=links,
        bus_attrs_update=bus_attrs_update,
        component_attrs_update=component_attrs_update,
        facade_attrs_update=facade_attrs_update,
    )

    clean_path(basepath)

    edp.to_csv_dir(basepath, overwrite=True)

    check_if_csv_dirs_equal(basepath, defaultpath)

    # set custom foreign keys and foreign key descriptors
    foreign_keys_update = {
        "bus": [
            "h2-fuel_cell",
        ]
    }

    foreign_key_descriptors_update = load_yaml(
        os.path.join(here, "_files", "foreign_key_descriptors_update.yml")
    )

    edp.infer_metadata(
        foreign_keys_update=foreign_keys_update,
        foreign_key_descriptors_update=foreign_key_descriptors_update,
    )


def test_edp_stack_unstack():

    tmp = extend_basic_path("tmp")
    before = os.path.join(tmp, "before")
    after = os.path.join(tmp, "after")

    name = "test_edp"
    datetimeindex = None
    regions = ["A", "B"]
    links = ["A-B"]

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

    edp.to_csv_dir(before, overwrite=True)

    edp.stack_components()

    edp.unstack_components()

    edp.to_csv_dir(after, overwrite=True)

    check_if_csv_dirs_equal(before, after)
