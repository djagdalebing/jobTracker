#!/usr/bin/env python3
"""
Single-pass website checker for GitHub Actions.
Checks all enabled websites once and exits.
"""

import os
import sys
from datetime import datetime
from tracker import CONFIG, check_website, send_telegram_alert


def main():
    print("🚀 Starting Website Tracker (single-pass mode)...")
    print(f"⏰ Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)

    websites = [w for w in CONFIG.get('websites', []) if w.get('enabled', True)]

    if not websites:
        print("❌ No enabled websites found in configuration!")
        sys.exit(1)

    print(f"\n📋 Checking {len(websites)} website(s):")
    for website in websites:
        print(f"  • {website['name']}")

    os.makedirs('data', exist_ok=True)

    errors = []
    for website in websites:
        try:
            check_website(website)
        except Exception as e:
            errors.append(f"{website['name']}: {e}")
            print(f"[-] Error checking {website['name']}: {e}")

    print("\n" + "-" * 50)
    print(f"✅ Finished checking {len(websites)} website(s).")
    if errors:
        print(f"⚠️  {len(errors)} error(s) occurred:")
        for err in errors:
            print(f"  • {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
