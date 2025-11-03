"""
Data preprocessing module for site discovery recommender.

Focus: Pilots discovering new sites through exploration.
- Training: Unique sites visited per pilot
- Splits: By pilots (not time), each pilot in only one split
- Evaluation: Walk-forward sequences simulating progressive discovery
"""

import logging
import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix

# Set up logger
logger = logging.getLogger(__name__)


def load_flight_data(engine, query=None):
    """
    Load flight data from database.
    
    Joins fact_flights with dim_sites to get site_id and display name.
    
    Args:
        engine: SQLAlchemy database engine
        query: Optional custom SQL query. If None, uses default query.
        
    Returns:
        DataFrame with columns: pilot, site_id, site_name, date, points
    """
    if query is None:
        query = """
        SELECT 
            f.pilot,
            s.site_id,
            s.name as site_name,
            f.date,
            f.points
        FROM glideator_mart.fact_flights f
        INNER JOIN glideator_mart.dim_sites s
            ON f.site = s.xc_name
        WHERE f.site IS NOT NULL 
            AND f.pilot IS NOT NULL
            AND s.site_id IS NOT NULL
        ORDER BY f.date
        """
    
    logger.info("Loading flight data...")
    df = pd.read_sql(query, engine)
    logger.info(f"Loaded {len(df):,} flights")
    logger.info(f"Unique pilots: {df['pilot'].nunique():,}")
    logger.info(f"Unique sites: {df['site_id'].nunique():,}")
    logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
    
    return df


def get_first_visits(df):
    """
    Get first visit to each site for each pilot.
    
    Args:
        df: DataFrame with columns: pilot, site_id, site_name, date
        
    Returns:
        DataFrame with first visit only per pilot-site combination,
        sorted by pilot and date
    """
    # Get first visit for each pilot-site combination
    first_visits = df.sort_values('date').groupby(['pilot', 'site_id']).first().reset_index()
    
    # Sort by pilot and date to get chronological order of discovery
    first_visits = first_visits.sort_values(['pilot', 'date'])
    
    logger.info(f"First visits: {len(first_visits):,}")
    logger.info(f"Pilots with visits: {first_visits['pilot'].nunique():,}")
    logger.info(f"Unique sites visited: {first_visits['site_id'].nunique():,}")
    
    return first_visits


def filter_pilots_and_sites(first_visits_df, min_sites_per_pilot=3, min_pilots_per_site=5):
    """
    Filter to active pilots and sites.
    
    Args:
        first_visits_df: DataFrame with first visits
        min_sites_per_pilot: Minimum number of unique sites per pilot
        min_pilots_per_site: Minimum number of pilots who visited the site
        
    Returns:
        Filtered DataFrame
    """
    # Count unique sites per pilot
    pilot_site_counts = first_visits_df.groupby('pilot')['site_id'].nunique()
    active_pilots = pilot_site_counts[pilot_site_counts >= min_sites_per_pilot].index
    
    # Count pilots per site
    site_pilot_counts = first_visits_df.groupby('site_id')['pilot'].nunique()
    active_sites = site_pilot_counts[site_pilot_counts >= min_pilots_per_site].index
    
    # Filter
    filtered_df = first_visits_df[
        first_visits_df['pilot'].isin(active_pilots) & 
        first_visits_df['site_id'].isin(active_sites)
    ].copy()
    
    logger.info(f"After filtering:")
    logger.info(f"  Pilots: {filtered_df['pilot'].nunique():,} (visited {min_sites_per_pilot}+ sites)")
    logger.info(f"  Sites: {filtered_df['site_id'].nunique():,} (visited by {min_pilots_per_site}+ pilots)")
    logger.info(f"  First visits: {len(filtered_df):,}")
    
    # Show distribution
    sites_per_pilot = filtered_df.groupby('pilot')['site_id'].nunique()
    logger.info(f"  Sites per pilot - mean: {sites_per_pilot.mean():.1f}, median: {sites_per_pilot.median():.0f}, "
                f"max: {sites_per_pilot.max()}")
    
    return filtered_df


def split_pilots(first_visits_df, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, 
                 random_seed=42):
    """
    Split pilots into train/val/test sets.
    Each pilot appears in exactly one split.
    
    Args:
        first_visits_df: DataFrame with first visits
        train_ratio: Proportion of pilots for training
        val_ratio: Proportion of pilots for validation
        test_ratio: Proportion of pilots for testing
        random_seed: Random seed for reproducibility
        
    Returns:
        tuple: (train_df, val_df, test_df)
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, \
        "Ratios must sum to 1.0"
    
    # Get unique pilots
    pilots = first_visits_df['pilot'].unique()
    n_pilots = len(pilots)
    
    # Shuffle pilots
    np.random.seed(random_seed)
    shuffled_pilots = np.random.permutation(pilots)
    
    # Split pilots
    n_train = int(n_pilots * train_ratio)
    n_val = int(n_pilots * val_ratio)
    
    train_pilots = shuffled_pilots[:n_train]
    val_pilots = shuffled_pilots[n_train:n_train + n_val]
    test_pilots = shuffled_pilots[n_train + n_val:]
    
    # Split data
    train_df = first_visits_df[first_visits_df['pilot'].isin(train_pilots)].copy()
    val_df = first_visits_df[first_visits_df['pilot'].isin(val_pilots)].copy()
    test_df = first_visits_df[first_visits_df['pilot'].isin(test_pilots)].copy()
    
    logger.info(f"\nPilot-based split:")
    logger.info(f"  Train: {len(train_pilots):,} pilots, {len(train_df):,} visits")
    logger.info(f"  Val:   {len(val_pilots):,} pilots, {len(val_df):,} visits")
    logger.info(f"  Test:  {len(test_pilots):,} pilots, {len(test_df):,} visits")
    
    return train_df, val_df, test_df


def create_walk_forward_sequences(first_visits_df, min_history=1):
    """
    Create walk-forward sequences for evaluation.
    
    For a pilot who visited [S1, S2, S3, S4] in chronological order:
    - [S1] -> S2
    - [S1, S2] -> S3
    - [S1, S2, S3] -> S4
    
    Args:
        first_visits_df: DataFrame with first visits (sorted by pilot, date)
        min_history: Minimum number of sites in history to create a sequence
        
    Returns:
        List of dicts with keys: pilot, history_sites, target_site, 
                                 history_names, target_name, sequence_idx
    """
    sequences = []
    
    # Group by pilot and ensure chronological order
    for pilot, group in first_visits_df.groupby('pilot'):
        group_sorted = group.sort_values('date')
        site_ids = group_sorted['site_id'].tolist()
        site_names = group_sorted['site_name'].tolist()
        
        # Create walk-forward sequences
        for i in range(min_history, len(site_ids)):
            sequences.append({
                'pilot': pilot,
                'history_sites': site_ids[:i],      # Site IDs for model
                'target_site': site_ids[i],         # Target site ID
                'history_names': site_names[:i],    # Names for display
                'target_name': site_names[i],       # Target name for display
                'sequence_idx': i                   # Position in pilot's journey
            })
    
    logger.info(f"\nCreated {len(sequences):,} walk-forward sequences")
    logger.info(f"  From {first_visits_df['pilot'].nunique():,} pilots")
    logger.info(f"  Avg sequences per pilot: {len(sequences) / first_visits_df['pilot'].nunique():.1f}")
    
    return sequences


def create_interaction_matrix(train_df):
    """
    Build pilot-site binary interaction matrix (1 if visited, 0 otherwise).
    
    Args:
        train_df: Training DataFrame with first visits
        
    Returns:
        tuple: (interaction_matrix, pilot_to_idx, site_to_idx, idx_to_site, site_id_to_name)
            - interaction_matrix: scipy sparse CSR matrix (pilots × sites), binary
            - pilot_to_idx: dict mapping pilot names to indices
            - site_to_idx: dict mapping site_id to indices
            - idx_to_site: dict mapping indices to site_id
            - site_id_to_name: dict mapping site_id to display name
    """
    # Create mappings
    pilots = sorted(train_df['pilot'].unique())
    site_ids = sorted(train_df['site_id'].unique())
    
    pilot_to_idx = {pilot: idx for idx, pilot in enumerate(pilots)}
    site_to_idx = {site_id: idx for idx, site_id in enumerate(site_ids)}
    idx_to_site = {idx: site_id for site_id, idx in site_to_idx.items()}
    
    # Create site_id to name mapping
    site_id_to_name = train_df[['site_id', 'site_name']].drop_duplicates().set_index('site_id')['site_name'].to_dict()
    
    n_pilots = len(pilot_to_idx)
    n_sites = len(site_to_idx)
    
    logger.info(f"\nInteraction matrix:")
    logger.info(f"  Shape: {n_pilots} pilots × {n_sites} sites")
    
    # Create binary interaction matrix (1 if pilot visited site, 0 otherwise)
    pilot_indices = train_df['pilot'].map(pilot_to_idx).values
    site_indices = train_df['site_id'].map(site_to_idx).values
    
    # Binary: just 1s for visited sites
    data = np.ones(len(pilot_indices))
    
    interaction_matrix = csr_matrix(
        (data, (pilot_indices, site_indices)),
        shape=(n_pilots, n_sites)
    )
    
    logger.info(f"  Density: {interaction_matrix.nnz / (n_pilots * n_sites):.6f}")
    logger.info(f"  Total interactions: {interaction_matrix.nnz:,}")
    
    return interaction_matrix, pilot_to_idx, site_to_idx, idx_to_site, site_id_to_name


def build_train_site_vocabulary(train_df):
    """
    Build vocabulary of sites that appear in training data.
    Used to filter validation/test sequences.
    
    Args:
        train_df: Training DataFrame
        
    Returns:
        set: Set of site_ids in training data
    """
    return set(train_df['site_id'].unique())
