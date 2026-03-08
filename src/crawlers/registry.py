"""Dynamic crawler loader."""
from __future__ import annotations

import importlib
from typing import Type

from crawlers.base import BaseCrawler


def load_crawler(dotted_path: str) -> Type[BaseCrawler]:
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    if not issubclass(cls, BaseCrawler):
        raise TypeError(f"{dotted_path} is not a BaseCrawler")
    return cls
