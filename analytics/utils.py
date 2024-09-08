import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors


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


def polar_plot(df, bar_col, color_col=None, bin_col='wind_bin', bin_size=5, range1=None, range2=None):
    """
    Create a polar plot of wind data with optional color mapping and range indicators.

    This function generates a polar plot (wind rose) from binned wind direction data,
    with the option to color-code the bars based on another variable and add range indicators.

    Args:
        df (pandas.DataFrame): The input DataFrame containing wind data.
        bar_col (str): The name of the column to use for bar heights.
        color_col (str, optional): The name of the column to use for color-coding the bars.
            If None, bars will be a single color. Defaults to None.
        bin_col (str, optional): The name of the column containing binned wind directions.
            Defaults to 'wind_bin'.
        bin_size (int, optional): The size of each wind direction bin in degrees.
            Defaults to 5.
        range1 (tuple, optional): A tuple of (start, end) degrees for the first range indicator.
            If None, no range indicator is drawn. Defaults to None.
        range2 (tuple, optional): A tuple of (start, end) degrees for the second range indicator.
            If None, no range indicator is drawn. Defaults to None.

    Returns:
        None: This function displays the plot but does not return any value.

    Note:
        - The function assumes that wind directions are binned and in degrees (0-360).
        - The polar plot is oriented with 0 degrees (North) at the top and proceeds clockwise.
        - If color_col is provided, a colorbar will be added to show the color scale.
        - Range indicators are drawn as dashed lines with shaded areas between them.
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

    plt.show()