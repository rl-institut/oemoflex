from oemoflex.model.model_structure import create_default_data


def test_default_data():

    data, rel_paths = create_default_data(
        select_regions=['A', 'B'],
        select_links=['A-B'],
    )

    assert isinstance(data, dict)
