from datetime import datetime, timedelta

import pandas as pd

from gfs.fetch import get_gfs_data, get_col_order


def test_get_gfs_data_equality():
    """
    Test that the historical and forecast GFS data are equal for a given date, run, and delta.
    """
    date = datetime.today().date() - timedelta(days=3)
    date = datetime(date.year, date.month, date.day)
    run = 0
    delta = 0
    lat_gfs = [50.00, 50.25, 49.75]
    lon_gfs = [16.00, 13.75, 18.75]

    data_hist = get_gfs_data(date, run, delta, lat_gfs, lon_gfs, source='hist')
    data_forecast = get_gfs_data(date, run, delta, lat_gfs, lon_gfs, source='forecast')

    num_gfs_cols = len(get_col_order())

    assert data_hist.shape[0] == len(lat_gfs), f"data_hist should have {len(lat_gfs)} rows, got {data_hist.shape[0]}"
    assert data_hist.shape[1] == num_gfs_cols + 4, f"data_hist should have {num_gfs_cols + 4} columns, got {data_hist.shape[1]}"
    assert data_forecast.shape[0] == len(lat_gfs), f"data_forecast should have {len(lat_gfs)} rows, got {data_forecast.shape[0]}"
    assert data_forecast.shape[1] == num_gfs_cols + 4, f"data_forecast should have {num_gfs_cols + 4} columns, got {data_forecast.shape[1]}"
    pd.testing.assert_frame_equal(data_hist, data_forecast, check_index_type=False)
