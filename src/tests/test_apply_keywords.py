from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
KEYWORDS_PATH = ROOT_DIR / "actions" / "apply_to_jobs" / "keywords.py"
SOME_KEYWORDS_PATH = ROOT_DIR / "actions" / "apply_to_jobs" / "some_keywords.py"


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_keywords_module_loads_with_clean_lists() -> None:
    module = _load_module("apply_keywords", KEYWORDS_PATH)

    assert module.SOFTWARE_KEYWORDS
    assert module.PLACEMENT_KEYWORDS
    assert all(isinstance(keyword, str) and keyword.strip() for keyword in module.SOFTWARE_KEYWORDS)
    assert all(isinstance(keyword, str) and keyword.strip() for keyword in module.PLACEMENT_KEYWORDS)
    assert len(module.SOFTWARE_KEYWORDS) == len(set(module.SOFTWARE_KEYWORDS))
    assert len(module.PLACEMENT_KEYWORDS) == len(set(module.PLACEMENT_KEYWORDS))


def test_requested_computer_and_it_roles_are_present() -> None:
    module = _load_module("apply_keywords", KEYWORDS_PATH)

    expected = {
        "computer technician",
        "computer network technician",
        "computer networks manager",
        "computer systems development manager",
        "computer systems manager",
        "manager computer systems",
        "computer programmer",
        "computer engineer",
        "personal computer technician",
        "pc technician",
        "programmer analyst",
        "systems programmer",
        "information systems manager",
        "information technology business analyst",
        "it business analyst",
        "test automation engineer",
        "application developer",
        "programmer, systems",
    }

    assert expected.issubset(set(module.SOFTWARE_KEYWORDS))


def test_some_keywords_reuses_canonical_software_keywords() -> None:
    keywords_module = _load_module("apply_keywords", KEYWORDS_PATH)
    some_keywords_module = _load_module("apply_some_keywords", SOME_KEYWORDS_PATH)

    assert some_keywords_module.SOFTWARE_KEYWORDS == keywords_module.SOFTWARE_KEYWORDS
