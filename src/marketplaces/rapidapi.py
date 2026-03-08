"""RapidAPI publisher stub."""
from __future__ import annotations

from typing import Dict, Any

from marketplaces.base import BasePublisher, PublishResult


class RapidApiPublisher(BasePublisher):
    def publish(self, api_spec: Dict[str, Any]) -> PublishResult:
        raise NotImplementedError("Implement RapidAPI publishing logic.")
