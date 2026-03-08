"""Core schemas for API specs and metadata."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ApiSpec:
    name: str
    version: str
    description: str
    metadata: Dict[str, Any]
