#!/usr/bin/env python3
"""
Tennessee Education Bill Monitor
---------------------------------
Usage:
  python main.py check           # Scan for new/updated education bills
  python main.py check --notify  # Force send notification even with no changes
  python main.py list            # List all tracked education bills
  python main.py report          # Full status breakdown

Configuration via .env (copy .env.example → .env and fill in values).
"""

import os
import sys
import argparse
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv()

from database import Database
from monitor import BillMonitor, STATUS_LABELS
from notify import ConsoleNotifier, EmailNotifier


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _get_config():
    api_key = os.environ.get("LEGISCAN_API_KEY", "").strip()
    if not api_key:
        print("Error: LEGISCAN_API_KEY is not set. Add it to your .env file.")
        sys.exit(1)

    return {
        "api_key": api_key,
        "db_path": os.environ.get("DB_PATH", "bills.db"),
        "smtp_host": os.environ.get("SMTP_HOST", ""),
        "smtp_port": os.environ.get("SMTP_PORT", "587"),
        "smtp_user": os.environ.get("SMTP_USER", ""),
        "smtp_pass": os.environ.get("SMTP_PASS", ""),
        "email_from": os.environ.get("EMAIL_FROM", ""),
        "email_to": [
            a.strip()
            for a in os.environ.get("EMAIL_TO", "").split(",")
            if a.strip()
        ],
    }


def _make_notifier(config):
    """Return an EmailNotifier if SMTP is configured, else ConsoleNotifier."""
    if config["smtp_host"] and config["email_from"] and config["email_to"]:
        return EmailNotifier(
            config["smtp_host"],
            config["smtp_port"],
            config["smtp_user"],
            config["smtp_pass"],
            config["email_from"],
            config["email_to"],
        )
    return ConsoleNotifier()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_check(args, config):
    db = Database(config["db_path"])
    monitor = BillMonitor(config["api_key"], db)

    print("Scanning LegiScan for Tennessee education bills…")
    new_bills, updated_bills, total = monitor.scan(verbose=True)

    print(
        f"\nDone. {total} education bills tracked | "
        f"{len(new_bills)} new | {len(updated_bills)} updated"
    )

    if new_bills or updated_bills or args.notify:
        notifier = _make_notifier(config)
        sent = notifier.send(new_bills, updated_bills)
        if sent and isinstance(notifier, __import__("notify").EmailNotifier):
            print(f"Email sent to: {', '.join(config['email_to'])}")


def cmd_list(args, config):
    db = Database(config["db_path"])
    bills = db.get_all_bills()

    if not bills:
        print("No bills tracked yet. Run 'check' first.")
        return

    print(f"Tracked Tennessee Education Bills ({len(bills)} total)\n{'='*62}")
    for b in bills:
        status = STATUS_LABELS.get(b.get("status", 0), "?")
        number = (b.get("bill_number") or "").ljust(12)
        title = (b.get("title") or "")[:55]
        print(f"  {number} [{status:<12}] {title}")


def cmd_report(args, config):
    db = Database(config["db_path"])
    bills = db.get_all_bills()
    events = db.get_recent_events(100)

    print("Tennessee Education Bill Watch — Full Report")
    print("=" * 62)
    print(f"Total bills tracked : {len(bills)}")
    print(f"Recent events       : {len(events)}")

    # Group by status
    by_status = defaultdict(list)
    for b in bills:
        label = STATUS_LABELS.get(b.get("status", 0), "Unknown")
        by_status[label].append(b)

    for status_label in sorted(by_status):
        group = by_status[status_label]
        print(f"\n{status_label} ({len(group)})")
        print("-" * 40)
        for b in group:
            number = (b.get("bill_number") or "").ljust(12)
            title = (b.get("title") or "")[:52]
            print(f"  {number} {title}")

    if events:
        print(f"\nRecent Activity (last {len(events)} events)")
        print("-" * 40)
        for ev in events[:20]:
            event_type = ev.get("event_type", "")
            number = ev.get("bill_number", "")
            title = (ev.get("title") or "")[:40]
            recorded = (ev.get("recorded_at") or "")[:16]
            print(f"  {recorded}  {event_type:<14} {number} {title}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Monitor LegiScan for Tennessee education bills"
    )
    sub = parser.add_subparsers(dest="command")

    check_p = sub.add_parser("check", help="Scan for new/updated education bills")
    check_p.add_argument(
        "--notify",
        action="store_true",
        help="Send a notification even when there are no changes",
    )

    sub.add_parser("list", help="List all tracked education bills")
    sub.add_parser("report", help="Full status breakdown with recent activity")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    config = _get_config()

    if args.command == "check":
        cmd_check(args, config)
    elif args.command == "list":
        cmd_list(args, config)
    elif args.command == "report":
        cmd_report(args, config)


if __name__ == "__main__":
    main()
