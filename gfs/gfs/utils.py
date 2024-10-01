import numpy as np

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
