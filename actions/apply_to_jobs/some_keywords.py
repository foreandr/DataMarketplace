"""
Compatibility shim for older callers.

The canonical keyword definitions now live in keywords.py.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


_KEYWORDS_PATH = Path(__file__).with_name("keywords.py")
_SPEC = importlib.util.spec_from_file_location("apply_keywords_canonical", _KEYWORDS_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

SOFTWARE_KEYWORDS = _MODULE.SOFTWARE_KEYWORDS
PLACEMENT_KEYWORDS = _MODULE.PLACEMENT_KEYWORDS
