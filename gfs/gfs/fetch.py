from datetime import timedelta
import warnings
import logging
import tempfile
import requests
from functools import reduce

import numpy as np
import pandas as pd
import xarray as xr
import cfgrib
import gfs.constants as constants

logger = logging.getLogger(__name__)


def get_col_map(source='hist'):
    """
    Returns a dictionary mapping {source}_name to the corresponding key in SCHEMA.
    """
    logger.debug(f"Generating column map for source: {source}")
    return {details[f'{source}_name']: key for key, details in constants.SCHEMA.items()}


def get_col_order():
    """
    Returns a list of keys from SCHEMA ordered by their position.
    """
    logger.debug("Retrieving column order based on SCHEMA positions")
    return sorted(constants.SCHEMA.keys(), key=lambda key: constants.SCHEMA[key]['position'])


def get_gfs_hist_url(date, run, time):
    """
    Returns the URL to the GFS historical data for the given date, run, and time.
    """
    date_str = date.strftime("%Y%m%d")
    year_str = date.strftime("%Y")
    url = f"{constants.GFS_HIST_BASE}/{year_str}/{date_str}/gfs.0p25.{date_str}{run:02d}.f{time:03d}.grib2"
    logger.debug(f"Constructed historical GFS URL: {url}")
    return url


def get_gfs_forecast_url(date, run, res='0p25'):
    """
    Returns the URL to the GFS forecast data for the given date, run, and resolution.
    """
    date_str = date.strftime("%Y%m%d")
    url = f"{constants.GFS_FORECAST_BASE}/gfs_{res}/gfs{date_str}/gfs_{res}_{run:02d}z"
    logger.debug(f"Constructed forecast GFS URL: {url}")
    return url


def get_gfs_grib_url(date, run, delta):
    date_str = date.strftime("%Y%m%d")
    url = (
     f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?dir=%2Fgfs.{date_str}%2F{run:02d}%2Fatmos&file=gfs.t{run:02d}z.pgrb2.0p25.f{delta:03d}&"
     "var_DPT=on&var_GUST=on&var_HGT=on&var_PRES=on&var_PWAT=on&var_RH=on&var_TMP=on&var_UGRD=on&var_VGRD=on&lev_2_m_above_ground=on&lev_10_m_above_ground=on&lev_80_m_above_ground=on&lev_100_m_above_ground=on&lev_1000_mb=on&lev_975_mb=on&lev_950_mb=on&lev_925_mb=on&lev_900_mb=on&lev_850_mb=on&lev_800_mb=on&lev_750_mb=on&lev_700_mb=on&lev_650_mb=on&lev_600_mb=on&lev_550_mb=on&lev_500_mb=on&lev_surface=on&lev_entire_atmosphere_(considered_as_a_single_layer)=on&subregion=&toplat=52&leftlon=6.5&rightlon=20.75&bottomlat=41.5"
    )
    return url


def flatten_column_names(columns):
    """
    Flattens the column names by removing the level and appending it to the name.
    """
    logger.debug("Flattening column names")
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
    logger.debug("Retrieving indexes from dataset")
    idexes = dict()
    for var in variables:
        if variables[var] is None:
            continue
        index = next((index_name for index_name in ds[var].indexes if index_name not in ['lat', 'lon', 'time', 'time1']), None)
        if index not in idexes:
            idexes[index] = variables[var]
    return idexes


def _download_hist_data(date, run, delta, lat_gfs, lon_gfs):
    """
    Downloads the historical GFS data for the given date, run, and delta.
    """
    logger.info(f"Starting download of historical GFS data for date: {date}, run: {run}, delta: {delta}")
    pds = []
    url = get_gfs_hist_url(date, run, delta)
    logger.debug(f"Historical data URL: {url}")
    try:
        with xr.open_dataset(url) as ds:
            logger.debug("Opened historical dataset successfully")
            query = get_idexes(ds, constants.VARIABLES_HIST)
            query['lat'] = np.unique(lat_gfs)
            query['lon'] = np.unique(lon_gfs)
            logger.debug(f"Query parameters for historical data selection: {query}")
            data = ds[list(constants.VARIABLES_HIST.keys())].sel(**query)
            logger.debug("Selected historical data based on query parameters")
            
            for idx in range(len(lat_gfs)):
                data_idx = data.sel(lat=[lat_gfs[idx]], lon=[lon_gfs[idx]])
                stacked = data_idx.stack(points=('lat', 'lon'), create_index=True)
                pds.append(stacked.to_stacked_array('x', sample_dims=['points']).to_pandas())
                logger.debug(f"Processed data for lat: {lat_gfs[idx]}, lon: {lon_gfs[idx]}")
            
        logger.info("Completed downloading and processing historical GFS data")
        return pd.concat(pds)
    except Exception as e:
        logger.error(f"Failed to download historical GFS data from {url}: {e}")
        raise


def _download_forecast_data(date, run, ref_time, lat_gfs, lon_gfs):
    """
    Downloads the forecast GFS data for the given date, run, and reference time.
    """
    logger.info(f"Starting download of forecast GFS data for date: {date}, run: {run}, reference time: {ref_time}")
    pds = []
    url = get_gfs_forecast_url(date, run)
    logger.debug(f"Forecast data URL: {url}")
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                category=xr.SerializationWarning,
                module=r"xarray",
            )
            with xr.open_dataset(url) as ds:
                logger.debug("Opened forecast dataset successfully")
                data = ds[list(constants.VARIABLES_FORECAST)].sel(
                    time=ref_time, 
                    lat=np.unique(lat_gfs), 
                    lon=np.unique(lon_gfs), 
                    lev=constants.HPA_LVLS
                )
                logger.debug("Selected forecast data based on query parameters")
    
                for idx in range(len(lat_gfs)):
                    data_idx = data.sel(lat=[lat_gfs[idx]], lon=[lon_gfs[idx]])
                    stacked = data_idx.stack(points=('lat', 'lon'), create_index=True)
                    pds.append(stacked.to_stacked_array('x', sample_dims=['points']).to_pandas())
                    logger.debug(f"Processed forecast data for lat: {lat_gfs[idx]}, lon: {lon_gfs[idx]}")
        logger.info("Completed downloading and processing forecast GFS data")
        return pd.concat(pds)
    except Exception as e:
        logger.error(f"Failed to download forecast GFS data from {url}: {e}")
        raise


def _download_grib_data(date, run, delta, lat_gfs, lon_gfs):
    """
    Downloads the GRIB GFS data for the given date, run, delta, and coordinates.
    """
    logger.info(f"Starting download of GRIB GFS data for date: {date}, run: {run}, delta: {delta}")
    url = get_gfs_grib_url(date, run, delta)
    logger.debug(f"GRIB data URL: {url}")
    points = pd.DataFrame({'lat': lat_gfs, 'lon': lon_gfs})
    lat = xr.DataArray(points['lat'], dims=['points'])
    lon = xr.DataArray(points['lon'], dims=['points'])
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            logger.debug("Created temporary file for GRIB data")
            response = requests.get(url)
            temp_file.write(response.content)
            temp_file_path = temp_file.name
            logger.debug(f"Downloaded GRIB data to temporary file: {temp_file_path}")

            grib_data = cfgrib.open_datasets(temp_file_path, backend_kwargs={'indexpath': ''})
            logger.debug("Opened GRIB datasets successfully")
            pds = []
            for idx in range(len(grib_data)):
                pdf = grib_data[idx].sel(latitude=lat, longitude=lon).to_stacked_array('x', sample_dims=['points']).to_pandas()
                pdf.columns = flatten_column_names(pdf.columns)
                pds.append(pdf)
                logger.debug(f"Processed GRIB dataset {idx+1}/{len(grib_data)}")

            pdf = reduce(lambda x, y: pd.merge(x, y, on = 'points'), pds)
            logger.debug("Merged all GRIB datasets")

            pdf = pdf.rename(columns=get_col_map('grib'))
            pdf = pdf[get_col_order()]
            logger.debug("Renamed columns and reordered according to schema")

            pdf = pdf.join(points).set_index(['lat', 'lon']).rename_axis(index={'lat': 'lat', 'lon': 'lon'})
            logger.debug("Added latitude and longitude information to the dataset")

        logger.info("Completed downloading and processing GRIB GFS data")
        return pdf
    except Exception as e:
        logger.error(f"Failed to download GRIB GFS data from {url}: {e}")
        raise


def get_gfs_data(date, run, delta, lat_gfs, lon_gfs, source='hist'):
    """
    Downloads the GFS data for the given date, run, delta, latitude, longitude, and source.
    """
    logger.info(f"Fetching GFS data with source: {source} for date: {date}, run: {run}, delta: {delta}")
    assert source in ['hist', 'forecast', 'grib'], 'Source must be either hist, forecast or grib'
    
    ref_time = date.replace(hour=run) + timedelta(hours=delta)
    logger.debug(f"Reference time calculated as: {ref_time}")

    try:
        if source == 'hist':
            logger.debug("Source set to historical data")
            data = _download_hist_data(date, run, delta, lat_gfs, lon_gfs)
            # force schema
            logger.debug("Flattening and renaming data columns to match schema")
            data.columns = flatten_column_names(data.columns)
            data = data.rename(columns=get_col_map(source))
            data = data[get_col_order()]
        elif source == 'forecast':
            logger.debug("Source set to forecast data")
            data = _download_forecast_data(date, run, ref_time, lat_gfs, lon_gfs)            # force schema
            logger.debug("Flattening and renaming data columns to match schema")
            data.columns = flatten_column_names(data.columns)
            data = data.rename(columns=get_col_map(source))
            data = data[get_col_order()]
        elif source == 'grib':
            logger.debug("Source set to GRIB data")
            data = _download_grib_data(date, run, delta, lat_gfs, lon_gfs)
        # add metadata
        logger.debug("Adding metadata to data")
        data['date'] = date
        data['run'] = run
        data['delta'] = delta
        data['ref_time'] = ref_time
        logger.info("GFS data fetching and processing completed successfully")
        return data
    except Exception as e:
        logger.error(f"Error in get_gfs_data: {e}")
        raise


def add_gfs_forecast(launches, date, run, delta, source='grib'):
    """
    Add GFS forecast data to launch data.

    Args:
        launches (pd.DataFrame): DataFrame containing launch data with 'lat_gfs' and 'lon_gfs' columns.
        date (datetime): The date of the forecast.
        run (int): The run time of the forecast.
        delta (int): The time delta for the forecast.

    Returns:
        pd.DataFrame: Joined DataFrame of GFS forecast data and launch data.
    """
    logger.info("Adding GFS forecast data to launch data")
    try:
        points = launches[['lat_gfs', 'lon_gfs']].drop_duplicates()
        lat_gfs = points['lat_gfs'].values
        lon_gfs = points['lon_gfs'].values
        logger.debug(f"Unique latitude and longitude points extracted: {len(lat_gfs)} points")

        gfs_data = get_gfs_data(date, run, delta, lat_gfs, lon_gfs, source=source)
        logger.debug("GFS data retrieved successfully, proceeding to join with launch data")

        joined = gfs_data.join(launches.set_index(['lat_gfs', 'lon_gfs']), on=['lat', 'lon'])
        logger.info("Successfully joined GFS data with launch data")
        return joined
    except Exception as e:
        logger.error(f"Error in add_gfs_forecast: {e}")
        raise