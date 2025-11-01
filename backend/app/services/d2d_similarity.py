import os
import logging
import pickle
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import date, datetime

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sklearn.metrics.pairwise import cosine_similarity

from .. import models
from ..services.forecast import (
    WEATHER_FEATURES,
    SITE_FEATURES,
    DATE_FEATURES,
    REFERENCES,
    fetch_sites,
)
import net.preprocessing as preprocessing
import gfs.fetch
from gfs.constants import HPA_LVLS

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
SCALER_PATH = BASE_DIR / 'models' / 'd2d_scaler.pkl'

# Cache for scaler
_scaler_cache: Optional[object] = None


def load_scaler():
    """Load and cache the d2d scaler."""
    global _scaler_cache
    if _scaler_cache is None:
        logger.info(f"Loading scaler from {SCALER_PATH}")
        with open(SCALER_PATH, 'rb') as f:
            _scaler_cache = pickle.load(f)
        logger.info(f"Scaler loaded successfully. Expects {_scaler_cache.n_features_in_} features")
    else:
        logger.debug("Using cached scaler")
    return _scaler_cache


def extract_features_from_forecast(
    row: pd.Series,
    site_latitude: float = None,
    site_longitude: float = None,
    site_altitude: int = None,
    ref_date: date = None
) -> np.ndarray:
    """
    Extract WEATHER_FEATURES from forecast row for d2d similarity.
    Note: Only weather features are used for scaling (site and date features are excluded).
    
    Args:
        row: DataFrame row with forecast data (joined_forecasts format)
        site_latitude: Site latitude (unused, kept for compatibility)
        site_longitude: Site longitude (unused, kept for compatibility)
        site_altitude: Site altitude (unused, kept for compatibility)
        ref_date: Reference date (unused, kept for compatibility)
    
    Returns:
        numpy array of weather features only (same as what's in scaled_features table)
    """
    logger.debug(f"Extracting weather features from forecast row. Expected {len(WEATHER_FEATURES)} features")
    
    # Extract only weather features in order (same as scaled_features table)
    weather_feat = []
    missing_features = []
    for feat_name in WEATHER_FEATURES:
        if feat_name in row.index:
            weather_feat.append(row[feat_name])
        else:
            logger.warning(f"Feature {feat_name} not found in row, using 0")
            weather_feat.append(0.0)
            missing_features.append(feat_name)
    
    if missing_features:
        logger.warning(f"Missing {len(missing_features)} features out of {len(WEATHER_FEATURES)}")
    
    # Return only weather features (231 features expected by scaler)
    features = np.array(weather_feat, dtype=np.float32)
    logger.debug(f"Extracted {len(features)} features. Min: {features.min():.4f}, Max: {features.max():.4f}, Mean: {features.mean():.4f}")
    return features


async def find_similar_days(
    db: AsyncSession,
    site_id: int,
    scaled_features: np.ndarray,
    top_k: int = 5
) -> List[Tuple[date, float]]:
    """
    Find top K similar past days for a given site using cosine similarity.
    
    Args:
        db: Database session
        site_id: Site ID to search within
        scaled_features: Scaled feature vector for current forecast
        top_k: Number of similar days to return
    
    Returns:
        List of (past_date, similarity_score) tuples, ordered by similarity (highest first)
    """
    logger.debug(f"Finding {top_k} similar days for site_id {site_id}")
    
    # Query scaled_features for this site_id
    query = select(models.ScaledFeature).where(
        models.ScaledFeature.site_id == site_id
    )
    result = await db.execute(query)
    past_features = result.scalars().all()
    
    if not past_features:
        logger.warning(f"No past features found for site_id {site_id}")
        return []
    
    logger.debug(f"Found {len(past_features)} past feature vectors for site_id {site_id}")
    
    # Prepare arrays for similarity computation
    past_dates = []
    past_vectors = []
    
    for pf in past_features:
        past_dates.append(pf.date)
        # Convert PostgreSQL array to numpy array
        past_vectors.append(np.array(pf.features, dtype=np.float32))
    
    if not past_vectors:
        logger.warning(f"No valid past vectors for site_id {site_id}")
        return []
    
    # Compute cosine similarities
    past_vectors_array = np.array(past_vectors)
    current_vector = scaled_features.reshape(1, -1)
    
    logger.debug(f"Computing cosine similarity: current vector shape {current_vector.shape}, past vectors shape {past_vectors_array.shape}")
    
    # Cosine similarity: 1 means identical, -1 means opposite
    similarities = cosine_similarity(current_vector, past_vectors_array)[0]
    
    # Get top K indices
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    # Return (date, similarity) pairs
    results = [(past_dates[i], float(similarities[i])) for i in top_indices]
    
    logger.debug(f"Found {len(results)} similar days for site_id {site_id}. Similarity scores: {[f'{s:.4f}' for _, s in results]}")
    return results


def reconstruct_forecast_from_unscaled_features(
    unscaled_features: np.ndarray,
    references: Tuple[Tuple[int, int], ...] = None
) -> dict:
    """
    Reconstruct Forecast JSON format from unscaled weather features.
    
    Args:
        unscaled_features: Unscaled feature array (length = len(WEATHER_FEATURES))
        references: Tuple of (run, delta) pairs that correspond to hours 9, 12, 15 (defaults to REFERENCES)
    
    Returns:
        Dictionary with forecast_9, forecast_12, forecast_15 in Forecast JSON format
    """
    from ..services.forecast import forecast_to_dict
    import gfs.fetch
    
    if references is None:
        references = REFERENCES
    
    # Verify feature count matches
    expected_features = len(WEATHER_FEATURES)
    if len(unscaled_features) != expected_features:
        raise ValueError(f"Expected {expected_features} features, got {len(unscaled_features)}")
    
    # Map unscaled features back to column names with hour suffixes
    # WEATHER_FEATURES structure: for each (run, delta), for each col, create f'{col}_{run+delta}'
    col_order = gfs.fetch.get_col_order()
    
    # Create a row-like structure (pandas Series) from unscaled features
    row_dict = {}
    feature_idx = 0
    for run, delta in references:
        hour = run + delta
        for col in col_order:
            feature_name = f'{col}_{hour}'
            row_dict[feature_name] = unscaled_features[feature_idx]
            feature_idx += 1
    
    # Create a pandas Series from the row_dict
    row = pd.Series(row_dict)
    
    # Use forecast_to_dict to reconstruct forecast JSON for each hour
    forecast_9 = forecast_to_dict(row, suffix='_9')
    forecast_12 = forecast_to_dict(row, suffix='_12')
    forecast_15 = forecast_to_dict(row, suffix='_15')
    
    return {
        'forecast_9': forecast_9,
        'forecast_12': forecast_12,
        'forecast_15': forecast_15
    }


async def get_past_scaled_features(
    db: AsyncSession,
    site_id: int,
    past_date: date
) -> Optional[np.ndarray]:
    """
    Get scaled features from scaled_features table for a past date.
    Returns the unscaled features after applying inverse_transform.
    
    Args:
        db: Database session
        site_id: Site ID
        past_date: Past date
    
    Returns:
        Unscaled feature array if found, None otherwise
    """
    logger.debug(f"Getting scaled features for site_id {site_id}, past_date {past_date}")
    query = select(models.ScaledFeature).where(
        models.ScaledFeature.site_id == site_id,
        models.ScaledFeature.date == past_date
    )
    result = await db.execute(query)
    scaled_feature = result.scalar_one_or_none()
    
    if not scaled_feature:
        logger.warning(f"No scaled features found for site_id {site_id}, past_date {past_date}")
        return None
    
    # Convert to numpy array and unscale
    scaled_array = np.array(scaled_feature.features, dtype=np.float32).reshape(1, -1)
    scaler = load_scaler()
    unscaled_array = scaler.inverse_transform(scaled_array)[0]
    
    logger.debug(f"Unscaled features for site_id {site_id}, past_date {past_date}. Shape: {unscaled_array.shape}")
    return unscaled_array

