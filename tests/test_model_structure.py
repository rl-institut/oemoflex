import os

import pandas as pd

from oemoflex.model.model_structure import create_default_data, FacadeAttrs

import oemoflex.model


def test_default_data():

    data, rel_paths = create_default_data(
        select_regions=["A", "B"],
        select_links=["A-B"],
    )

    assert isinstance(data, dict)


def test_facade_attrs_init():
    facade_attrs_dir = os.path.join(oemoflex.model.__path__[0], "facade_attrs")
    facade_attrs = FacadeAttrs(facade_attrs_dir)

    assert isinstance(facade_attrs.specs["load"], pd.DataFrame)


def test_facade_attrs_update():
    facade_attrs_dir = os.path.join(oemoflex.model.__path__[0], "facade_attrs")
    facade_attrs = FacadeAttrs(facade_attrs_dir)
    facade_attrs.update(facade_attrs_dir)

    assert isinstance(facade_attrs.specs["load"], pd.DataFrame)
