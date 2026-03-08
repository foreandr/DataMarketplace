"""Marketplace publisher interfaces."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class PublishResult:
    success: bool
    message: str
    metadata: Dict[str, Any] | None = None


class BasePublisher:
    def __init__(self, name: str, base_url: str, auth: Dict[str, Any] | None = None):
        self.name = name
        self.base_url = base_url
        self.auth = auth or {}

    def publish(self, api_spec: Dict[str, Any]) -> PublishResult:
        """Publish a new API listing. Override in subclasses."""
        raise NotImplementedError
