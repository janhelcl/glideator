"""XC forecast model family.

The hosted Jev benchmark does not require PyTorch. Keep neural-model exports lazy so
``glideator-ml[jev]`` can load the task data/evaluation modules without also pulling
in the much larger ``xc`` extra.
"""

from typing import TYPE_CHECKING, Any

from .preprocessing import DATE_FEATURES, TARGET_NAMES, WEATHER_TIMES, XC_THRESHOLDS

if TYPE_CHECKING:
    from .model import ExpandedGlideatorNet, StandardScalerLayer

__all__ = [
    "DATE_FEATURES",
    "ExpandedGlideatorNet",
    "StandardScalerLayer",
    "TARGET_NAMES",
    "WEATHER_TIMES",
    "XC_THRESHOLDS",
]


def __getattr__(name: str) -> Any:
    if name in {"ExpandedGlideatorNet", "StandardScalerLayer"}:
        from .model import ExpandedGlideatorNet, StandardScalerLayer

        return {
            "ExpandedGlideatorNet": ExpandedGlideatorNet,
            "StandardScalerLayer": StandardScalerLayer,
        }[name]
    raise AttributeError(name)
