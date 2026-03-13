import json
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

from report_paths import write_report_json

ROOT_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT_DIR / "logs" / "report"
REPORT_NAME = "monitor_server"

load_dotenv()

def fetch_metric(url, headers):
    try:
        r = requests.get(url, headers=headers)
        return r.json()
    except:
        return None

def extract_val(data):
    try:
        return float(data['data']['result'][0]['values'][-1][1])
    except (KeyError, IndexError, TypeError):
        return 0.0

def _flatten_stats(stats: dict) -> dict:
    flat = {}
    for key, value in stats.items():
        if isinstance(value, dict):
            for sub_key, sub_val in value.items():
                flat[f"{key}_{sub_key}"] = sub_val
        else:
            flat[key] = value
    return flat


def _should_include_processes() -> bool:
    flag = os.getenv("MONITOR_SERVER_INCLUDE_PROCESSES", "auto").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return True
    if flag in {"0", "false", "no", "off"}:
        return False
    return platform.system().lower() == "linux"


def _run_command(cmd: list[str], timeout: int = 15) -> str | None:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            return None
        return result.stdout
    except Exception:
        return None


def _parse_ps_output(output: str) -> list[dict]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return []
    if lines[0].lower().startswith("pid"):
        lines = lines[1:]

    processes: list[dict] = []
    for line in lines:
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        pid, comm, cpu, mem, rss = parts
        try:
            rss_mb = round(float(rss) / 1024, 2)
        except Exception:
            rss_mb = 0.0
        processes.append(
            {
                "pid": int(pid) if pid.isdigit() else pid,
                "command": comm,
                "cpu_percent": float(cpu) if cpu.replace(".", "", 1).isdigit() else cpu,
                "mem_percent": float(mem) if mem.replace(".", "", 1).isdigit() else mem,
                "rss_mb": rss_mb,
            }
        )
    return processes


def _get_process_snapshot() -> dict | None:
    if not _should_include_processes():
        return None

    top_n = int(os.getenv("MONITOR_SERVER_PROCESS_TOP_N", "25"))
    host = os.getenv("MONITOR_SERVER_SSH_HOST", "").strip()
    user = os.getenv("MONITOR_SERVER_SSH_USER", "").strip() or "root"
    key_path = os.getenv("MONITOR_SERVER_SSH_KEY_PATH", "").strip()
    port = os.getenv("MONITOR_SERVER_SSH_PORT", "").strip() or "22"

    ps_cmd = "ps -eo pid,comm,%cpu,%mem,rss --sort=-rss"
    if host:
        ssh_cmd = ["ssh", "-o", "BatchMode=yes", "-p", port]
        if key_path:
            ssh_cmd += ["-i", key_path]
        ssh_cmd += [f"{user}@{host}", ps_cmd]
        output = _run_command(ssh_cmd, timeout=20)
        source = "ssh"
        source_host = host
    else:
        if platform.system().lower() != "linux":
            return {"error": "Process listing only supported on Linux or via SSH."}
        output = _run_command(["ps", "-eo", "pid,comm,%cpu,%mem,rss", "--sort=-rss"])
        source = "local"
        source_host = "local"

    if not output:
        return {"error": "Process listing failed.", "source": source, "host": source_host}

    processes = _parse_ps_output(output)
    return {
        "source": source,
        "host": source_host,
        "total_processes": len(processes),
        "top_by_rss": processes[: max(top_n, 1)],
    }


def _write_stats(stats: dict) -> Path:
    return write_report_json(LOG_DIR, REPORT_NAME, "monitor_server", stats)


def get_full_telemetry():
    token = os.getenv("DIGITAL_OCEAN_APP_PASSWORD")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get Droplet ID
    d_resp = requests.get("https://api.digitalocean.com/v2/droplets", headers=headers).json()
    if 'droplets' not in d_resp: return {"error": "API Token invalid or account empty."}
    d_id = d_resp['droplets'][0]['id']
    
    # 5-minute window
    end = int(datetime.now().timestamp())
    start = end - 300
    base_url = f"https://api.digitalocean.com/v2/monitoring/metrics/droplet"
    query = f"host_id={d_id}&start={start}&end={end}"

    stats = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "droplet_id": d_id
    }

    # 1. RAM Usage
    m_avail = extract_val(fetch_metric(f"{base_url}/memory_available?{query}", headers))
    m_total = extract_val(fetch_metric(f"{base_url}/memory_total?{query}", headers))
    if m_total > 0:
        used = m_total - m_avail
        stats['memory'] = {
            "total_gb": round(m_total / (1024**3), 2),
            "used_mb": round(used / (1024**2), 2),
            "percent_used": round((used / m_total) * 100, 2)
        }

    # 2. CPU & Load
    # Load 1 is the 1-minute load average. On a 1-core CPU, > 1.0 means you are bottlenecked.
    stats['load_1m'] = extract_val(fetch_metric(f"{base_url}/load_1?{query}", headers))
    
    # CPU Idle (Total CPU % used = 100 - idle)
    cpu_idle = extract_val(fetch_metric(f"{base_url}/cpu?{query}&mode=idle", headers))
    stats['cpu_usage_percent'] = round(100 - cpu_idle, 2) if cpu_idle > 0 else "N/A"

    # 3. Disk
    d_free = extract_val(fetch_metric(f"{base_url}/filesystem_free?{query}", headers))
    d_size = extract_val(fetch_metric(f"{base_url}/filesystem_size?{query}", headers))
    if d_size > 0:
        stats['disk'] = {
            "total_gb": round(d_size / (1024**3), 2),
            "free_gb": round(d_free / (1024**3), 2),
            "percent_full": round(((d_size - d_free) / d_size) * 100, 2)
        }

    # 4. Bandwidth (Public Network)
    # Incoming and Outgoing in Megabits per second (Mbps)
    inbound = extract_val(fetch_metric(f"{base_url}/bandwidth?{query}&interface=public&direction=inbound", headers))
    outbound = extract_val(fetch_metric(f"{base_url}/bandwidth?{query}&interface=public&direction=outbound", headers))
    stats['bandwidth_mbps'] = {
        "inbound": round(inbound * 8 / (1024**2), 2),
        "outbound": round(outbound * 8 / (1024**2), 2)
    }

    # 5. Process list (top memory consumers)
    processes = _get_process_snapshot()
    if processes:
        stats["processes"] = processes

    return stats


def main() -> dict:
    telemetry = get_full_telemetry()
    flattened = _flatten_stats(telemetry)
    out_path = _write_stats(flattened)
    print(json.dumps(flattened, indent=2))
    print(f"Saved report: {out_path}")
    return flattened

if __name__ == "__main__":
    main()
