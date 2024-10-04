import logging
import numpy as np
import torch
from sklearn.preprocessing import StandardScaler, LabelEncoder

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


class Preprocessor:
    """
    Preprocesses the input data by scaling features and encoding categorical variables.

    Attributes:
        features (list): List of feature names to be scaled.
        scaler (StandardScaler): Scaler object for feature scaling.
        launch_indexer (LabelEncoder): Label encoder for encoding launch categories.
    """

    def __init__(self, features):
        """
        Initializes the Preprocessor with specified features.

        Args:
            features (list): List of feature names to be scaled.
        """
        logger.info(f"Initializing Preprocessor with features: {features}")
        self.features = features

    def fit(self, df):
        """
        Fits the scaler and label encoder to the data.

        Args:
            df (pandas.DataFrame): DataFrame containing the data to fit the scaler and encoder.
        """
        logger.info("Fitting scaler and label encoder to data.")
        self.scaler = StandardScaler()
        self.launch_indexer = LabelEncoder()
        self.scaler.fit(df[self.features])
        self.launch_indexer.fit(df['launch'])
        logger.debug("Scaler and label encoder have been fitted.")

    def transform(self, df):
        """
        Transforms the data using the fitted scaler and label encoder.

        Args:
            df (pandas.DataFrame): DataFrame containing the data to transform.

        Returns:
            tuple: A tuple containing:
                - torch.FloatTensor: Scaled feature tensors.
                - torch.LongTensor: Encoded launch tensors.
        """
        logger.info("Transforming data using the fitted scaler and label encoder.")
        scaled_features = self.scaler.transform(df[self.features])
        launch_encoded = self.launch_indexer.transform(df['launch'])
        logger.debug(f"Scaled features shape: {scaled_features.shape}")
        logger.debug(f"Encoded launch shape: {launch_encoded.shape}")
        return torch.FloatTensor(scaled_features), torch.LongTensor(launch_encoded)