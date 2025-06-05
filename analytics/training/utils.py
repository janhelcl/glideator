import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from sklearn.calibration import calibration_curve
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, roc_curve


def bin_degrees(df, bin_size=5, wind_direction_col='wind_direction_dgr', bin_col='wind_bin'):
    """
    Bin wind directions into discrete intervals.

    This function takes a DataFrame containing wind direction data and bins it into
    discrete intervals of a specified size.

    Args:
        df (pandas.DataFrame): The input DataFrame containing wind direction data.
        bin_size (int, optional): The size of each bin in degrees. Defaults to 5.
        wind_direction_col (str, optional): The name of the column containing wind
            direction data. Defaults to 'wind_direction_dgr'.
        bin_col (str, optional): The name of the new column to be created for the
            binned data. Defaults to 'wind_bin'.

    Returns:
        pandas.DataFrame: The input DataFrame with an additional column containing
        the binned wind direction data.

    Note:
        The function assumes that wind directions are in degrees (0-360).
        The bins are created to cover the full range from 0 to 360 degrees.
        The bins are labeled with their midpoint values.
    """
    bins = np.arange(0, 360 + bin_size, bin_size)  # Bins covering 0 to 360 degrees
    bin_labels = bins[:-1] + bin_size / 2  # Midpoints of the bins
    df[bin_col] = pd.cut(df[wind_direction_col], bins=bins, include_lowest=True, labels=bin_labels)
    return df


def polar_plot(df, bar_col, color_col=None, label=None, bin_col='wind_bin', bin_size=5, range1=None, range2=None, max_value=None):
    """
    Create a polar plot (wind rose) of wind data with optional color mapping and range indicators.

    This function generates a polar plot from binned wind direction data, with options to color-code
    the bars based on another variable and add range indicators.

    Args:
        df (pandas.DataFrame): Input DataFrame containing wind data.
        bar_col (str): Name of the column to use for bar heights.
        color_col (str, optional): Name of the column to use for color-coding the bars.
            If None, bars will be a single color. Defaults to None.
        label (str, optional): Label for the plot title. If None, no label is added. Defaults to None.
        bin_col (str, optional): Name of the column containing binned wind directions.
            Defaults to 'wind_bin'.
        bin_size (int, optional): Size of each wind direction bin in degrees. Defaults to 5.
        range1 (tuple, optional): Tuple of (start, end) degrees for the first range indicator.
            If None, no range indicator is drawn. Defaults to None.
        range2 (tuple, optional): Tuple of (start, end) degrees for the second range indicator.
            If None, no range indicator is drawn. Defaults to None.
        max_value (float, optional): Maximum value to be displayed on the radial axis.
            If None, the maximum value is determined from the data. Defaults to None.

    Returns:
        None: This function displays the plot but does not return any value.

    Note:
        - Assumes wind directions are binned and in degrees (0-360).
        - The polar plot is oriented with 0 degrees (North) at the top and proceeds clockwise.
        - If color_col is provided, a colorbar is added to show the color scale.
        - Range indicators are drawn as dashed lines with shaded areas between them.
        - The main title of the plot is set to the bar_col name, with an optional subtitle from the label parameter.
    """
    # Prepare data for the polar plot
    theta = np.deg2rad(df[bin_col].astype(float))  # Convert bin centers to radians
    bar_values = df[bar_col]
    
    # Create the polar plot
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, polar=True)
    
    # Set 0 degrees to be at the top (North) and make the direction clockwise
    ax.set_theta_zero_location('N')  # 0 degrees (North) at the top
    ax.set_theta_direction(-1)       # Clockwise direction
    
    if color_col:
        # Create custom colormap (from white to dark blue)
        colors = [(1, 1, 1), (0, 0, 0.8)]  # White to dark blue
        cmap = mcolors.LinearSegmentedColormap.from_list('custom_blue', colors)
        
        # Normalize color values for colormap
        norm = mcolors.Normalize(vmin=df[color_col].min(), vmax=df[color_col].max())
        
        # Create bars with color mapped to the color column
        bars = ax.bar(theta, bar_values, width=np.deg2rad(bin_size), bottom=0.0, color=cmap(norm(df[color_col])))
        
        # Add colorbar to show color mapping
        sm = cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, orientation="vertical", label=color_col)
    else:
        # Create bars without color mapping
        bars = ax.bar(theta, bar_values, width=np.deg2rad(bin_size), bottom=0.0)
    
    # Set the maximum value on the radial axis if specified
    if max_value is not None:
        ax.set_ylim(0, max_value)
    
    # Add line at specified ranges
    def plot_range(ax, range_values):
        if range_values is not None:
            range_low = np.deg2rad(range_values[0])  # Convert degree to radians
            ax.plot([range_low, range_low], [0, ax.get_ylim()[1]], color='black', linewidth=2, linestyle='--')
            range_high = np.deg2rad(range_values[1])  # Convert degree to radians
            ax.plot([range_high, range_high], [0, ax.get_ylim()[1]], color='black', linewidth=2, linestyle='--')
            if range_low > range_high:
                theta = np.linspace(range_low, 2*np.pi, 100)
                theta = np.concatenate([theta, np.linspace(0, range_high, 100)])
            else:
                theta = np.linspace(range_low, range_high, 100)
            r = np.full_like(theta, ax.get_ylim()[1])
            ax.fill_between(theta, 0, r, alpha=0.2, color='gray')

    plot_range(ax, range1)
    plot_range(ax, range2)

    # Set the title to the bar column name
    plt.title(bar_col)
    plt.suptitle(label)

    plt.show()


def area_under_darl(darl, env_lapse_rate, height):
    """
    Calculate the area under the Darl curve and above the environmental lapse rate.

    This function calculates the area under the Darl curve (darl) and above the environmental lapse rate (env_lapse_rate)
    for a given height (height). The Darl curve is the difference between the actual lapse rate and the environmental lapse rate.

    Args:
        darl (numpy.ndarray): Array of Darl values.
        env_lapse_rate (numpy.ndarray): Array of environmental lapse rate values.
        height (numpy.ndarray): Array of height values.

    Returns:
        float: The area under the Darl curve and above the environmental lapse rate.
    """
    darl = np.array(darl)
    env_lapse_rate = np.array(env_lapse_rate)
    height = np.array(height)
    
    difference = darl - env_lapse_rate
    positive_difference = np.where(difference > 0, difference, 0)
    area = np.trapz(positive_difference, height)
    return area


def thermal_top(darl, env_lapse_rate, height):
    """
    Finds the height at which darl and env_lapse_rate intersect.
    
    Parameters:
    - darl: numpy array of DARL values (lapse rates)
    - env_lapse_rate: numpy array of environmental lapse rate values
    - heights: numpy array of corresponding heights

    Returns:
    - The height of the first intersection, or None if they don't intersect.
    """
    darl = np.array(darl)
    env_lapse_rate = np.array(env_lapse_rate)
    height = np.array(height)
    # Calculate the difference between the two arrays
    difference = darl - env_lapse_rate
    
    # Find where the sign of the difference changes (excluding the first point)
    for i in range(1, len(difference)):
        if difference[i-1] * difference[i] < 0:  # Sign change indicates intersection
            # Perform linear interpolation to find the exact intersection point
            # h1 and h2 are the heights, d1 and d2 are the values of difference
            h1, h2 = height[i-1], height[i]
            d1, d2 = difference[i-1], difference[i]
            
            # Linear interpolation formula
            intersect_height = h1 - d1 * (h2 - h1) / (d2 - d1)
            return intersect_height

    # If no intersection is found, return None
    return None

def plot_calibration_and_histogram(y_true, y_pred_proba, ax=None, n_bins=10):
    """
    Create a calibration plot and histogram of predicted probabilities.

    Parameters:
    -----------
    ax : matplotlib axes object
        The axes on which to plot. If None, a new figure and axes will be created.
    """
    prob_true, prob_pred = calibration_curve(y_true, y_pred_proba, n_bins=n_bins)
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))

    ax.plot([0, 1], [0, 1], linestyle='--', label='Perfectly calibrated')
    ax.plot(prob_pred, prob_true, marker='o', label='Model')
    ax.set_xlabel('Mean predicted probability')
    ax.set_ylabel('Fraction of positives')
    ax.legend(loc='lower right')

    # Create twin axis for the histogram
    ax_hist = ax.twinx()
    ax_hist.hist(y_pred_proba, bins=50, range=(0, 1), alpha=0.3, edgecolor='black')
    ax_hist.set_ylabel('Count')

    # Set the title
    ax.set_title('Calibration Plot and Histogram of Predicted Probabilities')


def plot_roc_curve(y_true, y_pred_proba, ax=None):
    """
    Calculate ROC-AUC score and plot the ROC curve.

    Parameters:
    -----------
    ax : matplotlib axes object
        The axes on which to plot. If None, a new figure and axes will be created.
    """
    roc_auc = roc_auc_score(y_true, y_pred_proba)
    fpr, tpr, _ = roc_curve(y_true, y_pred_proba)
    
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 6))

    ax.plot(fpr, tpr, label=f'ROC curve (AUC = {roc_auc:.4f})')
    ax.plot([0, 1], [0, 1], 'k--')
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.set_title('ROC Curve')
    ax.legend(loc='lower right')
    ax.set_aspect('equal')
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1])


def plot_learning_curves_per_target(train_losses_per_target, val_losses_per_target=None, labels=None):
    num_targets = len(train_losses_per_target)
    num_cols = 2
    num_rows = (num_targets + 1) // 2  # Ceiling division to ensure enough rows

    fig, axes = plt.subplots(num_rows, num_cols, figsize=(20, 8 * num_rows))
    fig.suptitle('Learning Curves per Target', fontsize=16)

    for idx, (target, train_losses) in enumerate(train_losses_per_target.items()):
        row = idx // num_cols
        col = idx % num_cols
        ax = axes[row, col] if num_rows > 1 else axes[col]

        val_losses = val_losses_per_target[target] if val_losses_per_target else None
        
        ax.plot(train_losses, label='Training Loss')
        if val_losses is not None:
            ax.plot(val_losses, label='Validation Loss')

            best_epoch = val_losses.index(min(val_losses))
            ax.axvline(x=best_epoch, color='k', linestyle='--', label='Lowest Validation Loss')

        ax.set_xlabel('Epoch')
        ax.set_ylabel('Loss')
        
        # Use labels if provided, otherwise use target index
        title = labels[idx] if labels and idx < len(labels) else f'Target {target}'
        ax.set_title(title)
        
        ax.legend()
        ax.grid(True)

    # Remove any unused subplots
    for idx in range(num_targets, num_rows * num_cols):
        row = idx // num_cols
        col = idx % num_cols
        fig.delaxes(axes[row, col] if num_rows > 1 else axes[col])

    plt.tight_layout()
    plt.show()


def scatter_wind_shap_values(shap_values, mask=None, u_wind_col='u_wind_ms', v_wind_col='v_wind_ms', label=None, ax=None):
    """
    Create a scatter plot of wind SHAP values for a specific launch site.

    This function visualizes the SHAP values for wind speed and direction
    using a scatter plot. The plot shows the relationship between U and V
    wind components, with the color of each point representing the combined
    SHAP value for both wind components.

    Parameters:
    shap_values (shap.Explanation): SHAP values for the dataset.
    mask (numpy.ndarray, optional): Boolean mask to filter the data. If None, all data is used.
    u_wind_col (str): Column name for U wind component. Default is 'u_wind_ms'.
    v_wind_col (str): Column name for V wind component. Default is 'v_wind_ms'.
    label (str, optional): Label for the launch site. If provided, it's added to the plot title.
    ax (matplotlib.axes.Axes, optional): The axes on which to draw the plot. If None, a new figure and axes will be created.

    Returns:
    matplotlib.figure.Figure: The figure containing the plot.
    """
    if mask is None:
        mask = np.ones(len(shap_values), dtype=bool)
    u_wind_ms_shap_values = shap_values[:, 'u_wind_ms'].values[mask]
    v_wind_ms_shap_values = shap_values[:, 'v_wind_ms'].values[mask]
    u_wind_ms_data = shap_values[:, 'u_wind_ms'].data[mask]
    v_wind_ms_data = shap_values[:, 'v_wind_ms'].data[mask]

    wind_shap_values = u_wind_ms_shap_values + v_wind_ms_shap_values

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    scatter = ax.scatter(v_wind_ms_data, u_wind_ms_data, c=wind_shap_values, alpha=0.5)
    ax.plot(0, 0, 'k+', markersize=10, markeredgewidth=2, zorder=10)
    title = 'SHAP values for wind speed and direction'
    if label is not None:
        title += f' ({label})'
    ax.set_title(title)
    ax.set_xlabel('V wind speed')
    ax.set_ylabel('U wind speed')
    plt.colorbar(scatter, label='SHAP value', ax=ax)
    return fig