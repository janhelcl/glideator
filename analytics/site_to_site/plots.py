"""
Visualization module for site discovery recommender.

Provides reusable plotting functions for evaluation results.
"""

import logging
import numpy as np
import matplotlib.pyplot as plt

# Set up logger
logger = logging.getLogger(__name__)


def plot_metrics_comparison(metrics_dict, k_values=[5, 10, 20], 
                            figsize=(20, 4), save_path=None, include_diversity=True):
    """
    Plot comparison of metrics across different evaluation sets or models.
    
    Args:
        metrics_dict: Dict with structure {label: metrics} where metrics has
                     structure {k: {'hit_rate': [], 'mrr': [], 'ndcg': [], 
                                    'coverage': float, 'avg_log_pop': []}}
        k_values: List of K values to plot
        figsize: Figure size tuple (width, height)
        save_path: Optional path to save figure
        include_diversity: Whether to include Coverage and Avg Log-Pop plots
        
    Returns:
        matplotlib.figure.Figure
    """
    # Check if diversity metrics are available
    first_label = list(metrics_dict.keys())[0]
    first_k = k_values[0]
    has_coverage = 'coverage' in metrics_dict[first_label]['overall'][first_k]
    has_log_pop = (metrics_dict[first_label]['overall'][first_k].get('avg_log_pop') and 
                   len(metrics_dict[first_label]['overall'][first_k]['avg_log_pop']) > 0)
    
    # Determine which metrics to plot
    metric_names = ['hit_rate', 'mrr', 'ndcg']
    titles = ['Hit Rate@K', 'MRR', 'NDCG@K']
    
    if include_diversity and has_coverage:
        metric_names.append('coverage')
        titles.append('Coverage@K')
    
    if include_diversity and has_log_pop:
        metric_names.append('avg_log_pop')
        titles.append('Avg Log-Popularity@K')
    
    n_metrics = len(metric_names)
    fig, axes = plt.subplots(1, n_metrics, figsize=figsize)
    if n_metrics == 1:
        axes = [axes]
    
    # Get labels and colors
    labels = list(metrics_dict.keys())
    colors = plt.cm.Set2(range(len(labels)))
    
    for idx, (metric_name, title) in enumerate(zip(metric_names, titles)):
        x = np.arange(len(k_values))
        width = 0.8 / len(labels)  # Divide bar width by number of groups
        
        # Plot each group
        for i, (label, color) in enumerate(zip(labels, colors)):
            if metric_name == 'coverage':
                # Coverage is a single value per K, not a list
                values = [metrics_dict[label]['overall'][k][metric_name] for k in k_values]
            elif metric_name == 'avg_log_pop':
                # Avg log-pop might be a list, take mean
                values = [np.mean(metrics_dict[label]['overall'][k][metric_name]) 
                         if metrics_dict[label]['overall'][k][metric_name] else 0
                         for k in k_values]
            else:
                values = [np.mean(metrics_dict[label]['overall'][k][metric_name]) 
                         for k in k_values]
            offset = width * (i - len(labels) / 2 + 0.5)
            axes[idx].bar(x + offset, values, width, label=label, color=color)
        
        axes[idx].set_xlabel('K')
        axes[idx].set_ylabel('Score')
        axes[idx].set_title(title)
        axes[idx].set_xticks(x)
        axes[idx].set_xticklabels([str(k) for k in k_values])
        axes[idx].legend()
        
        # Set y-axis limit
        all_values = []
        for label in labels:
            if metric_name == 'coverage':
                all_values.extend([metrics_dict[label]['overall'][k][metric_name] for k in k_values])
            elif metric_name == 'avg_log_pop':
                all_values.extend([np.mean(metrics_dict[label]['overall'][k][metric_name])
                                  if metrics_dict[label]['overall'][k][metric_name] else 0
                                  for k in k_values])
            else:
                all_values.extend([np.mean(metrics_dict[label]['overall'][k][metric_name]) 
                                  for k in k_values])
        if all_values:
            axes[idx].set_ylim([0, max(all_values) * 1.2])
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Plot saved to '{save_path}'")
    
    return fig


def plot_performance_by_history_length(metrics, k=10, max_positions=10,
                                       figsize=(10, 5), save_path=None,
                                       title=None):
    """
    Plot performance as a function of history length.
    
    Args:
        metrics: Metrics dict with 'by_position' containing position-level metrics
        k: K value to plot (default 10)
        max_positions: Maximum number of positions to show
        figsize: Figure size tuple (width, height)
        save_path: Optional path to save figure
        title: Optional custom title
        
    Returns:
        matplotlib.figure.Figure
    """
    positions = sorted(metrics['by_position'].keys())[:max_positions]
    hit_rates = [np.mean(metrics['by_position'][pos][k]['hit_rate']) 
                for pos in positions]
    n_samples = [len(metrics['by_position'][pos][k]['hit_rate']) 
                for pos in positions]
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Plot line with markers
    ax.plot(positions, hit_rates, marker='o', linewidth=2, markersize=8, 
           color='steelblue', label=f'Hit Rate@{k}')
    
    # Add sample counts as annotations
    for pos, rate, n in zip(positions, hit_rates, n_samples):
        ax.annotate(f'n={n}', xy=(pos, rate), xytext=(0, 10),
                   textcoords='offset points', ha='center', fontsize=8,
                   alpha=0.7)
    
    ax.set_xlabel('History Length (number of previously visited sites)')
    ax.set_ylabel(f'Hit Rate@{k}')
    ax.set_title(title or f'Performance by History Length')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Plot saved to '{save_path}'")
    
    return fig


def plot_multiple_models_by_history(models_metrics, k=10, max_positions=10,
                                    figsize=(12, 6), save_path=None):
    """
    Plot performance by history length for multiple models.
    
    Args:
        models_metrics: Dict with structure {model_name: metrics}
        k: K value to plot
        max_positions: Maximum number of positions to show
        figsize: Figure size tuple (width, height)
        save_path: Optional path to save figure
        
    Returns:
        matplotlib.figure.Figure
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    colors = plt.cm.Set2(range(len(models_metrics)))
    
    for (model_name, metrics), color in zip(models_metrics.items(), colors):
        positions = sorted(metrics['by_position'].keys())[:max_positions]
        hit_rates = [np.mean(metrics['by_position'][pos][k]['hit_rate']) 
                    for pos in positions]
        
        ax.plot(positions, hit_rates, marker='o', linewidth=2, markersize=6,
               label=model_name, color=color)
    
    ax.set_xlabel('History Length (number of previously visited sites)')
    ax.set_ylabel(f'Hit Rate@{k}')
    ax.set_title(f'Model Comparison: Performance by History Length')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Plot saved to '{save_path}'")
    
    return fig


def plot_metric_heatmap(metrics, metric_name='hit_rate', max_positions=10,
                       figsize=(10, 8), save_path=None):
    """
    Plot heatmap of metric values across K and history length.
    
    Args:
        metrics: Metrics dict with 'by_position' structure
        metric_name: Which metric to plot ('hit_rate', 'mrr', or 'ndcg')
        max_positions: Maximum number of positions to show
        figsize: Figure size tuple (width, height)
        save_path: Optional path to save figure
        
    Returns:
        matplotlib.figure.Figure
    """
    positions = sorted(metrics['by_position'].keys())[:max_positions]
    
    # Get all K values
    k_values = sorted(metrics['overall'].keys())
    
    # Build heatmap data
    heatmap_data = np.zeros((len(positions), len(k_values)))
    for i, pos in enumerate(positions):
        for j, k in enumerate(k_values):
            heatmap_data[i, j] = np.mean(
                metrics['by_position'][pos][k][metric_name]
            )
    
    fig, ax = plt.subplots(figsize=figsize)
    
    im = ax.imshow(heatmap_data, cmap='YlOrRd', aspect='auto')
    
    # Set ticks
    ax.set_xticks(np.arange(len(k_values)))
    ax.set_yticks(np.arange(len(positions)))
    ax.set_xticklabels([f'K={k}' for k in k_values])
    ax.set_yticklabels([f'{pos}' for pos in positions])
    
    # Labels
    ax.set_xlabel('K Value')
    ax.set_ylabel('History Length')
    ax.set_title(f'{metric_name.replace("_", " ").title()} by K and History Length')
    
    # Colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label(metric_name.replace('_', ' ').title())
    
    # Annotate cells with values
    for i in range(len(positions)):
        for j in range(len(k_values)):
            text = ax.text(j, i, f'{heatmap_data[i, j]:.3f}',
                         ha="center", va="center", color="black", fontsize=9)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Plot saved to '{save_path}'")
    
    return fig


def plot_model_comparison_summary(models_results, k=10, metrics_to_plot=['hit_rate', 'mrr', 'ndcg'],
                                  figsize=(12, 4), save_path=None):
    """
    Plot summary comparison of multiple models on validation and test sets.
    
    Args:
        models_results: Dict with structure {model_name: {'val_metrics': ..., 'test_metrics': ...}}
        k: K value to display
        metrics_to_plot: List of metric names to plot
        figsize: Figure size tuple (width, height)
        save_path: Optional path to save figure
        
    Returns:
        matplotlib.figure.Figure
    """
    model_names = list(models_results.keys())
    n_metrics = len(metrics_to_plot)
    
    fig, axes = plt.subplots(1, n_metrics, figsize=figsize)
    if n_metrics == 1:
        axes = [axes]
    
    metric_display_names = {
        'hit_rate': f'Hit Rate@{k}',
        'mrr': 'MRR',
        'ndcg': f'NDCG@{k}'
    }
    
    for idx, metric_name in enumerate(metrics_to_plot):
        x = np.arange(len(model_names))
        width = 0.35
        
        val_values = []
        test_values = []
        
        for model_name in model_names:
            val_val = models_results[model_name]['val_metrics']['overall'][k][metric_name]
            test_val = models_results[model_name]['test_metrics']['overall'][k][metric_name]
            val_values.append(val_val)
            test_values.append(test_val)
        
        axes[idx].bar(x - width/2, val_values, width, label='Validation', color='steelblue')
        axes[idx].bar(x + width/2, test_values, width, label='Test', color='coral')
        
        axes[idx].set_ylabel('Score')
        axes[idx].set_title(metric_display_names.get(metric_name, metric_name))
        axes[idx].set_xticks(x)
        axes[idx].set_xticklabels(model_names, rotation=45, ha='right')
        axes[idx].legend()
        axes[idx].set_ylim([0, max(max(val_values), max(test_values)) * 1.2])
        
        # Add value labels on bars
        for i, (v_val, t_val) in enumerate(zip(val_values, test_values)):
            axes[idx].text(i - width/2, v_val, f'{v_val:.3f}', 
                          ha='center', va='bottom', fontsize=8)
            axes[idx].text(i + width/2, t_val, f'{t_val:.3f}', 
                          ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Plot saved to '{save_path}'")
    
    return fig


def create_results_dashboard(val_metrics, test_metrics, model_name='Model',
                            k_values=[5, 10, 20], save_path=None):
    """
    Create comprehensive dashboard with multiple visualizations.
    
    Args:
        val_metrics: Validation metrics
        test_metrics: Test metrics
        model_name: Name of the model for titles
        k_values: List of K values
        save_path: Optional path to save figure
        
    Returns:
        matplotlib.figure.Figure
    """
    # Check if diversity metrics are available
    has_coverage = 'coverage' in val_metrics['overall'][k_values[0]]
    has_log_pop = (val_metrics['overall'][k_values[0]].get('avg_log_pop') and 
                   len(val_metrics['overall'][k_values[0]]['avg_log_pop']) > 0)
    
    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(4, 3, hspace=0.3, wspace=0.3)
    
    # 1. Accuracy metrics comparison (top row)
    metric_names = ['hit_rate', 'mrr', 'ndcg']
    titles = ['Hit Rate@K', 'MRR', 'NDCG@K']
    
    for idx, (metric_name, title) in enumerate(zip(metric_names, titles)):
        ax = fig.add_subplot(gs[0, idx])
        x = np.arange(len(k_values))
        width = 0.35
        
        val_values = [np.mean(val_metrics['overall'][k][metric_name]) for k in k_values]
        test_values = [np.mean(test_metrics['overall'][k][metric_name]) for k in k_values]
        
        ax.bar(x - width/2, val_values, width, label='Validation', color='steelblue')
        ax.bar(x + width/2, test_values, width, label='Test', color='coral')
        
        ax.set_xlabel('K')
        ax.set_ylabel('Score')
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels([str(k) for k in k_values])
        ax.legend()
        ax.set_ylim([0, max(max(val_values), max(test_values)) * 1.2])
    
    # 1b. Diversity metrics (second row) if available
    row_idx = 1
    if has_coverage or has_log_pop:
        col_idx = 0
        if has_coverage:
            ax = fig.add_subplot(gs[row_idx, col_idx])
            x = np.arange(len(k_values))
            width = 0.35
            
            val_values = [val_metrics['overall'][k]['coverage'] for k in k_values]
            test_values = [test_metrics['overall'][k]['coverage'] for k in k_values]
            
            ax.bar(x - width/2, val_values, width, label='Validation', color='steelblue')
            ax.bar(x + width/2, test_values, width, label='Test', color='coral')
            
            ax.set_xlabel('K')
            ax.set_ylabel('Coverage')
            ax.set_title('Coverage@K (Catalog Diversity)')
            ax.set_xticks(x)
            ax.set_xticklabels([str(k) for k in k_values])
            ax.legend()
            ax.set_ylim([0, max(max(val_values), max(test_values)) * 1.2])
            col_idx += 1
        
        if has_log_pop:
            ax = fig.add_subplot(gs[row_idx, col_idx])
            x = np.arange(len(k_values))
            width = 0.35
            
            val_values = [np.mean(val_metrics['overall'][k]['avg_log_pop']) 
                         if val_metrics['overall'][k]['avg_log_pop'] else 0 for k in k_values]
            test_values = [np.mean(test_metrics['overall'][k]['avg_log_pop']) 
                          if test_metrics['overall'][k]['avg_log_pop'] else 0 for k in k_values]
            
            ax.bar(x - width/2, val_values, width, label='Validation', color='steelblue')
            ax.bar(x + width/2, test_values, width, label='Test', color='coral')
            
            ax.set_xlabel('K')
            ax.set_ylabel('Avg Log-Popularity')
            ax.set_title('Avg Log-Popularity@K (Lower = More Niche)')
            ax.set_xticks(x)
            ax.set_xticklabels([str(k) for k in k_values])
            ax.legend()
            if val_values and test_values:
                ax.set_ylim([0, max(max(val_values), max(test_values)) * 1.2])
        
        row_idx += 1
    
    # 2. Performance by history length (next row, spanning 2 columns)
    ax_hist = fig.add_subplot(gs[row_idx, :2])
    positions = sorted(val_metrics['by_position'].keys())[:10]
    val_hr = [np.mean(val_metrics['by_position'][pos][10]['hit_rate']) for pos in positions]
    test_hr = [np.mean(test_metrics['by_position'][pos][10]['hit_rate']) for pos in positions]
    
    ax_hist.plot(positions, val_hr, marker='o', linewidth=2, label='Validation', color='steelblue')
    ax_hist.plot(positions, test_hr, marker='s', linewidth=2, label='Test', color='coral')
    ax_hist.set_xlabel('History Length')
    ax_hist.set_ylabel('Hit Rate@10')
    ax_hist.set_title('Performance by History Length')
    ax_hist.legend()
    ax_hist.grid(True, alpha=0.3)
    
    # 3. Sample counts (same row, right)
    ax_samples = fig.add_subplot(gs[row_idx, 2])
    val_samples = [len(val_metrics['by_position'][pos][10]['hit_rate']) for pos in positions]
    test_samples = [len(test_metrics['by_position'][pos][10]['hit_rate']) for pos in positions]
    
    ax_samples.bar(positions, val_samples, alpha=0.7, label='Validation', color='steelblue')
    ax_samples.bar(positions, test_samples, alpha=0.7, label='Test', color='coral')
    ax_samples.set_xlabel('History Length')
    ax_samples.set_ylabel('Number of Sequences')
    ax_samples.set_title('Sample Counts')
    ax_samples.legend()
    
    row_idx += 1
    
    # 4. Summary statistics (bottom row)
    ax_summary = fig.add_subplot(gs[row_idx, :])
    ax_summary.axis('off')
    
    summary_text = f"{model_name} - Performance Summary\n\n"
    summary_text += "Validation Set:\n"
    for k in k_values:
        hr = np.mean(val_metrics['overall'][k]['hit_rate'])
        mrr = np.mean(val_metrics['overall'][k]['mrr'])
        ndcg = np.mean(val_metrics['overall'][k]['ndcg'])
        summary_text += f"  K={k}: HR={hr:.4f}, MRR={mrr:.4f}, NDCG={ndcg:.4f}"
        
        if has_coverage:
            cov = val_metrics['overall'][k]['coverage']
            summary_text += f", Cov={cov:.4f}"
        if has_log_pop and val_metrics['overall'][k]['avg_log_pop']:
            alp = np.mean(val_metrics['overall'][k]['avg_log_pop'])
            summary_text += f", ALP={alp:.4f}"
        summary_text += "\n"
    
    summary_text += "\nTest Set:\n"
    for k in k_values:
        hr = np.mean(test_metrics['overall'][k]['hit_rate'])
        mrr = np.mean(test_metrics['overall'][k]['mrr'])
        ndcg = np.mean(test_metrics['overall'][k]['ndcg'])
        summary_text += f"  K={k}: HR={hr:.4f}, MRR={mrr:.4f}, NDCG={ndcg:.4f}"
        
        if has_coverage:
            cov = test_metrics['overall'][k]['coverage']
            summary_text += f", Cov={cov:.4f}"
        if has_log_pop and test_metrics['overall'][k]['avg_log_pop']:
            alp = np.mean(test_metrics['overall'][k]['avg_log_pop'])
            summary_text += f", ALP={alp:.4f}"
        summary_text += "\n"
    
    ax_summary.text(0.1, 0.5, summary_text, fontsize=9, family='monospace',
                   verticalalignment='center')
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Dashboard saved to '{save_path}'")
    
    return fig

