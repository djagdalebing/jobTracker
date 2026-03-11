#!/usr/bin/env python3
"""
Looping website checker for GitHub Actions.
Checks all enabled websites every CHECK_INTERVAL minutes,
running for up to MAX_RUNTIME_MINUTES (default 330 = 5.5 hours)
to stay under GitHub Actions' 6-hour job limit.
Commits data/ to git after every sweep so progress is never lost.
"""

import os
import sys
import time
import subprocess
import threading
from datetime import datetime, timedelta
from tracker import CONFIG, check_website, send_telegram_alert

# How long to keep looping (minutes). Default 330 = 5h30m (under 6h limit).
MAX_RUNTIME_MINUTES = int(os.getenv("MAX_RUNTIME_MINUTES", "330"))
# Pause between full sweeps (minutes). Default 10.
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "10"))
# Max time (seconds) for a single website check before it's killed.
PER_SITE_TIMEOUT = int(os.getenv("PER_SITE_TIMEOUT", "180"))  # 3 minutes


def git_commit_and_push():
    """Commit data/ changes and push, handling conflicts gracefully."""
    try:
        subprocess.run(["git", "add", "data/"], check=False)
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], capture_output=True
        )
        if result.returncode == 0:
            print("[git] No data changes to commit.")
            return
        subprocess.run(
            ["git", "commit", "-m", "chore: update tracker data [skip ci]"],
            check=True,
        )
        # Pull with rebase to avoid conflicts from other runs
        subprocess.run(
            ["git", "pull", "--rebase", "origin", "main"],
            check=True,
        )
        subprocess.run(["git", "push"], check=True)
        print("[git] ✅ Data committed and pushed.")
    except subprocess.CalledProcessError as e:
        print(f"[git] ⚠️ Push failed (will retry next sweep): {e}")


def check_website_with_timeout(website, timeout=PER_SITE_TIMEOUT):
    """Run check_website in a thread with a timeout. Returns error string or None."""
    result = [None]  # mutable container for thread result

    def _target():
        try:
            check_website(website)
        except Exception as e:
            result[0] = str(e)

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout=timeout)

    if t.is_alive():
        msg = f"{website['name']}: timed out after {timeout}s"
        print(f"[⏰] {msg} — skipping.")
        return msg
    if result[0]:
        return f"{website['name']}: {result[0]}"
    return None


def run_sweep(websites):
    """Check every website once. Returns list of error strings."""
    errors = []
    for website in websites:
        err = check_website_with_timeout(website)
        if err:
            errors.append(err)
            print(f"[-] {err}")
    return errors


def main():
    print("🚀 Starting Website Tracker (looping mode)...")
    print(f"⏰ Start time : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏳ Max runtime: {MAX_RUNTIME_MINUTES} minutes")
    print(f"🔄 Interval  : {CHECK_INTERVAL_MINUTES} minutes")
    print("-" * 50)

    websites = [w for w in CONFIG.get('websites', []) if w.get('enabled', True)]

    if not websites:
        print("❌ No enabled websites found in configuration!")
        sys.exit(1)

    print(f"\n📋 Monitoring {len(websites)} website(s):")
    for website in websites:
        print(f"  • {website['name']}")

    os.makedirs('data', exist_ok=True)

    deadline = datetime.now() + timedelta(minutes=MAX_RUNTIME_MINUTES)
    sweep_count = 0

    while datetime.now() < deadline:
        sweep_count += 1
        print(f"\n{'='*50}")
        print(f"🔄 Sweep #{sweep_count} — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")

        errors = run_sweep(websites)

        if errors:
            print(f"⚠️  {len(errors)} error(s) in sweep #{sweep_count}")

        # Commit & push data after every sweep
        git_commit_and_push()

        remaining = (deadline - datetime.now()).total_seconds()
        sleep_seconds = CHECK_INTERVAL_MINUTES * 60

        if remaining <= sleep_seconds:
            print(f"\n⏰ Less than {CHECK_INTERVAL_MINUTES} min remaining — exiting.")
            break

        print(f"\n💤 Sleeping {CHECK_INTERVAL_MINUTES} minutes until next sweep...")
        time.sleep(sleep_seconds)

    print(f"\n✅ Done. Completed {sweep_count} sweep(s).")


if __name__ == "__main__":
    main()
