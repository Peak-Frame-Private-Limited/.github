#!/usr/bin/env python3
"""
Telemetry Synchronization Daemon / Script for Peak Frame.
Fetches the latest public contributions from GitHub GraphQL & REST APIs,
regenerates the founder telemetry card, and automatically commits & pushes
to GitHub if any new contributions, commits, or streak updates occurred.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(SCRIPTS_DIR))
import generate_live_dashboard


def run_cmd(cmd, check=True):
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    return subprocess.run(cmd, cwd=str(ROOT), env=env, text=True, capture_output=True, check=check)


def sync():
    print("Fetching latest telemetry and updating dashboards...")
    generate_live_dashboard.main()

    # Check git status for changes in assets or progress
    status_res = run_cmd(["git", "status", "--porcelain"])
    changed_lines = [line.strip() for line in status_res.stdout.splitlines() if line.strip()]

    telemetry_changed = any(
        "profile/assets/" in line or "profile/progress.json" in line for line in changed_lines
    )

    if not telemetry_changed:
        print("No changes detected in telemetry metrics. Dashboard is up to date.")
        return

    print("New contribution or activity detected! Committing and pushing to GitHub...")
    run_cmd(["git", "add", "profile/assets/", "profile/progress.json"])
    run_cmd([
        "git",
        "-c", "user.name=Peak Frame Bot",
        "-c", "user.email=bot@peakframe.in",
        "commit",
        "-m", "chore(telemetry): auto-update live founder activity metrics [skip ci]"
    ])
    
    push_res = run_cmd(["git", "-c", "credential.helper=!gh auth git-credential", "push", "origin", "main"], check=False)
    if push_res.returncode == 0:
        print("Successfully synced and pushed updated telemetry dashboard to GitHub!")
    else:
        print(f"Push failed: {push_res.stderr}")


if __name__ == "__main__":
    sync()
