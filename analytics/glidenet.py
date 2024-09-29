import numpy as np
import torch
import torch.nn as nn
from torchrec.modules.crossnet import CrossNet

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
    df['weekend'] = df[date_col].apply(lambda date: date.weekday() >= 5).astype(int)
    df['year'] = df[date_col].apply(lambda date: date.year)
    day_of_year = df[date_col].apply(lambda date: date.timetuple().tm_yday)
    df['day_of_year_sin'] = np.sin(2 * np.pi * day_of_year / 365.25)
    df['day_of_year_cos'] = np.cos(2 * np.pi * day_of_year / 365.25)
    return df


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
    for threshold in thresholds:
        df[f'XC{threshold}'] = df[max_points_col].apply(lambda x: 1 if x > threshold else 0)
    return df


class GlideatorNet(nn.Module):
    def __init__(self, input_dim, num_launches, launch_embedding_dim, num_targets=3, deep_hidden_units=[64, 32], cross_layers=2):
        super(GlideatorNet, self).__init__()
        
        # Launch Embedding Layer: Map launch names (categorical) to vectors
        self.launch_embedding = nn.Embedding(num_embeddings=num_launches, embedding_dim=launch_embedding_dim)
        
        # Cross Network: Cross layers to capture feature interactions
        self.cross_net = CrossNet(in_features=input_dim + launch_embedding_dim, num_layers=cross_layers)
        
        # Deep Network: Multi-Layer Perceptron (MLP)
        deep_layers = []
        prev_units = input_dim + launch_embedding_dim  # input dim + launch embedding dim
        for hidden_units in deep_hidden_units:
            deep_layers.append(nn.Linear(prev_units, hidden_units))
            deep_layers.append(nn.ReLU())
            prev_units = hidden_units
        
        self.deep_net = nn.Sequential(*deep_layers)
        
        # Output Layers: One for each target (shared backbone, multiple heads)
        final_dim = deep_hidden_units[-1] + input_dim + launch_embedding_dim  # Deep + Cross output concatenation
        self.output_layers = nn.ModuleList([nn.Linear(final_dim, 1) for _ in range(num_targets)])

    def forward(self, features, launch_ids):
        # Get the launch embedding for each launch ID
        launch_embedded = self.launch_embedding(launch_ids)
        
        # Concatenate launch embedding with other features (e.g., weather, location)
        combined_features = torch.cat([features, launch_embedded], dim=-1)
        
        # Cross Network forward pass
        cross_out = self.cross_net(combined_features)
        
        # Deep Network forward pass
        deep_out = self.deep_net(combined_features)
        
        # Concatenate Cross and Deep outputs
        combined = torch.cat([cross_out, deep_out], dim=-1)
        
        # Output layers: Multi-target prediction (one output per target)
        outputs = [torch.sigmoid(layer(combined)) for layer in self.output_layers]
        
        # Stack the outputs to create a tensor of shape (batch_size, num_targets)
        return torch.cat(outputs, dim=-1)