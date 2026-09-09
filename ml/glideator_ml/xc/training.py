from __future__ import annotations

import copy
import logging
import random
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, TensorDataset

from .benchmark import XCFeatureContract
from .data import fit_scaling_params
from .model import ExpandedGlideatorNet, StandardScalerLayer
from .objective import xc_loss
from .preprocessing import DATE_FEATURES, TARGET_NAMES, WEATHER_TIMES

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class XCFitResult:
    model: ExpandedGlideatorNet
    weather_scaling_params: dict[str, dict[str, float]]
    site_scaling_params: dict[str, dict[str, float]]
    model_config: dict[str, Any]
    history: list[dict[str, float | int]]
    best_epoch: int
    best_validation_loss: float
    device: str


def _seed_everything(seed: int, deterministic: bool) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    if deterministic:
        torch.use_deterministic_algorithms(True)


def _device(value: str) -> torch.device:
    if value == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(value)


def _dataset(frame: pd.DataFrame, features: XCFeatureContract) -> TensorDataset:
    weather = [
        torch.tensor(
            frame[list(features.weather_columns(hour))].to_numpy(dtype=np.float32),
            dtype=torch.float32,
        )
        for hour in WEATHER_TIMES
    ]
    site = torch.tensor(
        frame[list(features.site_features)].to_numpy(dtype=np.float32), dtype=torch.float32
    )
    site_id = torch.tensor(frame["site_id"].to_numpy(dtype=np.int64), dtype=torch.int64)
    date = torch.tensor(
        frame[list(DATE_FEATURES)].to_numpy(dtype=np.float32), dtype=torch.float32
    )
    targets = torch.tensor(
        frame[list(TARGET_NAMES)].to_numpy(dtype=np.float32), dtype=torch.float32
    )
    return TensorDataset(*weather, site, site_id, date, targets)


def _features(batch: tuple[torch.Tensor, ...], device: torch.device):
    weather_9, weather_12, weather_15, site, site_id, date, targets = batch
    inputs = {
        "weather": {
            "9": weather_9.to(device),
            "12": weather_12.to(device),
            "15": weather_15.to(device),
        },
        "site": site.to(device),
        "site_id": site_id.to(device),
        "date": date.to(device),
    }
    return inputs, targets.to(device)


def _regularization(model: torch.nn.Module, l1: float, l2: float) -> torch.Tensor:
    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    if not trainable:
        raise ValueError("XC model has no trainable parameters")
    result = trainable[0].new_zeros(())
    if l1:
        result = result + l1 * sum(parameter.abs().sum() for parameter in trainable)
    if l2:
        result = result + l2 * sum(parameter.square().sum() for parameter in trainable)
    return result


def _validation_loss(
    model: ExpandedGlideatorNet,
    loader: DataLoader,
    device: torch.device,
) -> float:
    model.eval()
    weighted_loss = 0.0
    rows = 0
    with torch.no_grad():
        for batch in loader:
            inputs, targets = _features(batch, device)
            loss = xc_loss(model(inputs), targets).prediction
            batch_rows = int(targets.shape[0])
            weighted_loss += float(loss.item()) * batch_rows
            rows += batch_rows
    return weighted_loss / rows


def fit_xc(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    features: XCFeatureContract,
    config: dict[str, Any],
) -> XCFitResult:
    """Fit on train and use validation only for model selection/early stopping."""

    seed = int(config.get("seed", 42))
    deterministic = bool(config.get("deterministic", True))
    _seed_everything(seed, deterministic)
    device = _device(str(config.get("device", "auto")))

    weather_scaling, site_scaling = fit_scaling_params(train, features)
    requested_launches = config.get("num_launches")
    num_launches = int(requested_launches or (int(train["site_id"].max()) + 1))
    max_site_id = int(max(train["site_id"].max(), validation["site_id"].max()))
    if num_launches <= max_site_id:
        raise ValueError(
            f"model.num_launches={num_launches} cannot represent site_id={max_site_id}"
        )

    model_config = {
        "num_launches": num_launches,
        "num_targets": len(TARGET_NAMES),
        "deep_hidden_units": list(config.get("deep_hidden_units", [64, 32])),
        "cross_layers": int(config.get("cross_layers", 2)),
        "site_embedding_dim": int(config.get("site_embedding_dim", 8)),
        "prediction_head_type": str(config.get("prediction_head_type", "multilabel")),
        "parallel_deep_hidden_units": config.get("parallel_deep_hidden_units"),
        "share_cross_net": bool(config.get("share_cross_net", True)),
        "include_time_input_branch": bool(
            config.get("include_time_input_branch", True)
        ),
        "share_parallel_deep_net": bool(
            config.get("share_parallel_deep_net", True)
        ),
        "dropout": float(config.get("dropout", 0.0)),
    }
    model = ExpandedGlideatorNet(
        weather_scaler=StandardScalerLayer(weather_scaling),
        site_scaler=StandardScalerLayer(site_scaling),
        **model_config,
    ).to(device)
    logger.info(
        "Fitting XC model on %s rows, validating on %s rows, device=%s",
        len(train),
        len(validation),
        device,
    )

    batch_size = int(config.get("batch_size", 2048))
    generator = torch.Generator().manual_seed(seed)
    train_loader = DataLoader(
        _dataset(train, features),
        batch_size=batch_size,
        shuffle=True,
        generator=generator,
        num_workers=int(config.get("num_workers", 0)),
    )
    validation_loader = DataLoader(_dataset(validation, features), batch_size=batch_size)

    optimizer = torch.optim.Adam(
        model.parameters(), lr=float(config.get("learning_rate", 1e-3))
    )
    scheduler = torch.optim.lr_scheduler.ExponentialLR(
        optimizer, gamma=float(config.get("lr_decay", 1.0))
    )
    monotonicity_lambda = float(config.get("monotonicity_lambda", 1e-9))
    l1_lambda = float(config.get("l1_lambda", 1e-9))
    l2_lambda = float(config.get("l2_lambda", 1e-9))
    epochs = int(config.get("epochs", 30))
    patience_value = config.get("patience")
    patience = None if patience_value is None else int(patience_value)

    best_loss = float("inf")
    best_epoch = 0
    best_state = copy.deepcopy(model.state_dict())
    history: list[dict[str, float | int]] = []
    stale_epochs = 0

    for epoch in range(1, epochs + 1):
        model.train()
        train_total = 0.0
        train_rows = 0
        for batch in train_loader:
            inputs, targets = _features(batch, device)
            optimizer.zero_grad()
            loss = xc_loss(model(inputs), targets, monotonicity_lambda=monotonicity_lambda)
            total = loss.total + _regularization(model, l1_lambda, l2_lambda)
            total.backward()
            optimizer.step()
            rows = int(targets.shape[0])
            train_total += float(total.item()) * rows
            train_rows += rows

        validation_loss = _validation_loss(model, validation_loader, device)
        train_loss = train_total / train_rows
        logger.info(
            "XC epoch %s/%s train_loss=%.6f validation_loss=%.6f",
            epoch,
            epochs,
            train_loss,
            validation_loss,
        )
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "validation_loss": validation_loss,
                "learning_rate": float(optimizer.param_groups[0]["lr"]),
            }
        )
        if validation_loss < best_loss:
            best_loss = validation_loss
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
            stale_epochs = 0
        else:
            stale_epochs += 1
        scheduler.step()
        if patience is not None and stale_epochs >= patience:
            break

    model.load_state_dict(best_state)
    return XCFitResult(
        model=model,
        weather_scaling_params=weather_scaling,
        site_scaling_params=site_scaling,
        model_config=model_config,
        history=history,
        best_epoch=best_epoch,
        best_validation_loss=best_loss,
        device=str(device),
    )


def predict_xc(
    model: ExpandedGlideatorNet,
    frame: pd.DataFrame,
    features: XCFeatureContract,
    *,
    batch_size: int = 4096,
    device: str = "cpu",
) -> tuple[np.ndarray, np.ndarray]:
    target_device = torch.device(device)
    model = model.to(target_device)
    loader = DataLoader(_dataset(frame, features), batch_size=batch_size)
    predictions: list[np.ndarray] = []
    targets_out: list[np.ndarray] = []
    model.eval()
    with torch.no_grad():
        for batch in loader:
            inputs, targets = _features(batch, target_device)
            predictions.append(model(inputs).detach().cpu().numpy())
            targets_out.append(targets.detach().cpu().numpy())
    return np.concatenate(targets_out), np.concatenate(predictions)
