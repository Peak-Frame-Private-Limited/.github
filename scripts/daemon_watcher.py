#!/usr/bin/env python3
"""
Peak Frame Real-Time Telemetry Background Watcher Daemon.
Polls GitHub GraphQL API every 30 seconds for live contribution updates in IST.
When new activity occurs anywhere (local or remote), immediately updates dashboards and pushes to GitHub.
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


def fetch_live_count(token):
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
    }}
    """
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "User-Agent": "PeakFrame"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.load(resp)
        return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]


def run_daemon(interval=30):
    print(f"[{dt.datetime.now().isoformat()}] Starting Peak Frame Telemetry Watcher Daemon (poll interval: {interval}s)...")
    token = get_token()
    last_known_count = None
    
    progress_file = ROOT / "profile" / "progress.json"
    if progress_file.exists():
        try:
            snap = json.loads(progress_file.read_text(encoding="utf-8"))
            last_known_count = sum(snap.get("activity", {}).get("daily", {}).values())
        except Exception:
            last_known_count = None

    while True:
        try:
            current_count = fetch_live_count(token)
            if last_known_count is None or current_count != last_known_count:
                print(f"[{dt.datetime.now().isoformat()}] Detected contribution change: {last_known_count} -> {current_count}. Triggering sync...")
                sync_telemetry.sync()
                last_known_count = current_count
        except Exception as e:
            # Silently retry on transient network glitch
            pass
        time.sleep(interval)


if __name__ == "__main__":
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    run_daemon(interval)
