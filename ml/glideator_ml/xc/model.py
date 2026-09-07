from __future__ import annotations

from collections.abc import Mapping, Sequence

import torch
from torch import nn
import torch.nn.functional as F


class StandardScalerLayer(nn.Module):
    """Fixed z-score scaling embedded in the model graph."""

    def __init__(self, scaling_params: Mapping[str, Mapping[str, float]]) -> None:
        super().__init__()
        self.means = nn.Parameter(
            torch.tensor(
                [param["mean"] for param in scaling_params.values()], dtype=torch.float32
            ),
            requires_grad=False,
        )
        self.stds = nn.Parameter(
            torch.tensor(
                [param["std"] for param in scaling_params.values()], dtype=torch.float32
            ),
            requires_grad=False,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.means) / self.stds


class CrossNet(nn.Module):
    """TorchRec-compatible full-rank CrossNet without the TorchRec dependency.

    Parameter names and shapes intentionally match ``torchrec.modules.crossnet.CrossNet``
    so legacy XC state dicts can be loaded unchanged.
    """

    def __init__(self, in_features: int, num_layers: int) -> None:
        super().__init__()
        self._num_layers = num_layers
        self.kernels = nn.ParameterList(
            [
                nn.Parameter(nn.init.xavier_normal_(torch.empty(in_features, in_features)))
                for _ in range(num_layers)
            ]
        )
        self.bias = nn.ParameterList(
            [
                nn.Parameter(nn.init.zeros_(torch.empty(in_features, 1)))
                for _ in range(num_layers)
            ]
        )

    def forward(self, input: torch.Tensor) -> torch.Tensor:
        x_0 = input.unsqueeze(2)
        x_l = x_0
        for layer in range(self._num_layers):
            xl_w = torch.matmul(self.kernels[layer], x_l)
            x_l = x_0 * (xl_w + self.bias[layer]) + x_l
        return torch.squeeze(x_l, dim=2)


class MultilabelHead(nn.Module):
    def __init__(self, input_dim: int, num_targets: int) -> None:
        super().__init__()
        self.output_layers = nn.ModuleList(
            [nn.Linear(input_dim, 1) for _ in range(num_targets)]
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.cat(
            [torch.sigmoid(layer(x)) for layer in self.output_layers], dim=-1
        )


class OrdinalHead(nn.Module):
    def __init__(self, input_dim: int, num_targets: int) -> None:
        super().__init__()
        self.num_targets = num_targets
        self.num_classes = num_targets + 1
        self.fc = nn.Linear(input_dim, 1)
        self.bias_base = nn.Parameter(torch.tensor(0.0))
        self.bias_deltas = nn.Parameter(torch.ones(self.num_classes - 1))

    def get_ordered_thresholds(self) -> torch.Tensor:
        deltas = F.softplus(self.bias_deltas)
        return self.bias_base + torch.cumsum(deltas, dim=0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        a = self.fc(x).squeeze(-1)
        thresholds = self.get_ordered_thresholds()
        logits = thresholds.unsqueeze(0) - a.unsqueeze(1)
        return 1.0 - torch.sigmoid(logits)


class AdaptiveMonotonicHead(nn.Module):
    """Feature-conditioned cumulative logits with monotonic probabilities.

    XC0 gets an unconstrained base logit. Each harder threshold subtracts a
    positive, feature-dependent gap from the previous logit. The gaps are
    produced with ``softplus``, so probabilities can never increase as the XC
    threshold rises while still allowing weather-dependent threshold spacing.
    """

    def __init__(self, input_dim: int, num_targets: int) -> None:
        super().__init__()
        if num_targets < 2:
            raise ValueError("Adaptive monotonic head requires num_targets >= 2")
        self.num_targets = num_targets
        self.base_logit = nn.Linear(input_dim, 1)
        self.gap_logits = nn.Linear(input_dim, num_targets - 1)

        # Start from a sensible decreasing curve without initially imposing
        # feature-dependent threshold gaps. softplus(-1) ~= 0.31, which gives
        # the optimizer useful gradients across the full XC0..XC100 range.
        nn.init.zeros_(self.gap_logits.weight)
        nn.init.constant_(self.gap_logits.bias, -1.0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        base = self.base_logit(x)
        gaps = F.softplus(self.gap_logits(x))
        cumulative_gaps = torch.cumsum(gaps, dim=-1)
        logits = torch.cat([base, base - cumulative_gaps], dim=-1)
        return torch.sigmoid(logits)


def _deep_tower(input_dim: int, hidden_units: Sequence[int]) -> nn.Sequential:
    layers: list[nn.Module] = []
    previous = input_dim
    for units in hidden_units:
        layers.extend((nn.Linear(previous, units), nn.ReLU()))
        previous = units
    return nn.Sequential(*layers)


class ExpandedGlideatorNet(nn.Module):
    """Production XC architecture, migrated into the model-family workspace.

    The default module and parameter names intentionally mirror
    ``net.net.ExpandedGlideatorNet`` so legacy training checkpoints can be
    loaded via ``load_state_dict``. Experimental constructor flags default to
    the legacy behavior and are used only by candidate configs.
    """

    time_keys = ("9", "12", "15")

    def __init__(
        self,
        weather_scaler: StandardScalerLayer,
        site_scaler: StandardScalerLayer,
        num_launches: int,
        num_targets: int = 11,
        deep_hidden_units: Sequence[int] = (64, 32),
        cross_layers: int = 2,
        site_embedding_dim: int = 8,
        prediction_head_type: str = "multilabel",
        parallel_deep_hidden_units: Sequence[int] | None = None,
        share_cross_net: bool = True,
        include_time_input_branch: bool = True,
        share_parallel_deep_net: bool = True,
    ) -> None:
        super().__init__()
        if not deep_hidden_units:
            raise ValueError("deep_hidden_units must contain at least one layer")
        if not include_time_input_branch and cross_layers:
            raise ValueError(
                "cross_layers must be 0 when include_time_input_branch is false"
            )

        self.weather_scaler = weather_scaler
        self.site_scaler = site_scaler
        weather_dim = len(weather_scaler.means)
        site_dim = len(site_scaler.means)
        date_dim = 4
        self.num_targets = num_targets
        self.launch_embedding = nn.Embedding(num_launches, site_embedding_dim)

        single_time_input_dim = weather_dim + site_dim + site_embedding_dim + date_dim
        self.share_cross_net = share_cross_net
        self.include_time_input_branch = include_time_input_branch
        self.share_parallel_deep_net = share_parallel_deep_net

        if include_time_input_branch:
            if share_cross_net:
                self.cross_net = CrossNet(single_time_input_dim, cross_layers)
            else:
                self.cross_nets = nn.ModuleDict(
                    {
                        time_key: CrossNet(single_time_input_dim, cross_layers)
                        for time_key in self.time_keys
                    }
                )

        self.parallel_deep_net: nn.Sequential | None = None
        self.parallel_deep_nets: nn.ModuleDict | None = None
        if parallel_deep_hidden_units:
            if share_parallel_deep_net:
                self.parallel_deep_net = _deep_tower(
                    single_time_input_dim, parallel_deep_hidden_units
                )
            else:
                self.parallel_deep_nets = nn.ModuleDict(
                    {
                        time_key: _deep_tower(
                            single_time_input_dim, parallel_deep_hidden_units
                        )
                        for time_key in self.time_keys
                    }
                )

        single_time_output_dim = 0
        if include_time_input_branch:
            single_time_output_dim += single_time_input_dim
        if parallel_deep_hidden_units:
            single_time_output_dim += parallel_deep_hidden_units[-1]
        if single_time_output_dim == 0:
            raise ValueError(
                "At least one of the time input branch or parallel deep tower is required"
            )

        self.deep_net = _deep_tower(
            len(self.time_keys) * single_time_output_dim, deep_hidden_units
        )

        self.prediction_head_type = prediction_head_type
        if prediction_head_type == "multilabel":
            self.prediction_head = MultilabelHead(deep_hidden_units[-1], num_targets)
        elif prediction_head_type == "ordinal":
            if num_targets < 2:
                raise ValueError("Ordinal prediction head requires num_targets >= 2")
            self.prediction_head = OrdinalHead(deep_hidden_units[-1], num_targets)
        elif prediction_head_type == "adaptive_monotonic":
            self.prediction_head = AdaptiveMonotonicHead(
                deep_hidden_units[-1], num_targets
            )
        else:
            raise ValueError(f"Unknown prediction_head_type: {prediction_head_type}")

    def forward(self, features: Mapping[str, object]) -> torch.Tensor:
        weather = features["weather"]
        if not isinstance(weather, Mapping):
            raise TypeError(
                "features['weather'] must be a mapping keyed by 9, 12 and 15"
            )

        site = features["site"]
        site_id = features["site_id"]
        date = features["date"]
        if not all(
            isinstance(value, torch.Tensor) for value in (site, site_id, date)
        ):
            raise TypeError("site, site_id and date features must be tensors")

        site_scaled = self.site_scaler(site)
        launch_embedded = self.launch_embedding(site_id)
        date_features = date.clone()
        date_features[:, 1] = date_features[:, 1] / 2000

        time_slice_outputs = []
        for time_key in self.time_keys:
            weather_value = weather[time_key]
            if not isinstance(weather_value, torch.Tensor):
                raise TypeError(f"weather[{time_key!r}] must be a tensor")
            weather_scaled = self.weather_scaler(weather_value)
            combined = torch.cat(
                [weather_scaled, site_scaled, launch_embedded, date_features], dim=-1
            )

            branches: list[torch.Tensor] = []
            if self.include_time_input_branch:
                if self.share_cross_net:
                    branches.append(self.cross_net(combined))
                else:
                    branches.append(self.cross_nets[time_key](combined))
            if self.parallel_deep_net is not None:
                branches.append(self.parallel_deep_net(combined))
            elif self.parallel_deep_nets is not None:
                branches.append(self.parallel_deep_nets[time_key](combined))

            time_slice_outputs.append(
                branches[0] if len(branches) == 1 else torch.cat(branches, dim=-1)
            )

        deep_output = self.deep_net(torch.cat(time_slice_outputs, dim=-1))
        return self.prediction_head(deep_output)
