import requests
import logging
import re
from datetime import datetime

import numpy as np

import gfs.constants as constants

logger = logging.getLogger(__name__)


def round_to_nearest_quarter(arr):
    """
    Rounds the elements of the input array to the nearest quarter (0.25).

    Parameters:
    arr (array-like): Input array to be rounded.

    Returns:
    numpy.ndarray: Array with elements rounded to the nearest quarter.
    """
    arr = np.array(arr)
    return np.round(arr / 0.25) * 0.25


def gfs_lat(lat):
    """
    Rounds the latitude to the nearest quarter.

    Parameters:
    lat (float or array-like): Latitude value(s) to be rounded.

    Returns:
    float or numpy.ndarray: Rounded latitude value(s).
    """
    return round_to_nearest_quarter(lat)


def gfs_lon(lon):
    """
    Rounds the longitude to the nearest quarter and adjusts for negative values.

    Parameters:
    lon (float or array-like): Longitude value(s) to be rounded.

    Returns:
    float or numpy.ndarray: Rounded and adjusted longitude value(s).
    """
    lon = round_to_nearest_quarter(lon)
    if lon < 0:
        lon += 360
    return lon


def find_latest_available_date():
    """
    Finds the latest available date for GFS forecast data.

    This function scrapes the GFS forecast base URL to find the most recent date
    for which forecast data is available. It looks for directories named in the
    format 'gfsYYYYMMDD/'.

    Returns:
    str: The latest available date in 'YYYYMMDD' format, or None if no valid dates are found
         or if an error occurs during the process.
    """
    url = f'{constants.GFS_FORECAST_BASE}/gfs_0p25'
    try:
        response = requests.get(url)
        response.raise_for_status()

        pattern = re.compile(r'gfs(\d{8})/')
        dates = pattern.findall(response.text)

        if not dates:
            logger.warning("No valid date directories found.")
            return None

        return max(dates)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return None


def find_latest_available_run(date_str):
    """
    Finds the latest available run for a given date in GFS forecast data.

    This function scrapes the GFS forecast URL for a specific date to find the most recent
    run number available. It looks for patterns like 'gfs_0p25_XXz' where XX is the run number.

    Args:
    date_str (str): The date string in 'YYYYMMDD' format.

    Returns:
    int: The latest available run number (0-23), or None if no valid runs are found
         or if an error occurs during the process.
    """
    url = f'{constants.GFS_FORECAST_BASE}/gfs_0p25/gfs{date_str}'
    try:
        response = requests.get(url)
        response.raise_for_status()

        pattern = re.compile(r'gfs_0p25_(\d{2})z:')
        runs = pattern.findall(response.text)
        runs = map(int, runs)

        if not runs:
            logger.warning("No valid run numbers found.")
            return None

        return max(runs)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return None


def find_latest_forecast_parameters():
    """
    Finds the latest available forecast parameters (date and run number).

    This function combines the results of find_latest_available_date() and
    find_latest_available_run() to get the most up-to-date forecast parameters.

    Returns:
    tuple: A tuple containing:
           - datetime object representing the latest available date
           - int representing the latest available run number
    """
    latest_date = find_latest_available_date()
    latest_run = find_latest_available_run(latest_date)
    return datetime.strptime(latest_date, "%Y%m%d"), latest_run


def find_delta(latest_hour, target_hour):
    """
    Find the delta between the latest hour and the nearest future target hour.
    
    Args:
    latest_hour (int): The current hour (0-23)
    target_hour (int): The target hour (0-23)
    
    Returns:
    int: The number of hours until the next occurrence of the target hour
    """
    if latest_hour <= target_hour:
        return target_hour - latest_hour
    else:
        return (24 - latest_hour) + target_hour
