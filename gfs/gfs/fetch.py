from datetime import timedelta
import warnings

import numpy as np
import pandas as pd
import xarray as xr

import gfs.constants as constants


def get_col_map(source='hist'):
    """
    Returns a dictionary mapping {source}_name to the corresponding key in SCHEMA.
    """
    return {details[f'{source}_name']: key for key, details in constants.SCHEMA.items()}


def get_col_order():
    """
    Returns a list of keys from SCHEMA ordered by their position.
    """
    return sorted(constants.SCHEMA.keys(), key=lambda key: constants.SCHEMA[key]['position'])


def get_gfs_hist_url(date, run, time):
    """
    Returns the URL to the GFS historical data for the given date, run, and time.
    """
    date_str = date.strftime("%Y%m%d")
    year_str = date.strftime("%Y")
    return f"{constants.GFS_HIST_BASE}/{year_str}/{date_str}/gfs.0p25.{date_str}{run:02d}.f{time:03d}.grib2"


def get_gfs_forecast_url(date, run, res='0p25'):
    """
    Returns the URL to the GFS forecast data for the given date, run, and resolution.
    """
    date_str = date.strftime("%Y%m%d")
    return f"{constants.GFS_FORECAST_BASE}/gfs_{res}/gfs{date_str}/gfs_{res}_{run:02d}z"


def flatten_column_names(columns):
    """
    Flattens the column names by removing the level and appending it to the name.
    """
    new_columns = []
    for col in columns:
        name = col[0]  
        level = next((x for x in col if isinstance(x, float) and not np.isnan(x)), None)
        if level is not None:
            new_columns.append(f'{name}_{int(level)}')
        else:
            new_columns.append(name)
    return new_columns


def get_idexes(ds, variables):
    """
    Returns a dictionary of indexes for the given dataset and variables.
    """
    idexes = dict()
    for var in variables:
        if variables[var] is None:
            continue
        index = next((index_name for index_name in ds[var].indexes if index_name not in ['lat', 'lon', 'time']), None)
        if index not in idexes:
            idexes[index] = variables[var]
    return idexes


def _download_hist_data(date, run, delta, lat_gfs, lon_gfs):
    """
    Downloads the historical GFS data for the given date, run, and delta.
    """
    pds = []
    url = get_gfs_hist_url(date, run, delta)
    with xr.open_dataset(url) as ds:
        query = get_idexes(ds, constants.VARIABLES_HIST)
        query['lat'] = np.unique(lat_gfs)
        query['lon'] = np.unique(lon_gfs)
        data = ds[constants.VARIABLES_HIST.keys()].sel(**query)
        
        for idx in range(len(lat_gfs)):
            data_idx = data.sel(lat=[lat_gfs[idx]], lon=[lon_gfs[idx]])
            stacked = data_idx.stack(points=('lat', 'lon'), create_index=True)
            pds.append(stacked.to_stacked_array('x', sample_dims=['points']).to_pandas())
        
    return pd.concat(pds)


def _download_forecast_data(date, run, ref_time, lat_gfs, lon_gfs):
    """
    Downloads the forecast GFS data for the given date, run, and reference time.
    """
    pds = []
    url = get_gfs_forecast_url(date, run)
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=xr.SerializationWarning,
            module=r"xarray",
        )
        with xr.open_dataset(url) as ds:
            data = ds[constants.VARIABLES_FORECAST].sel(time=ref_time, lat=np.unique(lat_gfs), lon=np.unique(lon_gfs), lev=constants.HPA_LVLS)

            for idx in range(len(lat_gfs)):
                data_idx = data.sel(lat=[lat_gfs[idx]], lon=[lon_gfs[idx]])
                stacked = data_idx.stack(points=('lat', 'lon'), create_index=True)
                pds.append(stacked.to_stacked_array('x', sample_dims=['points']).to_pandas())
    return pd.concat(pds)


def get_gfs_data(date, run, delta, lat_gfs, lon_gfs, source='hist'):
    """
    Downloads the GFS data for the given date, run, delta, latitude, longitude, and source.
    """
    assert source in ['hist', 'forecast'], 'Source must be either hist or forecast'
    
    ref_time = date.replace(hour=run) + timedelta(hours=delta)

    if source == 'hist':
        data = _download_hist_data(date, run, delta, lat_gfs, lon_gfs)
    else:
        data = _download_forecast_data(date, run, ref_time, lat_gfs, lon_gfs)
    # force schema
    data.columns = flatten_column_names(data.columns)
    data = data.rename(columns=get_col_map(source))
    data = data[get_col_order()]
    # add metadata
    data['date'] = date
    data['run'] = run
    data['delta'] = delta
    data['ref_time'] = ref_time
    return data