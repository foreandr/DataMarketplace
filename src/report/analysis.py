from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import db_report, monitor_server
from report_paths import iter_report_files
from telegram_messaging import send_message


FORCE_SEND = False

ROOT_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT_DIR / "logs" / "report"


def _get_env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "").strip() or default)
    except Exception:
        return default


def _get_env_int(name: str, default: int) -> int:
    try:
        return int(float(os.getenv(name, "").strip() or default))
    except Exception:
        return default


def _load_latest_db_report() -> dict | None:
    reports = list(iter_report_files(LOG_DIR, "db_report", "db_report_*.json"))
    if not reports:
        return None
    path = max(reports, key=lambda p: p.stat().st_mtime)
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_timestamp(value: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue
    return None


def _load_monitor_samples(hours: int = 24) -> list[dict]:
    cutoff = datetime.now() - timedelta(hours=hours)
    samples: list[dict] = []
    for path in iter_report_files(LOG_DIR, "monitor_server", "monitor_server_*.json"):
        try:
            if datetime.fromtimestamp(path.stat().st_mtime) < cutoff:
                continue
        except Exception:
            pass
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        ts = None
        if isinstance(data, dict) and data.get("timestamp"):
            ts = _parse_timestamp(str(data["timestamp"]))
        if not ts:
            try:
                ts = datetime.fromtimestamp(path.stat().st_mtime)
            except Exception:
                continue
        if ts < cutoff:
            continue
        data["_ts"] = ts
        samples.append(data)
    return sorted(samples, key=lambda x: x["_ts"])


def _metric_summary(samples: list[dict], key: str, warn: float, crit: float) -> dict[str, Any]:
    if not samples:
        return {"count": 0}
    values = [float(s.get(key, 0)) for s in samples if s.get(key) is not None]
    if not values:
        return {"count": 0}
    count = len(values)
    max_v = max(values)
    avg_v = sum(values) / count
    warn_hits = sum(1 for v in values if v >= warn)
    crit_hits = sum(1 for v in values if v >= crit)
    return {
        "count": count,
        "max": round(max_v, 2),
        "avg": round(avg_v, 2),
        "warn_hits": warn_hits,
        "crit_hits": crit_hits,
        "warn_ratio": round(warn_hits / count, 2),
        "crit_ratio": round(crit_hits / count, 2),
    }


def _build_message(db_payload: dict | None, samples: list[dict]) -> tuple[str, bool]:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    latest = samples[-1] if samples else {}

    cpu_warn = _get_env_float("TELEMETRY_CPU_WARN", 80)
    cpu_crit = _get_env_float("TELEMETRY_CPU_CRIT", 95)
    ram_warn = _get_env_float("TELEMETRY_RAM_WARN", 80)
    ram_crit = _get_env_float("TELEMETRY_RAM_CRIT", 95)
    disk_warn = _get_env_float("TELEMETRY_DISK_WARN", 85)
    disk_crit = _get_env_float("TELEMETRY_DISK_CRIT", 95)
    min_samples = _get_env_int("TELEMETRY_ALERT_MIN_SAMPLES", 2)
    min_ratio = _get_env_float("TELEMETRY_ALERT_MIN_RATIO", 0.5)

    windows = {
        "1h": [s for s in samples if s["_ts"] >= datetime.now() - timedelta(hours=1)],
        "6h": [s for s in samples if s["_ts"] >= datetime.now() - timedelta(hours=6)],
        "24h": samples,
    }

    def window_line(label: str, key: str, warn: float, crit: float) -> tuple[str, bool]:
        sm = _metric_summary(windows[label], key, warn, crit)
        if sm.get("count", 0) == 0:
            return f"{label}: no data", False
        crit_alert = sm["crit_hits"] >= min_samples and sm["crit_ratio"] >= min_ratio
        warn_alert = sm["warn_hits"] >= min_samples and sm["warn_ratio"] >= min_ratio
        alert = crit_alert or warn_alert
        flag = "CRIT" if crit_alert else "WARN" if warn_alert else "OK"
        line = (
            f"{label}: max {sm['max']} | avg {sm['avg']} | "
            f"warn {sm['warn_hits']}/{sm['count']} | "
            f"crit {sm['crit_hits']}/{sm['count']} => {flag}"
        )
        return line, alert

    cpu_lines = []
    cpu_alert = False
    for label in ("1h", "6h", "24h"):
        line, alert = window_line(label, "cpu_usage_percent", cpu_warn, cpu_crit)
        cpu_lines.append(line)
        cpu_alert = cpu_alert or alert

    ram_lines = []
    ram_alert = False
    for label in ("1h", "6h", "24h"):
        line, alert = window_line(label, "memory_percent_used", ram_warn, ram_crit)
        ram_lines.append(line)
        ram_alert = ram_alert or alert

    disk_lines = []
    disk_alert = False
    for label in ("1h", "6h", "24h"):
        line, alert = window_line(label, "disk_percent_full", disk_warn, disk_crit)
        disk_lines.append(line)
        disk_alert = disk_alert or alert

    current_cpu = latest.get("cpu_usage_percent", "N/A")
    current_ram = latest.get("memory_percent_used", "N/A")
    current_disk = latest.get("disk_percent_full", "N/A")
    current_load = latest.get("load_1m", "N/A")
    current_bw_in = latest.get("bandwidth_mbps_inbound", "N/A")
    current_bw_out = latest.get("bandwidth_mbps_outbound", "N/A")
    process_source = latest.get("processes_source")
    process_list = latest.get("processes_top_by_rss") or []

    lines = [
        "Data Marketplace Report",
        f"Generated: {now}",
        "",
        "Server Telemetry (current):",
        f"CPU: {current_cpu}%",
        f"RAM: {current_ram}%",
        f"Disk: {current_disk}%",
        f"Load1m: {current_load}",
        f"Bandwidth (Mbps): in {current_bw_in} | out {current_bw_out}",
        "",
        "CPU Window Summary:",
        *cpu_lines,
        "",
        "RAM Window Summary:",
        *ram_lines,
        "",
        "Disk Window Summary:",
        *disk_lines,
    ]

    if process_list:
        lines.append("")
        lines.append("Top Memory Processes:")
        if process_source:
            lines.append(f"Source: {process_source}")
        for proc in process_list[:5]:
            pid = proc.get("pid", "?")
            cmd = proc.get("command", "?")
            rss = proc.get("rss_mb", "?")
            cpu = proc.get("cpu_percent", "?")
            mem = proc.get("mem_percent", "?")
            lines.append(f"{pid} {cmd} | rss {rss} MB | cpu {cpu}% | mem {mem}%")

    if db_payload:
        lines.append("")
        lines.append("DB Report Summary:")
        dbs = db_payload.get("data", []) if isinstance(db_payload, dict) else db_payload
        for db in (dbs or [])[:5]:
            db_name = db.get("db_name", "unknown")
            lines.append(f"- {db_name}")
            for table in (db.get("tables") or [])[:3]:
                rows = table.get("rows", 0)
                rates = table.get("rates") or {}
                if rates:
                    lines.append(
                        f"  {table.get('name')}: rows {rows} | "
                        f"1h {rates.get('rows_last_1h')} | "
                        f"24h {rates.get('rows_last_24h')}"
                    )
                else:
                    lines.append(f"  {table.get('name')}: rows {rows}")

    alert = cpu_alert or ram_alert or disk_alert
    return "\n".join(lines), alert


def main() -> None:
    load_dotenv()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    db_report.main()
    monitor_server.main() if hasattr(monitor_server, "main") else None

    db_payload = _load_latest_db_report()
    samples = _load_monitor_samples(hours=24)
    message, alert = _build_message(db_payload, samples)

    send_always = os.getenv("TELEMETRY_SEND_ALWAYS", "false").lower() in {"1", "true", "yes", "on"}
    if alert or send_always or FORCE_SEND:
        send_message(message)
    else:
        print("No alert conditions met. Message not sent.")


if __name__ == "__main__":
    main()
