#!/usr/bin/env python3
"""
Peak Frame Ultra-Fast Telemetry Background Watcher Daemon.
Polls GitHub GraphQL API every 5 seconds for live contribution updates in Indian Standard Time (IST).
Includes automatic rate-limit protection and instant auto-sync.
"""

import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(SCRIPTS_DIR))
import sync_telemetry


def get_token():
    token = os.environ.get("GH_TOKEN")
    if not token:
        try:
            token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
        except Exception:
            token = ""
    return token


def fetch_live_data(token):
    import urllib.request
    IST = dt.timezone(dt.timedelta(hours=5, minutes=30), name="IST")
    current_year = dt.datetime.now(IST).year
    query = f"""
    query {{
      user(login: "Vijaysir0hi") {{
        contributionsCollection(from: "{current_year}-01-01T00:00:00+05:30", to: "{current_year}-12-31T23:59:59+05:30") {{
          contributionCalendar {{
            totalContributions
          }}
        }}
      }}
      rateLimit {{
        remaining
        resetAt
      }}
    }}
    """
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "User-Agent": "PeakFrame"}
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.load(resp)
        coll = data["data"]["user"]["contributionsCollection"]
        count = coll["contributionCalendar"]["totalContributions"]
        remaining = data.get("data", {}).get("rateLimit", {}).get("remaining", 5000)
        return count, remaining


def run_daemon(target_interval=5):
    print(f"[{dt.datetime.now().isoformat()}] Starting Peak Frame Real-Time Telemetry Daemon (poll interval: {target_interval}s)...")
    token = get_token()
    last_known_count = None
    
    progress_file = ROOT / "profile" / "progress.json"
    if progress_file.exists():
        try:
            snap = json.loads(progress_file.read_text(encoding="utf-8"))
            last_known_count = sum(snap.get("activity", {}).get("daily", {}).values())
        except Exception:
            last_known_count = None

    sleep_time = target_interval
    while True:
        try:
            current_count, remaining = fetch_live_data(token)
            
            # Rate limit guard: 5s consumes 720/hr out of 5,000/hr limit.
            # If remaining ever dips below 200, step down to 15s to be 100% safe.
            if remaining < 200:
                sleep_time = 15
            else:
                sleep_time = target_interval

            if last_known_count is None or current_count != last_known_count:
                print(f"[{dt.datetime.now().isoformat()}] Live contribution change detected: {last_known_count} -> {current_count}. Triggering instant sync (API points left: {remaining})...")
                sync_telemetry.sync()
                last_known_count = current_count
        except Exception as e:
            # Silently pass transient network blips and retry next tick
            pass
        
        time.sleep(sleep_time)


if __name__ == "__main__":
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    run_daemon(interval)
