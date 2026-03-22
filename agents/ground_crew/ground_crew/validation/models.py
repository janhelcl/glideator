"""Common validation data models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ValidationStatus(str, Enum):
    OK = "ok"
    DEAD = "dead"
    REDIRECTED = "redirected"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class ValidationResult:
    status: ValidationStatus
    http_status: Optional[int] = None
    final_url: Optional[str] = None
    latency_ms: Optional[int] = None
    error: Optional[str] = None


