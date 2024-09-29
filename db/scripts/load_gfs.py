"""
This script is responsible for loading Global Forecast System (GFS) data into a database.

It performs the following main tasks:
1. Fetches launch site information from a database
2. Retrieves GFS weather data for specified dates and locations
3. Processes and transforms the GFS data
4. Loads the processed data into a database table

The script uses various libraries including xarray for handling meteorological data,
pandas for data manipulation, and SQLAlchemy for database operations.

Usage:
    This script is typically run as part of a data pipeline to update weather forecasts
    for launch sites. It requires proper environment setup, including database credentials.
"""

import os
import logging
import argparse

import xarray as xr
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

import gfs


SCHEMA = "source"
TABLE = "gfs"

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_launches(engine):
    """
    Fetch launch site information from the database.

    Args:
        engine: SQLAlchemy engine object for database connection.

    Returns:
        pandas.DataFrame: DataFrame containing launch site information.
    """
    logging.info("Fetching launch sites from the database.")
    query = """
    SELECT
        name,
        latitude,
        longitude
    FROM
        glideator_mart.dim_launches
    """
    launches = pd.read_sql(query, con=engine)
    launches['lat_gfs'] = gfs.round_to_nearest_quarter(launches['latitude'])
    launches['lon_gfs'] = gfs.round_to_nearest_quarter(launches['longitude'])
    logging.info(f"Retrieved {len(launches)} launch sites.")
    return launches


def get_db_engine():
    """
    Create and return a SQLAlchemy database engine using environment variables.

    Returns:
        sqlalchemy.engine.Engine: Database engine object.
    """
    logging.info("Creating database engine.")
    connection_string = "postgresql://{user}:{password}@{host}:{port}/{db}".format(
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        db=os.getenv('DB_NAME')
    )
    return create_engine(connection_string)


def get_gfs_data(start_date, end_date, run, delta, lat_gfs, lon_gfs, engine):
    """
    Fetch GFS data for a range of dates and launch sites.

    Args:
        start_date: datetime object for the start date.
        end_date: datetime object for the end date.
        run: int for the run number.
        delta: int for the delta in hours.
        lat_gfs: pandas.Series for the latitude.
        lon_gfs: pandas.Series for the longitude.
        engine: SQLAlchemy engine object for database connection.

    Returns:
        pandas.DataFrame: DataFrame containing GFS data for the specified date range and launch sites.
    """
    logging.info(f"Fetching GFS data from {start_date} to {end_date}.")
    for date in pd.date_range(start_date, end_date):
        logging.info(f"Fetching GFS data for {date}.")
        try:
            load_gfs_data(
                gfs.get_gfs_data(date, run, delta, lat_gfs, lon_gfs, source='hist'),
                engine
            )
        except Exception as e:
            logging.error(f"Error fetching GFS data for {date}: {e}")
    logging.info("Completed fetching GFS data for the date range.")


def load_gfs_data(gfs_data, engine):
    """
    Load GFS data into the database table.

    Args:
        gfs_data: pandas.DataFrame containing GFS data to be loaded.
        engine: SQLAlchemy engine object for database connection.
    """
    logging.info(f"Loading GFS data into the database table {SCHEMA}.{TABLE}.")
    gfs_data.to_sql(name=TABLE, schema=SCHEMA, con=engine, if_exists='append', index=True)
    logging.info("GFS data loaded successfully.")


def main():
    """
    Main function to fetch and load GFS data into the database.

    This function performs the following steps:
    1. Loads environment variables from a .env file.
    2. Parses command-line arguments to get the start and end dates.
    3. Converts the start and end dates from string format to datetime objects.
    4. Creates a database engine using the provided connection details.
    5. Retrieves the list of launch sites from the database.
    6. Fetches GFS data for the specified date range and launch sites.
    7. Loads the fetched GFS data into the database.

    Command-line Arguments:
        --start_date (str): The start date in 'YYYY-MM-DD' format.
        --end_date (str): The end date in 'YYYY-MM-DD' format.

    Example:
        python load_gfs.py --start_date 2023-01-01 --end_date 2023-01-31
    """
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start_date', type=str, required=True, help='Start date in YYYY-MM-DD format (inclusive)')
    parser.add_argument('--end_date', type=str, required=True, help='End date in YYYY-MM-DD format (inclusive)')
    parser.add_argument('--run', type=int, default=12, help='Run number')
    parser.add_argument('--delta', type=int, default=0, help='Delta in hours')
    args = parser.parse_args()
    start_date = pd.to_datetime(args.start_date, format='%Y-%m-%d')
    end_date = pd.to_datetime(args.end_date, format='%Y-%m-%d')
    engine = get_db_engine()
    launches = get_launches(engine)
    points = launches[['lat_gfs', 'lon_gfs']].drop_duplicates()
    get_gfs_data(start_date, end_date, int(args.run), int(args.delta), points['lat_gfs'].values, points['lon_gfs'].values, engine)


if __name__ == "__main__":
    main()
