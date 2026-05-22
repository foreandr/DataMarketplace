from __future__ import annotations

import importlib.util
from pathlib import Path
import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "actions" / "volleyball" / "send_agency_emails.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("send_agency_emails", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_send_all_routes_to_test_address_when_test_mode_is_on(monkeypatch) -> None:
    module = _load_module()
    sent_calls: list[dict[str, object]] = []
    log_path = ROOT / "actions" / "volleyball" / "test-send-log.txt"
    if log_path.exists():
        log_path.unlink()

    monkeypatch.setattr(
        module,
        "iter_agencies",
        lambda: ["one@example.com", "two@example.com"],
    )
    monkeypatch.setattr(module, "LOG_PATH", log_path)

    def fake_send_email(**kwargs):
        sent_calls.append(kwargs)
        return True

    monkeypatch.setattr(module.email_sender, "send_email", fake_send_email)

    sent_count = module.send_all(test_mode=True)

    assert sent_count == 2
    assert [call["receiver"] for call in sent_calls] == [
        module.TEST_RECEIVER,
        module.TEST_RECEIVER,
    ]
    assert all(
        call["attachment_paths"] == [str(module.CV_PATH)]
        for call in sent_calls
    )
    log_text = log_path.read_text(encoding="utf-8")
    assert "original_agency=one@example.com" in log_text
    assert "original_agency=two@example.com" in log_text
    assert f"sent_to={module.TEST_RECEIVER}" in log_text
    log_path.unlink()


def test_send_all_uses_real_agencies_when_test_mode_is_off(monkeypatch) -> None:
    module = _load_module()
    sent_calls: list[dict[str, object]] = []
    log_path = ROOT / "actions" / "volleyball" / "test-send-log.txt"
    if log_path.exists():
        log_path.unlink()

    monkeypatch.setattr(
        module,
        "iter_agencies",
        lambda: ["agent1@example.com", "agent2@example.com"],
    )
    monkeypatch.setattr(module, "LOG_PATH", log_path)

    def fake_send_email(**kwargs):
        sent_calls.append(kwargs)
        return True

    monkeypatch.setattr(module.email_sender, "send_email", fake_send_email)

    sent_count = module.send_all(test_mode=False)

    assert sent_count == 2
    assert [call["receiver"] for call in sent_calls] == [
        "agent1@example.com",
        "agent2@example.com",
    ]
    log_text = log_path.read_text(encoding="utf-8")
    assert "original_agency=agent1@example.com" in log_text
    assert "original_agency=agent2@example.com" in log_text
    assert "sent_to=agent1@example.com" in log_text
    assert "sent_to=agent2@example.com" in log_text
    log_path.unlink()


def test_live_send_skips_agencies_already_logged_as_live(monkeypatch, capsys) -> None:
    module = _load_module()
    sent_calls: list[dict[str, object]] = []
    sleep_calls: list[int] = []
    log_path = ROOT / "actions" / "volleyball" / "test-send-log.txt"
    log_path.write_text(
        "2026-05-22T02:39:11.906341+00:00 | original_agency=sent@example.com | "
        "sent_to=sent@example.com | test_mode=false\n"
        "2026-05-22T02:39:25.295755+00:00 | original_agency=tested@example.com | "
        "sent_to=foreandr@gmail.com | test_mode=true\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        module,
        "iter_agencies",
        lambda: ["sent@example.com", "tested@example.com", "fresh@example.com"],
    )
    monkeypatch.setattr(module, "LOG_PATH", log_path)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    def fake_send_email(**kwargs):
        sent_calls.append(kwargs)
        return True

    monkeypatch.setattr(module.email_sender, "send_email", fake_send_email)

    sent_count = module.send_all(test_mode=False)

    assert sent_count == 2
    assert [call["receiver"] for call in sent_calls] == [
        "tested@example.com",
        "fresh@example.com",
    ]
    assert sleep_calls == [5]
    output = capsys.readouterr().out
    assert "SKIPPING ALREADY-SENT LIVE AGENCY: sent@example.com" in output
    assert "WAITING 5 SECONDS" in output
    log_text = log_path.read_text(encoding="utf-8")
    assert log_text.count("original_agency=sent@example.com") == 1
    log_path.unlink()
