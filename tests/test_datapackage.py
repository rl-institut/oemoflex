import os
import json
from shutil import rmtree

from oemof.solph.helpers import extend_basic_path
import oemof.tabular

from oemoflex.model.datapackage import DataFramePackage, EnergyDataPackage
from oemoflex.tools.helpers import check_if_csv_dirs_equal


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


def test_edp_setup_default_with_updates(monkeypatch):

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
            "defaults": {"input_parameters": "{}", "output_parameters": "{}"},
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
    foreign_keys_update = {"fuel_cell": ["h2-fuel_cell"]}

    edp.infer_metadata(
        foreign_keys_update=foreign_keys_update,
    )

    # Check datapackage without custom descriptor file:
    assert os.path.exists(basepath)
    assert os.path.exists(os.path.join(basepath, "datapackage.json"))
    with open(os.path.join(basepath, "datapackage.json"), "r") as dp_file:
        datapackage = json.load(dp_file)
    fuel_cell_index = next(
        i
        for i, resource in enumerate(datapackage["resources"])
        if resource["name"] == "h2-fuel_cell"
    )
    # With no custom foreign_key descriptors given, oemof.tabular assumes that 'fuel_cell' refers to
    # a profile. The foreign keys thus have only one entry.
    assert len(datapackage["resources"][fuel_cell_index]["schema"]["foreignKeys"]) == 1

    monkeypatch.setenv(
        "OEMOF_TABULAR_FOREIGN_KEY_DESCRIPTORS_FILE",
        os.path.join(here, "_files", "foreign_key_descriptors.json"),
    )
    import importlib

    importlib.reload(oemof.tabular.config.config)

    edp.infer_metadata(
        foreign_keys_update=foreign_keys_update,
    )

    # Check datapackage with custom descriptor file including 'fuel_cell':
    assert os.path.exists(basepath)
    assert os.path.exists(os.path.join(basepath, "datapackage.json"))
    with open(os.path.join(basepath, "datapackage.json"), "r") as dp_file:
        datapackage = json.load(dp_file)
    fuel_cell_index = next(
        i
        for i, resource in enumerate(datapackage["resources"])
        if resource["name"] == "h2-fuel_cell"
    )
    # With custom foreign_key descriptors given, oemof.tabular uses them to set the foreign keys.
    assert len(datapackage["resources"][fuel_cell_index]["schema"]["foreignKeys"]) == 3

    foreign_keys_fuel_cell = [
        fk["fields"]
        for fk in datapackage["resources"][fuel_cell_index]["schema"]["foreignKeys"]
    ]

    foreign_keys_expected = ["h2_bus", "electricity_bus", "heat_bus"]

    assert sorted(foreign_keys_fuel_cell) == sorted(foreign_keys_expected)


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


def test_edp_stack_unstack_keep_column_order():
    # set up paths
    here = os.path.dirname(__file__)
    tmp = extend_basic_path("tmp")

    default = os.path.join(here, "_files", "default_edp_custom_column_order")
    stacked_unstacked = os.path.join(tmp, "stacked_unstacked")

    clean_path(stacked_unstacked)

    # load default energydatapackage
    edp = EnergyDataPackage.from_csv_dir(default)

    # stack and unstack
    edp.stack_components()

    edp.unstack_components()

    # save and compare
    edp.to_csv_dir(stacked_unstacked, overwrite=True)

    check_if_csv_dirs_equal(default, stacked_unstacked)
