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

    This function scrapes the NOMADS gribfilter page to find the most recent date
    for which forecast data is available. It looks for dates in the format 'gfs.YYYYMMDD'.

    Returns:
    str: The latest available date in 'YYYYMMDD' format, or None if no valid dates are found
         or if an error occurs during the process.
    """
    url = "https://nomads.ncep.noaa.gov/gribfilter.php?ds=gfs_0p25"
    try:
        response = requests.get(url)
        response.raise_for_status()

        pattern = re.compile(r'gfs\.(\d{8})')
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

    This function checks the NOMADS gribfilter page for a specific date to find the most
    recent run (cycle) that actually has files available. It checks cycles in descending
    order (18, 12, 06, 00) and verifies that files exist for each cycle.

    Args:
    date_str (str): The date string in 'YYYYMMDD' format.

    Returns:
    int: The latest available run number (0, 6, 12, or 18), or None if no valid runs
         are found or if an error occurs during the process.
    """
    base_url = "https://nomads.ncep.noaa.gov/gribfilter.php"
    cycles = [18, 12, 6, 0]

    for cycle in cycles:
        cycle_str = f"{cycle:02d}"
        url = f"{base_url}?ds=gfs_0p25&dir=%2Fgfs.{date_str}%2F{cycle_str}%2Fatmos"
        try:
            response = requests.get(url)
            response.raise_for_status()

            # Check if files for this specific cycle exist
            # Files are named like gfs.t18z.pgrb2.0p25.f000 or gfs.t18z.pgrb2.0p25.anl
            pattern = re.compile(rf'gfs\.t{cycle_str}z\.pgrb2\.0p25\.(f\d{{3}}|anl)')
            if pattern.search(response.text):
                logger.info(f"Found available run: {cycle} for date {date_str}")
                return cycle

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from {url}: {e}")
            continue
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            continue

    logger.warning(f"No valid run numbers found for date {date_str}.")
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
