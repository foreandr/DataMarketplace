import json
import os
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT_DIR / "logs" / "report"

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


def _write_stats(stats: dict) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_path = LOG_DIR / f"monitor_server_{stamp}.json"
    out_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return out_path


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
