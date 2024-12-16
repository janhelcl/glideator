import torch
import torch.nn as nn
from torchrec.modules.crossnet import CrossNet


class StandardScalerLayer(nn.Module):
    """
    A PyTorch layer that performs standardization (z-score normalization) on input features.

    This layer implements the standardization formula: z = (x - μ) / σ
    where x is the input data, μ is the mean, and σ is the standard deviation.
    The means and standard deviations are fixed parameters loaded during initialization
    and are not updated during training.

    Args:
        scaling_params (dict): Dictionary containing the scaling parameters for each feature,
            with structure {feature_name: {'mean': float, 'std': float}}

    Attributes:
        means (nn.Parameter): Tensor of mean values for each feature
        stds (nn.Parameter): Tensor of standard deviation values for each feature

    Example:
        >>> scaler_params = {'feature1': {'mean': 0.5, 'std': 1.2},
        ...                  'feature2': {'mean': -0.3, 'std': 0.8}}
        >>> scaler = StandardScalerLayer(scaler_params)
        >>> x = torch.randn(32, 2)  # batch of 32 samples, 2 features
        >>> scaled_x = scaler(x)
    """
    def __init__(self, scaling_params):
        super(StandardScalerLayer, self).__init__()
        # Register the scaling parameters as buffers (not trainable)
        self.means = nn.Parameter(torch.tensor([param['mean'] for param in scaling_params.values()], dtype=torch.float32), requires_grad=False)
        self.stds = nn.Parameter(torch.tensor([param['std'] for param in scaling_params.values()], dtype=torch.float32), requires_grad=False)

    def forward(self, x):
        """
        Standardizes the input tensor using stored means and standard deviations.

        Args:
            x (torch.Tensor): Input tensor to be standardized

        Returns:
            torch.Tensor: Standardized tensor with same shape as input
        """
        return (x - self.means) / self.stds


class GlideatorNet(nn.Module):
    """
    Neural network model for predicting gliding conditions.

    This model combines a cross network and deep network architecture with feature scaling
    and embeddings to predict multiple probability thresholds for gliding conditions.

    Args:
        weather_scaler (StandardScalerLayer): Scaler for weather features
        site_scaler (StandardScalerLayer): Scaler for site features 
        num_launches (int): Number of unique launch sites
        num_targets (int, optional): Number of probability thresholds to predict. Defaults to 11.
        deep_hidden_units (list, optional): List of hidden layer sizes for deep network. Defaults to [64, 32].
        cross_layers (int, optional): Number of cross layers. Defaults to 2.
        site_embedding_dim (int, optional): Dimension of site embeddings. Defaults to 8.

    Input Features:
        The model expects a dictionary with the following keys:
        - 'weather': Weather features tensor
        - 'site': Site features tensor 
        - 'site_id': Site ID tensor for embeddings
        - 'date': Date features tensor containing:
            - weekend indicator
            - year 
            - day of year sine
            - day of year cosine

    Architecture:
        1. Feature scaling using StandardScalerLayer
        2. Site ID embedding layer
        3. Cross network for feature interactions
        4. Deep network with configurable hidden layers
        5. Concatenation of cross and deep outputs
        6. Multiple sigmoid output heads for each probability threshold
    """
    def __init__(self, weather_scaler, site_scaler, num_launches, num_targets=11, 
                 deep_hidden_units=[64, 32], cross_layers=2, site_embedding_dim=8):
        super(GlideatorNet, self).__init__()
        
        # Scaling layers
        self.weather_scaler = weather_scaler
        self.site_scaler = site_scaler
        
        # Get input dimensions from scalers
        weather_dim = len(weather_scaler.means)
        site_dim = len(site_scaler.means)
        date_dim = 4  # weekend, year, day_of_year_sin, day_of_year_cos
        
        # Store number of targets
        self.num_targets = num_targets
        
        # Launch Embedding Layer
        self.launch_embedding = nn.Embedding(num_embeddings=num_launches, embedding_dim=site_embedding_dim)
        
        # Calculate total input dimension
        total_input_dim = weather_dim + site_dim + site_embedding_dim + date_dim
        
        # Cross Network
        self.cross_net = CrossNet(in_features=total_input_dim, num_layers=cross_layers)
        
        # Deep Network
        deep_layers = []
        prev_units = total_input_dim
        for hidden_units in deep_hidden_units:
            deep_layers.append(nn.Linear(prev_units, hidden_units))
            deep_layers.append(nn.ReLU())
            prev_units = hidden_units
        
        self.deep_net = nn.Sequential(*deep_layers)
        
        # Output Layers
        final_dim = deep_hidden_units[-1] + total_input_dim  # Deep + Cross output concatenation
        self.output_layers = nn.ModuleList([nn.Linear(final_dim, 1) for _ in range(num_targets)])

    def forward(self, features):
        """
        Forward pass of the GlideatorNet.
        
        Args:
            features (dict): Dictionary containing:
                - 'weather': Weather features tensor
                - 'site': Site features tensor
                - 'site_id': Site ID tensor
                - 'date': Date features tensor

        Returns:
            torch.Tensor: Predicted probabilities for each threshold, shape (batch_size, num_targets)
        """
        # Scale the features
        weather_scaled = self.weather_scaler(features['weather'])
        site_scaled = self.site_scaler(features['site'])
        
        # Get the launch embedding
        launch_embedded = self.launch_embedding(features['site_id'])
        
        # Normalize year by dividing by 2000
        date_features = features['date'].clone()
        date_features[:, 1] = date_features[:, 1] / 2000
        
        # Concatenate all features
        combined_features = torch.cat([
            weather_scaled,
            site_scaled,
            launch_embedded,
            date_features
        ], dim=-1)
        
        # Cross Network forward pass
        cross_out = self.cross_net(combined_features)
        
        # Deep Network forward pass
        deep_out = self.deep_net(combined_features)
        
        # Concatenate Cross and Deep outputs
        combined = torch.cat([cross_out, deep_out], dim=-1)
        
        # Output layers
        outputs = [torch.sigmoid(layer(combined)) for layer in self.output_layers]
        
        return torch.cat(outputs, dim=-1)