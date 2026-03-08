"""Selenium-driven marketplace portal stub."""
from __future__ import annotations

from typing import Dict, Any

from marketplaces.base import BasePublisher, PublishResult


class SeleniumPortalPublisher(BasePublisher):
    def publish(self, api_spec: Dict[str, Any]) -> PublishResult:
        raise NotImplementedError("Implement Selenium portal publishing logic.")
