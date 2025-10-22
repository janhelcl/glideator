import logging
import numpy as np

logger = logging.getLogger(__name__)


def add_targets(df, max_points_col='max_points', thresholds=[0, 10, 20, 30, 40, 50]):
    """
    Add binary target columns to the dataframe based on max points thresholds.

    This function creates new columns in the dataframe, each representing a binary
    classification target based on whether the max points exceed a given threshold.

    Args:
        df (pandas.DataFrame): Input dataframe containing the max points column.
        max_points_col (str, optional): Name of the column containing max points. 
                                        Defaults to 'max_points'.
        thresholds (list, optional): List of threshold values for creating binary targets. 
                                     Defaults to [0, 10, 20, 30, 40, 50].

    Returns:
        pandas.DataFrame: The input dataframe with added binary target columns.

    Note:
        - The function adds new columns named 'XC{threshold}' for each threshold.
        - Each 'XC{threshold}' column contains 1 if max_points > threshold, else 0.
        - The function modifies the input dataframe in-place and also returns it.
    """
    logger.info(f"Adding target columns with thresholds: {thresholds}")
    for threshold in thresholds:
        logger.debug(f"Applying threshold: {threshold}")
        df[f'XC{threshold}'] = df[max_points_col].apply(lambda x: 1 if x > threshold else 0)
    return df


def add_date_features(df, date_col='date'):
    """Adds date features to the dataframe.

    This function enhances the input dataframe with additional date-related features:
    - 'weekend': A boolean indicating whether the date is a weekend (Saturday or Sunday).
    - 'year': The year extracted from the date.
    - 'day_of_year_sin' and 'day_of_year_cos': Cyclical encoding of the day of the year,
      using sine and cosine transformations to capture the circular nature of annual patterns.

    Args:
        df (pandas.DataFrame): Input dataframe containing a date column.
        date_col (str, optional): Name of the date column. Defaults to 'date'.

    Returns:
        pandas.DataFrame: The input dataframe with added date features.

    Note:
        - The function assumes the specified date column is in a datetime format.
        - The function modifies the input dataframe in-place and also returns it.
        - The cyclical encoding uses 365.25 days per year to account for leap years.
        - The function modifies the input dataframe in-place and also returns it.
    """
    logger.info(f"Adding date features using date column: '{date_col}'")
    df['weekend'] = df[date_col].apply(lambda date: date.weekday() >= 5).astype(int)
    df['year'] = df[date_col].apply(lambda date: date.year)
    day_of_year = df[date_col].apply(lambda date: date.timetuple().tm_yday)
    df['day_of_year_sin'] = np.sin(2 * np.pi * day_of_year / 365.25)
    df['day_of_year_cos'] = np.cos(2 * np.pi * day_of_year / 365.25)
    return df
