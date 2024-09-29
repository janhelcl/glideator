import os
import json
from datetime import datetime, timedelta
import warnings

import numpy as np
import pandas as pd
import xarray as xr


GFS_HIST_BASE = "https://thredds.rda.ucar.edu/thredds/dodsC/files/g/d084001"
GFS_FORECAST_BASE = "https://nomads.ncep.noaa.gov/dods"

PA_LVLS = [50000, 55000,60000, 65000, 70000, 75000, 80000, 85000,90000, 92500, 95000, 97500, 100000]
HPA_LVLS = np.array(PA_LVLS) / 100
WIND_AGL_LVLS = [10., 100.]
TEMP_AGL_LVLS = [2., 80., 100.]
DEWPOINT_AGL_LVLS = [2.]

VARIABLES_HIST = {
    # wind
    'u-component_of_wind_isobaric': PA_LVLS, 
    'v-component_of_wind_isobaric': PA_LVLS,
    'u-component_of_wind_height_above_ground': WIND_AGL_LVLS,
    'v-component_of_wind_height_above_ground': WIND_AGL_LVLS,
    'Wind_speed_gust_surface': None,
    #temperature
    'Temperature_isobaric': PA_LVLS,
    'Temperature_height_above_ground': TEMP_AGL_LVLS,
    'Dewpoint_temperature_height_above_ground': DEWPOINT_AGL_LVLS,
    #pressure
    'Pressure_surface': None,
    #humidity
    'Precipitable_water_entire_atmosphere_single_layer': None,
    'Relative_humidity_isobaric': PA_LVLS,
    #geopotential
    'Geopotential_height_isobaric': PA_LVLS,
    'Geopotential_height_surface': None
}

VARIABLES_FORECAST = [
    #wind
    'ugrdprs',
    'vgrdprs',
    'ugrd10m',
    'vgrd10m',
    'ugrd100m',
    'vgrd100m',
    'gustsfc',
    #temperature
    'tmpprs',
    'tmp2m',
    'tmp80m',
    'tmp100m',
    'dpt2m',
    #pressure
    'pressfc',
    #humidity
    'pwatclm',
    'rhprs',
    #geopotential
    'hgtprs',
    'hgtsfc'
]

current_dir = os.path.dirname(os.path.abspath(__file__))
schema_path = os.path.join(current_dir, 'schema.json')
SCHEMA = json.load(open(schema_path))


def get_col_map(source='hist'):
    """
    Returns a dictionary mapping {source}_name to the corresponding key in SCHEMA.
    """
    return {details[f'{source}_name']: key for key, details in SCHEMA.items()}


def get_col_order():
    """
    Returns a list of keys from SCHEMA ordered by their position.
    """
    return sorted(SCHEMA.keys(), key=lambda key: SCHEMA[key]['position'])

def get_gfs_hist_url(date, run, time):
    """
    Returns the URL to the GFS historical data for the given date, run, and time.
    """
    date_str = date.strftime("%Y%m%d")
    year_str = date.strftime("%Y")
    return f"{GFS_HIST_BASE}/{year_str}/{date_str}/gfs.0p25.{date_str}{run:02d}.f{time:03d}.grib2"


def get_gfs_forecast_url(date, run, res='0p25'):
    """
    Returns the URL to the GFS forecast data for the given date, run, and resolution.
    """
    date_str = date.strftime("%Y%m%d")
    return f"{GFS_FORECAST_BASE}/gfs_{res}/gfs{date_str}/gfs_{res}_{run:02d}z"


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

def round_to_nearest_quarter(arr):
    arr = np.array(arr)
    return np.round(arr / 0.25) * 0.25


def _download_hist_data(date, run, delta, lat_gfs, lon_gfs):
    """
    Downloads the historical GFS data for the given date, run, and delta.
    """
    pds = []
    url = get_gfs_hist_url(date, run, delta)
    with xr.open_dataset(url) as ds:
        query = get_idexes(ds, VARIABLES_HIST)
        query['lat'] = np.unique(lat_gfs)
        query['lon'] = np.unique(lon_gfs)
        data = ds[VARIABLES_HIST.keys()].sel(**query)
        
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
            data = ds[VARIABLES_FORECAST].sel(time=ref_time, lat=np.unique(lat_gfs), lon=np.unique(lon_gfs), lev=HPA_LVLS)

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