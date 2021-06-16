from oemoflex.tools import plots


def test_group_agg_by_column():
    df = None

    df_agg = plots.group_agg_by_column(df)

    df_agg_default = None

    # Check if df_agg is the same as expected
