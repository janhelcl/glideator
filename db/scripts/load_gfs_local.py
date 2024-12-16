"""
This script loads Global Forecast System (GFS) data from local GRIB files into a database.

It performs the following main tasks:
1. Scans a specified folder for GFS GRIB files
2. Processes each file to extract weather data
3. Loads the processed data into a database table

Usage:
    python load_gfs_local.py --folder /path/to/grib/files --sites_only
    
The --sites_only flag is optional and when set, will only load data for known sites.
Otherwise, it will load all points from the GRIB files.
"""

import os
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import xarray as xr
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

import gfs.fetch
import gfs.constants
import gfs.utils

SCHEMA = "source"
TABLE = "gfs"

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_gfs_filename(filename):
    """Extract date, run and delta from GFS filename.
    
    Args:
        filename (str): Full path to file in format path/to/gfs.0p25.YYYYMMDDHH.fDDD.grib2
        
    Returns:
        tuple: (date as datetime, run as int, delta as int)
    """
    basename = os.path.basename(filename)
    
    pattern = r'gfs\.0p25\.(\d{10})\.f(\d{3})\.grib2'
    import re
    match = re.search(pattern, basename)
    
    if not match:
        raise ValueError(f"Invalid filename format: {filename}")
        
    datetime_str = match.group(1)
    delta = int(match.group(2))
    
    date = datetime.strptime(datetime_str[:8], '%Y%m%d')
    run = int(datetime_str[8:10])
    
    return date, run, delta

def get_sites(engine):
    """
    Fetch site information from the database.

    Args:
        engine: SQLAlchemy engine object for database connection.

    Returns:
        pandas.DataFrame: DataFrame containing launch site information.
    """
    logger.info("Fetching sites from the database.")
    query = """
    SELECT
        name,
        lat_gfs,
        lon_gfs
    FROM
        glideator_mart.dim_sites
    """
    sites = pd.read_sql(query, con=engine)
    logger.info(f"Retrieved {len(sites)} sites.")
    return sites

def get_db_engine():
    """
    Create and return a SQLAlchemy database engine using environment variables.

    Returns:
        sqlalchemy.engine.Engine: Database engine object.
    """
    logger.info("Creating database engine.")
    connection_string = "postgresql://{user}:{password}@{host}:{port}/{db}".format(
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        db=os.getenv('DB_NAME')
    )
    return create_engine(connection_string)

def process_grib_file(file_path, lat_points=None, lon_points=None):
    """
    Process a single GRIB file and return the extracted data.
    
    Args:
        file_path (str): Path to the GRIB file
        lat_points (array-like, optional): Specific latitude points to extract
        lon_points (array-like, optional): Specific longitude points to extract
        
    Returns:
        pandas.DataFrame: Processed GFS data
    """
    logger.info(f"Processing file: {file_path}")
    
    date, run, delta = parse_gfs_filename(file_path)
    
    ds = xr.open_dataset(file_path)
    ds = ds.assign_coords(longitude=(((ds.longitude + 180) % 360) - 180))
    ds = ds.rename({'latitude': 'lat', 'longitude': 'lon'})

    query = gfs.fetch.get_idexes(ds, gfs.constants.VARIABLES_HIST)
    
    if lat_points is not None and lon_points is not None:
        query['lat'] = np.unique(lat_points)
        query['lon'] = np.unique(lon_points)
    
    data = ds[gfs.constants.VARIABLES_HIST.keys()].sel(**query)
    
    pds = []
    if lat_points is not None and lon_points is not None:
        for idx in range(len(lat_points)):
            data_idx = data.sel(lat=[lat_points[idx]], lon=[lon_points[idx]])
            stacked = data_idx.stack(points=('lat', 'lon'), create_index=True)
            pds.append(stacked.to_stacked_array('x', sample_dims=['points']).to_pandas())
    else:
        stacked = data.stack(points=('lat', 'lon'), create_index=True)
        pds.append(stacked.to_stacked_array('x', sample_dims=['points']).to_pandas())

    res = pd.concat(pds)
    res.columns = gfs.fetch.flatten_column_names(res.columns)
    res = res.rename(columns=gfs.fetch.get_col_map('hist'))
    res = res[gfs.fetch.get_col_order()]
    
    ref_time = date.replace(hour=run) + timedelta(hours=delta)
    res['date'] = date
    res['run'] = run
    res['delta'] = delta
    res['ref_time'] = ref_time
    
    return res

def load_gfs_data(gfs_data, engine):
    """
    Load GFS data into the database table.

    Args:
        gfs_data: pandas.DataFrame containing GFS data to be loaded.
        engine: SQLAlchemy engine object for database connection.
    """
    logger.info(f"Loading GFS data into the database table {SCHEMA}.{TABLE}.")
    gfs_data.to_sql(name=TABLE, schema=SCHEMA, con=engine, if_exists='append', index=True)
    logger.info("GFS data loaded successfully.")

def main():
    """
    Main function to process GRIB files and load data into the database.
    """
    load_dotenv()
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=str, required=True, help='Folder containing GRIB files')
    parser.add_argument('--sites_only', action='store_true', help='Only process sites')
    args = parser.parse_args()
    
    engine = get_db_engine()
    
    lat_points = None
    lon_points = None
    
    if args.sites_only:
        sites = get_sites(engine)
        points = sites[['lat_gfs', 'lon_gfs']].drop_duplicates()
        lat_points = points['lat_gfs'].values
        lon_points = points['lon_gfs'].values
    
    folder_path = Path(args.folder)
    grib_files = list(folder_path.glob('*.grib2'))
    
    logger.info(f"Found {len(grib_files)} GRIB files to process")
    
    for file_path in grib_files:
        try:
            gfs_data = process_grib_file(file_path, lat_points, lon_points)
            load_gfs_data(gfs_data, engine)
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            continue

if __name__ == "__main__":
    main()