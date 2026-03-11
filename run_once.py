#!/usr/bin/env python3
"""
Looping website checker for GitHub Actions.
Checks all enabled websites every CHECK_INTERVAL minutes,
running for up to MAX_RUNTIME_MINUTES (default 330 = 5.5 hours)
to stay under GitHub Actions' 6-hour job limit.
"""

import os
import sys
import time
from datetime import datetime, timedelta
from tracker import CONFIG, check_website, send_telegram_alert

# How long to keep looping (minutes). Default 330 = 5h30m (under 6h limit).
MAX_RUNTIME_MINUTES = int(os.getenv("MAX_RUNTIME_MINUTES", "330"))
# Pause between full sweeps (minutes). Default 10.
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "10"))


def run_sweep(websites):
    """Check every website once. Returns list of error strings."""
    errors = []
    for website in websites:
        try:
            check_website(website)
        except Exception as e:
            errors.append(f"{website['name']}: {e}")
            print(f"[-] Error checking {website['name']}: {e}")
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
