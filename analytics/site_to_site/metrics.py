"""
Evaluation metrics module for site discovery recommender.

Evaluates using walk-forward sequences that simulate progressive site discovery.
For each pilot's chronological site visits [S1, S2, S3, S4]:
- Given [S1], predict S2
- Given [S1, S2], predict S3  
- Given [S1, S2, S3], predict S4

Metrics:
- Hit Rate@K: Accuracy - is target in top-K?
- MRR: Mean Reciprocal Rank - at what position is the target?
- NDCG@K: Normalized Discounted Cumulative Gain
- Coverage@K: Diversity - what fraction of catalog is recommended?
- Avg Log-Popularity@K: Popularity bias - how popular are recommendations?
"""

import logging
import numpy as np
from tqdm import tqdm

# Set up logger
logger = logging.getLogger(__name__)


def hit_rate_at_k(recommendations, target, k):
    """
    Check if target is in top-k recommendations.
    
    Args:
        recommendations: List of (site_id, site_name, score) tuples
        target: Target site_id
        k: Number of top recommendations to consider
        
    Returns:
        1.0 if target in top-k, 0.0 otherwise
    """
    if recommendations is None or len(recommendations) == 0:
        return 0.0
    top_k = [site_id for site_id, _, _ in recommendations[:k]]
    return 1.0 if target in top_k else 0.0


def reciprocal_rank(recommendations, target):
    """
    Calculate reciprocal rank of target in recommendations.
    
    Args:
        recommendations: List of (site_id, site_name, score) tuples
        target: Target site_id
        
    Returns:
        1/rank if target found, 0.0 otherwise
    """
    if recommendations is None or len(recommendations) == 0:
        return 0.0
    for rank, (site_id, _, _) in enumerate(recommendations, 1):
        if site_id == target:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(recommendations, target, k):
    """
    Calculate NDCG@K for binary relevance.
    
    Args:
        recommendations: List of (site_id, site_name, score) tuples
        target: Target site_id
        k: Number of top recommendations to consider
        
    Returns:
        NDCG@K score
    """
    if recommendations is None or len(recommendations) == 0:
        return 0.0
    for rank, (site_id, _, _) in enumerate(recommendations[:k], 1):
        if site_id == target:
            return 1.0 / np.log2(rank + 1)
    return 0.0


def compute_site_popularity(train_df):
    """
    Compute popularity (visit count) for each site in training data.
    
    Args:
        train_df: DataFrame with 'pilot' and 'site_id' columns
        
    Returns:
        dict: Mapping from site_id to number of unique pilots who visited it
    """
    # Count unique pilots per site
    site_popularity = train_df.groupby('site_id')['pilot'].nunique().to_dict()
    return site_popularity


def catalog_coverage_at_k(all_recommendations_k, catalog_size):
    """
    Calculate what fraction of the catalog appears in recommendations.
    
    Coverage@K measures diversity: higher values mean more items are recommended.
    
    Args:
        all_recommendations_k: Set of all unique site_ids recommended at k
        catalog_size: Total number of sites in the catalog (training set)
        
    Returns:
        Coverage@K: float between 0 and 1
    """
    if catalog_size == 0:
        return 0.0
    return len(all_recommendations_k) / catalog_size


def avg_log_popularity_at_k(recommendations, k, site_popularity):
    """
    Calculate average log-popularity of top-K recommendations.
    
    Measures popularity bias: lower values mean more niche/long-tail items.
    
    Args:
        recommendations: List of (site_id, site_name, score) tuples
        k: Number of top recommendations to consider
        site_popularity: Dict mapping site_id to popularity (visit count)
        
    Returns:
        Average log-popularity of top-K items (None if no valid recommendations)
    """
    if recommendations is None or len(recommendations) == 0:
        return None
    
    log_pops = []
    for site_id, _, _ in recommendations[:k]:
        pop = site_popularity.get(site_id, 1)  # Default to 1 if not found
        log_pops.append(np.log(pop))
    
    return np.mean(log_pops) if log_pops else None


def evaluate_walk_forward(model, sequences, train_site_vocab, train_df=None, 
                          k_values=[5, 10, 20], verbose=True):
    """
    Evaluate model using walk-forward sequences.
    
    For each sequence [history_sites] -> target_site:
    - Get recommendations based on history
    - Check if target appears in top-K
    - Calculate ranking metrics
    - Track coverage and popularity bias
    
    Args:
        model: Recommender model with get_recommendations(history_sites, top_k) method
        sequences: List of dicts with keys: pilot, history_sites, target_site, sequence_idx
        train_site_vocab: Set of sites in training data (to filter valid sequences)
        train_df: DataFrame with 'pilot' and 'site_id' columns for computing popularity
                  (optional, required for coverage and avg_log_pop metrics)
        k_values: List of K values to evaluate
        verbose: Whether to print progress
        
    Returns:
        Dict with structure: {
            'overall': {k: {'hit_rate': [], 'mrr': [], 'ndcg': [], 
                           'avg_log_pop': [], 'coverage': float}},
            'by_position': {position: {k: {'hit_rate': [], 'mrr': [], 'ndcg': [], 
                                          'avg_log_pop': []}}}
        }
    """
    # Compute site popularity if train_df provided
    site_popularity = None
    catalog_size = len(train_site_vocab)
    if train_df is not None:
        site_popularity = compute_site_popularity(train_df)
        if verbose:
            logger.info(f"Computed popularity for {len(site_popularity)} sites")
    
    # Initialize metrics
    metrics = {
        'overall': {k: {'hit_rate': [], 'mrr': [], 'ndcg': [], 'avg_log_pop': []} 
                   for k in k_values}
    }
    
    # Track all recommended sites for coverage
    recommended_sites = {k: set() for k in k_values}
    
    # Also track by sequence position (how many sites in history)
    by_position = {}
    
    # Filter sequences to only include those where:
    # 1. All history sites are in training vocab
    # 2. Target site is in training vocab
    valid_sequences = []
    for seq in sequences:
        history_sites = seq['history_sites']
        target_site = seq['target_site']
        
        if (target_site in train_site_vocab and 
            all(s in train_site_vocab for s in history_sites)):
            valid_sequences.append(seq)
    
    if verbose:
        logger.info(f"Evaluating {len(valid_sequences):,} valid sequences (out of {len(sequences):,})")
    
    # Evaluate each sequence
    iterator = tqdm(valid_sequences) if verbose else valid_sequences
    for seq in iterator:
        history_sites = seq['history_sites']
        target_site = seq['target_site']
        position = seq['sequence_idx']  # How many sites in history
        
        # Get recommendations based on history
        recommendations = model.get_recommendations(history_sites, top_k=max(k_values))
        
        if recommendations is None:
            continue
        
        # Calculate metrics for each K
        for k in k_values:
            hit = hit_rate_at_k(recommendations, target_site, k)
            ndcg = ndcg_at_k(recommendations, target_site, k)
            
            metrics['overall'][k]['hit_rate'].append(hit)
            metrics['overall'][k]['ndcg'].append(ndcg)
            
            # Track recommended sites for coverage
            top_k_sites = [site_id for site_id, _, _ in recommendations[:k]]
            recommended_sites[k].update(top_k_sites)
            
            # Calculate avg log-popularity if site_popularity available
            if site_popularity is not None:
                avg_log_pop = avg_log_popularity_at_k(recommendations, k, site_popularity)
                if avg_log_pop is not None:
                    metrics['overall'][k]['avg_log_pop'].append(avg_log_pop)
            
            # Track by position
            if position not in by_position:
                by_position[position] = {kv: {'hit_rate': [], 'mrr': [], 'ndcg': [], 'avg_log_pop': []} 
                                        for kv in k_values}
            by_position[position][k]['hit_rate'].append(hit)
            by_position[position][k]['ndcg'].append(ndcg)
            
            # Track avg_log_pop by position
            if site_popularity is not None and avg_log_pop is not None:
                by_position[position][k]['avg_log_pop'].append(avg_log_pop)
        
        # MRR is independent of k
        mrr = reciprocal_rank(recommendations, target_site)
        for k in k_values:
            metrics['overall'][k]['mrr'].append(mrr)
            by_position[position][k]['mrr'].append(mrr)
    
    # Add by_position to metrics
    metrics['by_position'] = by_position
    
    # Compute coverage for each K
    for k in k_values:
        coverage = catalog_coverage_at_k(recommended_sites[k], catalog_size)
        metrics['overall'][k]['coverage'] = coverage
    
    # Print results
    if verbose:
        logger.info("\n" + "="*60)
        logger.info("Walk-Forward Evaluation Results")
        logger.info("="*60)
        for k in k_values:
            logger.info(f"\nMetrics @ K={k}:")
            logger.info(f"  Hit Rate@{k}:  {np.mean(metrics['overall'][k]['hit_rate']):.4f}")
            logger.info(f"  MRR:           {np.mean(metrics['overall'][k]['mrr']):.4f}")
            logger.info(f"  NDCG@{k}:      {np.mean(metrics['overall'][k]['ndcg']):.4f}")
            
            # Show coverage and avg_log_pop if available
            if 'coverage' in metrics['overall'][k]:
                coverage = metrics['overall'][k]['coverage']
                logger.info(f"  Coverage@{k}:  {coverage:.4f} ({len(recommended_sites[k])}/{catalog_size} sites)")
            
            if metrics['overall'][k]['avg_log_pop']:
                avg_log_pop = np.mean(metrics['overall'][k]['avg_log_pop'])
                logger.info(f"  Avg Log-Pop@{k}: {avg_log_pop:.4f}")
        
        # Show metrics by position (history length)
        logger.info("\n" + "="*60)
        logger.info("Performance by History Length (K=10):")
        logger.info("="*60)
        positions = sorted(by_position.keys())[:10]  # Show first 10 positions
        for pos in positions:
            n_samples = len(by_position[pos][10]['hit_rate'])
            hit_rate = np.mean(by_position[pos][10]['hit_rate'])
            logger.info(f"  History size {pos}: Hit Rate@10 = {hit_rate:.4f} ({n_samples} sequences)")
    
    return metrics


def print_metrics_summary(metrics, k_values=[5, 10, 20]):
    """
    Print summary of evaluation metrics.
    
    Args:
        metrics: Metrics dict from evaluate_walk_forward
        k_values: List of K values to display
    """
    logger.info("\n" + "="*60)
    logger.info("Evaluation Summary")
    logger.info("="*60)
    
    for k in k_values:
        n_samples = len(metrics['overall'][k]['hit_rate'])
        logger.info(f"\nMetrics @ K={k} ({n_samples} sequences):")
        logger.info(f"  Hit Rate@{k}:  {np.mean(metrics['overall'][k]['hit_rate']):.4f}")
        logger.info(f"  MRR:           {np.mean(metrics['overall'][k]['mrr']):.4f}")
        logger.info(f"  NDCG@{k}:      {np.mean(metrics['overall'][k]['ndcg']):.4f}")
        
        # Show coverage and avg_log_pop if available
        if 'coverage' in metrics['overall'][k]:
            logger.info(f"  Coverage@{k}:  {metrics['overall'][k]['coverage']:.4f}")
        
        if metrics['overall'][k]['avg_log_pop']:
            avg_log_pop = np.mean(metrics['overall'][k]['avg_log_pop'])
            logger.info(f"  Avg Log-Pop@{k}: {avg_log_pop:.4f}")


def aggregate_metrics(metrics):
    """
    Aggregate metrics to mean values for saving/comparison.
    
    Args:
        metrics: Metrics dict from evaluate_walk_forward
        
    Returns:
        Dict with mean values for each metric
    """
    aggregated = {}
    
    # Overall metrics
    aggregated['overall'] = {}
    for k in metrics['overall'].keys():
        agg_k = {
            'hit_rate': np.mean(metrics['overall'][k]['hit_rate']),
            'mrr': np.mean(metrics['overall'][k]['mrr']),
            'ndcg': np.mean(metrics['overall'][k]['ndcg']),
            'n_samples': len(metrics['overall'][k]['hit_rate'])
        }
        
        # Add coverage if present
        if 'coverage' in metrics['overall'][k]:
            agg_k['coverage'] = metrics['overall'][k]['coverage']
        
        # Add avg_log_pop if present
        if metrics['overall'][k]['avg_log_pop']:
            agg_k['avg_log_pop'] = np.mean(metrics['overall'][k]['avg_log_pop'])
        
        aggregated['overall'][k] = agg_k
    
    # By position metrics
    aggregated['by_position'] = {}
    for pos, pos_metrics in metrics['by_position'].items():
        aggregated['by_position'][pos] = {}
        for k in pos_metrics.keys():
            agg_k = {
                'hit_rate': np.mean(pos_metrics[k]['hit_rate']),
                'mrr': np.mean(pos_metrics[k]['mrr']),
                'ndcg': np.mean(pos_metrics[k]['ndcg']),
                'n_samples': len(pos_metrics[k]['hit_rate'])
            }
            
            # Add avg_log_pop if present
            if pos_metrics[k]['avg_log_pop']:
                agg_k['avg_log_pop'] = np.mean(pos_metrics[k]['avg_log_pop'])
            
            aggregated['by_position'][pos][k] = agg_k
    
    return aggregated
