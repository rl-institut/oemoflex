from oemoflex.tools import plots
import pandas as pd


def test_group_agg_by_column():
    df = pd.DataFrame({"A": [1, 1, 1], "B": [2, 2, 2]})
    df.rename(columns={"B": "A"}, inplace=True)

    df_agg = plots._group_agg_by_column(df)

    df_agg_default = pd.DataFrame({"A": [3, 3, 3]})

    # Check if df_agg is the same as expected
    pd.testing.assert_frame_equal(df_agg, df_agg_default)
