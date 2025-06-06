import torch
import torch.nn as nn
import torch.nn.functional as F
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


class MultilabelHead(nn.Module):
    """
    Prediction head for multilabel classification.
    Each target is predicted by an independent linear layer followed by a sigmoid.
    """
    def __init__(self, input_dim: int, num_targets: int):
        super().__init__()
        self.output_layers = nn.ModuleList([nn.Linear(input_dim, 1) for _ in range(num_targets)])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        outputs = [torch.sigmoid(layer(x)) for layer in self.output_layers]
        return torch.cat(outputs, dim=-1)


class OrdinalHead(nn.Module):
    """
    Ordinal regression head that outputs P(Y > t_k) for thresholds t_k = [0, 10, ..., 100].
    Assumes 11 thresholds → 12 ordinal bins.
    Output: (batch_size, 11) corresponding to P(Y > 0), ..., P(Y > 100).
    """
    def __init__(self, input_dim: int, num_targets: int):
        super().__init__()
        self.num_targets = num_targets
        self.num_classes = num_targets + 1  # 12 bins for 11 thresholds
        self.fc = nn.Linear(input_dim, 1)

        # Initialize thresholds using softplus deltas to guarantee order
        self.bias_base = nn.Parameter(torch.tensor(0.0))  # Make this large enough!
        self.bias_deltas = nn.Parameter(torch.ones(self.num_classes - 1))  # 11 deltas

    def get_ordered_thresholds(self):
        deltas = F.softplus(self.bias_deltas)
        return self.bias_base + torch.cumsum(deltas, dim=0)  # (11,)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        a = self.fc(x).squeeze(-1)  # (B,)
        thresholds = self.get_ordered_thresholds()  # (K = num_targets)

        logits = thresholds.unsqueeze(0) - a.unsqueeze(1)  # (B, K)
        p_gt = 1.0 - torch.sigmoid(logits)  # P(Y > t_k)

        return p_gt


class ExpandedGlideatorNet(nn.Module):
    """
    Neural network model for predicting gliding conditions using expanded time-based weather features.

    This model processes weather features for different times ('9', '12', '15') separately
    through a cross network before combining them for the deep network.

    Args:
        weather_scaler (StandardScalerLayer): Scaler for weather features (applied to each time)
        site_scaler (StandardScalerLayer): Scaler for site features 
        num_launches (int): Number of unique launch sites
        num_targets (int, optional): Number of probability thresholds to predict. Defaults to 11.
        deep_hidden_units (list, optional): List of hidden layer sizes for deep network. Defaults to [64, 32].
        cross_layers (int, optional): Number of cross layers. Defaults to 2.
        site_embedding_dim (int, optional): Dimension of site embeddings. Defaults to 8.
        prediction_head_type (str, optional): Type of prediction head. Defaults to "multilabel".
        parallel_deep_hidden_units (list | None, optional): List of hidden layer sizes for parallel deep network. Defaults to None.
        share_cross_net (bool, optional): Whether to share a single CrossNet across time slices. Defaults to True.

    Input Features:
        The model expects a dictionary with the following keys:
        - 'weather': Dictionary of weather features tensors for different times 
                     (e.g., {'9': tensor, '12': tensor, '15': tensor})
        - 'site': Site features tensor 
        - 'site_id': Site ID tensor for embeddings
        - 'date': Date features tensor containing:
            - weekend indicator
            - year 
            - day of year sine
            - day of year cosine

    Architecture:
        1. Feature scaling using StandardScalerLayer for site and each weather time.
        2. Site ID embedding layer.
        3. For each weather time ('9', '12', '15'):
            a. Concatenate scaled weather (for time), scaled site, embedded site, date features.
            b. Pass through a Cross network. This network can either be shared across all time slices or unique to each.
            c. (Optional, if parallel_deep_hidden_units is provided) Pass the same concatenated features through a parallel Deep network (shared across time slices).
            d. Concatenate the output of the Cross network and (if used) the parallel Deep network for that time slice.
        4. Concatenate the combined outputs from all three time slices.
        5. Pass the final concatenated result through a main Deep network.
        6. Use the specified prediction head (e.g., Multilabel or Ordinal) for final output.
    """
    def __init__(self, weather_scaler, site_scaler, num_launches, num_targets=11, 
                 deep_hidden_units=[64, 32], cross_layers=2, site_embedding_dim=8,
                 prediction_head_type: str = "multilabel",
                 parallel_deep_hidden_units: list | None = None,
                 share_cross_net: bool = True):
        super(ExpandedGlideatorNet, self).__init__()
        
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
        
        # Calculate input dimension for CrossNet and ParallelDeepNet (for a single time point)
        single_time_input_dim = weather_dim + site_dim + site_embedding_dim + date_dim
        
        self.share_cross_net = share_cross_net
        self.time_keys = ['9', '12', '15']

        # Cross Network(s) (shared or separate for each time point)
        if self.share_cross_net:
            self.cross_net = CrossNet(in_features=single_time_input_dim, num_layers=cross_layers)
        else:
            self.cross_nets = nn.ModuleDict({
                time_key: CrossNet(in_features=single_time_input_dim, num_layers=cross_layers)
                for time_key in self.time_keys
            })
        
        # Optional Parallel Deep Network (shared across time points)
        self.parallel_deep_net = None
        single_time_output_dim = single_time_input_dim # Output of CrossNet. This is the base dimension for one time slice.

        # Only proceed if parallel_deep_hidden_units is a non-empty list
        if parallel_deep_hidden_units and isinstance(parallel_deep_hidden_units, list) and len(parallel_deep_hidden_units) > 0:
            parallel_deep_layers = []
            prev_parallel_units = single_time_input_dim
            for hidden_units in parallel_deep_hidden_units:
                parallel_deep_layers.append(nn.Linear(prev_parallel_units, hidden_units))
                parallel_deep_layers.append(nn.ReLU())
                prev_parallel_units = hidden_units
            self.parallel_deep_net = nn.Sequential(*parallel_deep_layers)
            # If parallel_deep_net is created, its output will be concatenated.
            # The dimension added is the size of the last layer of this parallel_deep_net.
            single_time_output_dim += parallel_deep_hidden_units[-1] 
            
        # Calculate input dimension for the main DeepNet (concatenation of 3 time-slice outputs)
        main_deep_input_dim = 3 * single_time_output_dim
        
        # Main Deep Network
        deep_layers = []
        prev_units = main_deep_input_dim
        for hidden_units in deep_hidden_units:
            deep_layers.append(nn.Linear(prev_units, hidden_units))
            deep_layers.append(nn.ReLU())
            prev_units = hidden_units
        
        self.deep_net = nn.Sequential(*deep_layers)
        
        # Output Layers (input is the output of the deep network)
        final_dim = deep_hidden_units[-1]
        
        self.prediction_head_type = prediction_head_type
        if self.prediction_head_type == "multilabel":
            self.prediction_head = MultilabelHead(final_dim, num_targets)
        elif self.prediction_head_type == "ordinal":
            if num_targets < 2: # num_targets is treated as num_classes for ordinal
                raise ValueError("Ordinal prediction head requires num_targets (num_classes) >= 2.")
            self.prediction_head = OrdinalHead(final_dim, num_targets)
        else:
            raise ValueError(f"Unknown prediction_head_type: {self.prediction_head_type}")

    def forward(self, features):
        """
        Forward pass of the ExpandedGlideatorNet.
        
        Args:
            features (dict): Dictionary containing:
                - 'weather': Dict of weather features {'9': tensor, '12': tensor, '15': tensor}
                - 'site': Site features tensor
                - 'site_id': Site ID tensor
                - 'date': Date features tensor

        Returns:
            torch.Tensor: Predicted probabilities for each threshold, shape (batch_size, num_targets)
        """
        # Scale site features
        site_scaled = self.site_scaler(features['site'])
        
        # Get the launch embedding
        launch_embedded = self.launch_embedding(features['site_id'])
        
        # Normalize year by dividing by 2000
        date_features = features['date'].clone()
        date_features[:, 1] = date_features[:, 1] / 2000
        
        time_slice_outputs = []
        for time_key in self.time_keys:
            # Scale weather features for the current time
            weather_scaled = self.weather_scaler(features['weather'][time_key])
            
            # Concatenate features for the current time
            combined_features_time = torch.cat([
                weather_scaled,
                site_scaled,
                launch_embedded,
                date_features
            ], dim=-1)
            
            # Cross Network forward pass for the current time
            if self.share_cross_net:
                cross_out_time = self.cross_net(combined_features_time)
            else:
                cross_out_time = self.cross_nets[time_key](combined_features_time)
            
            if self.parallel_deep_net is not None:
                parallel_deep_out_time = self.parallel_deep_net(combined_features_time)
                # Concatenate Cross and Parallel Deep outputs for the current time slice
                time_slice_combined_out = torch.cat([cross_out_time, parallel_deep_out_time], dim=-1)
            else:
                time_slice_combined_out = cross_out_time
                
            time_slice_outputs.append(time_slice_combined_out)
            
        # Concatenate outputs from all time slices
        final_concat = torch.cat(time_slice_outputs, dim=-1)
        
        # Main Deep Network forward pass
        deep_out = self.deep_net(final_concat)
        
        # Output layers
        return self.prediction_head(deep_out)