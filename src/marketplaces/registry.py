"""Dynamic publisher loader."""
from __future__ import annotations

import importlib
from typing import Type

from marketplaces.base import BasePublisher


def load_publisher(dotted_path: str) -> Type[BasePublisher]:
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    if not issubclass(cls, BasePublisher):
        raise TypeError(f"{dotted_path} is not a BasePublisher")
    return cls
