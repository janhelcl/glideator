"""
Hyperparameter optimization module for site recommender models.

Provides functionality for randomized search over hyperparameter spaces,
evaluation on validation data, and analysis of results.
"""

import logging
import numpy as np
import pandas as pd
from tqdm import tqdm
from sklearn.model_selection import ParameterSampler
from scipy.stats import uniform, loguniform
import matplotlib.pyplot as plt
import seaborn as sns

# Set up logger
logger = logging.getLogger(__name__)


def get_uniform(min_val, max_val):
    """
    Transform min (lower bound) and max (upper bound) to scipy.stats.uniform parameters.
    
    Args:
        min_val: Lower bound
        max_val: Upper bound
        
    Returns:
        scipy.stats.uniform distribution
    """
    return uniform(loc=min_val, scale=max_val - min_val)


def perform_hyperparameter_search(
    model_class,
    train_data,
    val_sequences,
    train_site_vocab,
    search_space,
    fixed_params,
    n_iter=50,
    metric='hit_rate',
    k=10,
    random_state=42
):
    """
    Perform randomized hyperparameter search for recommender models.
    
    This function conducts a randomized search over a specified hyperparameter space
    for a recommender model. It evaluates each hyperparameter combination on the
    validation set and returns the results sorted by the specified metric.
    
    Parameters:
    -----------
    model_class : class
        The recommender model class (e.g., SVDRecommender)
    train_data : tuple
        Tuple of (interaction_matrix, pilot_to_idx, site_to_idx, idx_to_site, 
                  site_id_to_name, train_df)
    val_sequences : list
        List of validation walk-forward sequences
    train_site_vocab : set
        Set of sites in training data
    search_space : dict
        Dictionary specifying the hyperparameter search space. Values can be:
        - List of discrete values: [1, 2, 3]
        - scipy.stats distribution: uniform(0, 1), loguniform(0.01, 1)
    fixed_params : dict
        Dictionary of fixed parameters for the model
    n_iter : int, optional (default=50)
        Number of parameter settings to sample
    metric : str, optional (default='hit_rate')
        Metric to optimize: 'hit_rate', 'mrr', 'ndcg', 'coverage', 'avg_log_pop'
    k : int, optional (default=10)
        K value for evaluation metrics
    random_state : int, optional (default=42)
        Random seed for reproducibility
        
    Returns:
    --------
    pandas.DataFrame
        DataFrame containing the results of the hyperparameter search,
        including hyperparameters, metrics, and rankings
        
    Notes:
    ------
    - The function uses the evaluate_walk_forward function from metrics module
    - Results are sorted by the specified metric in descending order
      (except for avg_log_pop which is sorted ascending)
    """
    from metrics import evaluate_walk_forward
    
    # Unpack training data
    interaction_matrix, pilot_to_idx, site_to_idx, idx_to_site, site_id_to_name, train_df = train_data
    
    # Generate randomized hyperparameter combinations
    param_combinations = list(ParameterSampler(
        search_space, n_iter=n_iter, random_state=random_state
    ))
    
    # Prepare to store results
    results = []
    best_score = -np.inf if metric != 'avg_log_pop' else np.inf
    best_params = None
    
    logger.info(f"Starting hyperparameter search with {n_iter} iterations")
    logger.info(f"Optimizing for: {metric}@{k}")
    
    # Iterate over each hyperparameter combination
    for idx, params in enumerate(tqdm(param_combinations, desc="Hyperparameter search")):
        try:
            # Combine fixed and search parameters
            model_params = {**fixed_params, **params}
            
            # Initialize and train model
            model = model_class(**model_params)
            model.fit(interaction_matrix, pilot_to_idx, site_to_idx, 
                     idx_to_site, site_id_to_name)
            
            # Evaluate on validation set
            val_metrics = evaluate_walk_forward(
                model,
                val_sequences,
                train_site_vocab,
                train_df=train_df,
                k_values=[k],
                verbose=False
            )
            
            # Extract metrics
            hit_rate = np.mean(val_metrics['overall'][k]['hit_rate'])
            mrr = np.mean(val_metrics['overall'][k]['mrr'])
            ndcg = np.mean(val_metrics['overall'][k]['ndcg'])
            coverage = val_metrics['overall'][k].get('coverage', None)
            avg_log_pop = (np.mean(val_metrics['overall'][k]['avg_log_pop']) 
                          if val_metrics['overall'][k]['avg_log_pop'] else None)
            
            # Determine score for optimization
            if metric == 'hit_rate':
                score = hit_rate
            elif metric == 'mrr':
                score = mrr
            elif metric == 'ndcg':
                score = ndcg
            elif metric == 'coverage':
                score = coverage if coverage is not None else 0
            elif metric == 'avg_log_pop':
                score = avg_log_pop if avg_log_pop is not None else np.inf
            else:
                raise ValueError(f"Unknown metric: {metric}")
            
            # Update best score
            is_better = (score > best_score if metric != 'avg_log_pop' 
                        else score < best_score)
            if is_better:
                best_score = score
                best_params = params
            
            # Store results
            result = params.copy()
            result['hit_rate'] = hit_rate
            result['mrr'] = mrr
            result['ndcg'] = ndcg
            result['coverage'] = coverage
            result['avg_log_pop'] = avg_log_pop
            result[f'{metric}@{k}'] = score
            results.append(result)
            
            # Log progress every 10 iterations
            if (idx + 1) % 10 == 0:
                logger.info(f"Iteration {idx + 1}/{n_iter}: Best {metric}@{k} = {best_score:.4f}")
                logger.info(f"Best parameters: {best_params}")
        
        except Exception as e:
            logger.error(f"Error in iteration {idx + 1}: {e}")
            continue
    
    # Convert to DataFrame
    results_df = pd.DataFrame(results)
    
    # Sort by metric
    ascending = (metric == 'avg_log_pop')
    results_df = results_df.sort_values(by=f'{metric}@{k}', ascending=ascending)
    
    logger.info(f"\nHyperparameter search complete!")
    logger.info(f"Best {metric}@{k}: {best_score:.4f}")
    logger.info(f"Best parameters: {best_params}")
    
    return results_df


def plot_hyperparameter_analysis(results_df, param_names, metric='hit_rate', k=10,
                                 figsize=(15, 10), save_path=None):
    """
    Plot hyperparameter analysis showing metric vs each hyperparameter.
    
    Uses bar charts for categorical parameters and scatter plots for continuous ones.
    
    Args:
        results_df: DataFrame from perform_hyperparameter_search
        param_names: List of hyperparameter names to plot
        metric: Metric name to plot
        k: K value for metric
        figsize: Figure size
        save_path: Optional path to save figure
        
    Returns:
        matplotlib.figure.Figure
    """
    metric_col = f'{metric}@{k}'
    
    # Calculate grid dimensions
    n_params = len(param_names)
    n_cols = min(3, n_params)
    n_rows = (n_params + n_cols - 1) // n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    if n_params == 1:
        axes = [axes]
    else:
        axes = axes.flatten() if n_params > 1 else [axes]
    
    for idx, param_name in enumerate(param_names):
        ax = axes[idx]
        
        if param_name not in results_df.columns:
            ax.text(0.5, 0.5, f'{param_name}\nnot found',
                   ha='center', va='center', transform=ax.transAxes)
            ax.axis('off')
            continue
        
        # Determine if parameter is categorical or continuous
        unique_values = results_df[param_name].nunique()
        param_values = results_df[param_name].values
        
        # Consider categorical if: boolean, few unique values, or all values are integers
        is_categorical = (
            unique_values <= 5 or 
            results_df[param_name].dtype == bool or
            all(isinstance(v, (bool, str)) for v in param_values if pd.notna(v))
        )
        
        if is_categorical:
            # Bar chart for categorical parameters
            # Group by parameter value and compute mean and std
            grouped = results_df.groupby(param_name)[metric_col].agg(['mean', 'std', 'count'])
            grouped = grouped.sort_values('mean', ascending=False)
            
            x_pos = np.arange(len(grouped))
            means = grouped['mean'].values
            stds = grouped['std'].fillna(0).values
            counts = grouped['count'].values
            
            bars = ax.bar(x_pos, means, yerr=stds, capsize=5, alpha=0.7, color='steelblue')
            
            # Add count labels on bars
            for i, (bar, count) in enumerate(zip(bars, counts)):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'n={int(count)}',
                       ha='center', va='bottom', fontsize=9)
            
            ax.set_xticks(x_pos)
            ax.set_xticklabels([str(x) for x in grouped.index], rotation=45, ha='right')
            ax.set_ylabel(f'{metric}@{k}')
            ax.set_xlabel(param_name)
            ax.set_title(f'{metric}@{k} by {param_name}')
            ax.grid(True, alpha=0.3, axis='y')
            
        else:
            # Scatter plot for continuous parameters
            x = results_df[param_name]
            y = results_df[metric_col]
            
            # Simple scatter without color coding
            ax.scatter(x, y, alpha=0.5, s=50, color='steelblue', edgecolors='black', linewidth=0.5)
            
            # Add trend line
            try:
                z = np.polyfit(x, y, 2)  # Quadratic fit
                p = np.poly1d(z)
                x_trend = np.linspace(x.min(), x.max(), 100)
                ax.plot(x_trend, p(x_trend), "r--", alpha=0.7, linewidth=2, label='Trend')
                ax.legend()
            except:
                pass  # Skip trend line if fitting fails
            
            ax.set_xlabel(param_name)
            ax.set_ylabel(f'{metric}@{k}')
            ax.set_title(f'{metric}@{k} vs {param_name}')
            ax.grid(True, alpha=0.3)
            
            # Add statistics text
            corr = np.corrcoef(x, y)[0, 1]
            ax.text(0.05, 0.95, f'corr: {corr:.3f}', 
                   transform=ax.transAxes, fontsize=9,
                   verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Hide unused subplots
    for idx in range(n_params, len(axes)):
        axes[idx].axis('off')
    
    plt.suptitle(f'{metric.upper()}@{k} vs Hyperparameters', fontsize=14)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Plot saved to '{save_path}'")
    
    return fig


def plot_metric_correlations(results_df, metrics=['hit_rate', 'mrr', 'ndcg', 'coverage'],
                            figsize=(10, 8), save_path=None):
    """
    Plot correlation matrix between different metrics.
    
    Args:
        results_df: DataFrame from perform_hyperparameter_search
        metrics: List of metrics to include
        figsize: Figure size
        save_path: Optional path to save figure
        
    Returns:
        matplotlib.figure.Figure
    """
    # Extract metric columns (those that exist in results_df)
    metric_cols = [col for col in results_df.columns 
                   if any(m in col for m in metrics)]
    
    if not metric_cols:
        logger.warning("No metric columns found in results")
        return None
    
    # Compute correlation matrix
    corr_matrix = results_df[metric_cols].corr()
    
    # Plot
    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(corr_matrix, annot=True, fmt='.3f', cmap='coolwarm',
               center=0, square=True, ax=ax, cbar_kws={'shrink': 0.8})
    ax.set_title('Metric Correlations', fontsize=14)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Plot saved to '{save_path}'")
    
    return fig


def get_best_params(results_df, metric='hit_rate', k=10, top_n=5):
    """
    Get top N parameter sets by specified metric.
    
    Args:
        results_df: DataFrame from perform_hyperparameter_search
        metric: Metric to sort by
        k: K value for metric
        top_n: Number of top results to return
        
    Returns:
        DataFrame with top N results
    """
    metric_col = f'{metric}@{k}'
    ascending = (metric == 'avg_log_pop')
    
    top_results = results_df.sort_values(by=metric_col, ascending=ascending).head(top_n)
    
    logger.info(f"\nTop {top_n} parameter sets by {metric}@{k}:")
    for idx, row in enumerate(top_results.itertuples(), 1):
        logger.info(f"{idx}. {metric}@{k} = {getattr(row, metric_col.replace('@', '_')):.4f}")
        param_str = ", ".join([f"{col}={getattr(row, col)}" 
                              for col in results_df.columns 
                              if col not in ['hit_rate', 'mrr', 'ndcg', 'coverage', 
                                            'avg_log_pop'] and '@' not in col])
        logger.info(f"   {param_str}")
    
    return top_results


def compare_param_distributions(results_df, param_name, metric='hit_rate', k=10,
                                bins=10, figsize=(10, 6), save_path=None):
    """
    Compare distribution of a parameter in top vs bottom performers.
    
    Args:
        results_df: DataFrame from perform_hyperparameter_search
        param_name: Name of parameter to analyze
        metric: Metric for ranking
        k: K value for metric
        bins: Number of bins for histogram
        figsize: Figure size
        save_path: Optional path to save figure
        
    Returns:
        matplotlib.figure.Figure
    """
    metric_col = f'{metric}@{k}'
    
    # Split into top and bottom performers
    n_total = len(results_df)
    n_split = n_total // 4  # Top/bottom 25%
    
    ascending = (metric == 'avg_log_pop')
    sorted_df = results_df.sort_values(by=metric_col, ascending=ascending)
    
    top_performers = sorted_df.head(n_split)[param_name]
    bottom_performers = sorted_df.tail(n_split)[param_name]
    
    # Plot
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    
    # Histogram comparison
    axes[0].hist(top_performers, bins=bins, alpha=0.6, label='Top 25%', color='green')
    axes[0].hist(bottom_performers, bins=bins, alpha=0.6, label='Bottom 25%', color='red')
    axes[0].set_xlabel(param_name)
    axes[0].set_ylabel('Frequency')
    axes[0].set_title(f'Distribution of {param_name}')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Box plot comparison
    axes[1].boxplot([top_performers, bottom_performers],
                    labels=['Top 25%', 'Bottom 25%'])
    axes[1].set_ylabel(param_name)
    axes[1].set_title(f'{param_name} Distribution')
    axes[1].grid(True, alpha=0.3)
    
    plt.suptitle(f'{param_name} Analysis (by {metric}@{k})', fontsize=14)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Plot saved to '{save_path}'")
    
    return fig

