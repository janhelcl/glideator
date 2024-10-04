import torch
import torch.nn as nn
from torchrec.modules.crossnet import CrossNet


class GlideatorNet(nn.Module):
    """
    A neural network model for glide prediction using a combination of Cross Network and Deep Network.

    This model is designed to predict multiple targets related to gliding performance based on
    various input features and launch site information.

    Attributes:
        launch_embedding (nn.Embedding): Embedding layer for launch site categorical data.
        cross_net (CrossNet): Cross Network for capturing feature interactions.
        deep_net (nn.Sequential): Deep Neural Network for learning complex patterns.
        output_layers (nn.ModuleList): Multiple output layers for multi-target prediction.

    Args:
        input_dim (int): Dimension of the input features.
        num_launches (int): Number of unique launch sites.
        launch_embedding_dim (int): Dimension of the launch site embedding.
        num_targets (int, optional): Number of prediction targets. Defaults to 3.
        deep_hidden_units (list, optional): List of hidden unit sizes for the deep network. 
                                            Defaults to [64, 32].
        cross_layers (int, optional): Number of layers in the Cross Network. Defaults to 2.
    """

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
        """
        Forward pass of the GlideatorNet.

        Args:
            features (torch.Tensor): Input features tensor of shape (batch_size, input_dim).
            launch_ids (torch.Tensor): Tensor of launch site IDs of shape (batch_size,).

        Returns:
            torch.Tensor: Predicted outputs for each target, shape (batch_size, num_targets).
        """
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