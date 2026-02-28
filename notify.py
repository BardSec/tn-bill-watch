"""
Notification system for TN education bill changes.

Supports:
  - ConsoleNotifier  – prints a plain-text report to stdout (default/fallback)
  - EmailNotifier    – sends a plain-text email via SMTP
"""

import json
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from monitor import STATUS_LABELS


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _parse_json_field(value):
    """Return parsed list from a JSON string or pass through a list."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    return value or []


def _bill_summary(bill):
    subjects = _parse_json_field(bill.get("subjects", []))
    subject_names = [
        s.get("subject_name", "") if isinstance(s, dict) else str(s)
        for s in subjects
    ]

    sponsors = _parse_json_field(bill.get("sponsors", []))
    sponsor_names = [
        s.get("name", "") if isinstance(s, dict) else str(s)
        for s in sponsors[:4]
    ]

    return {
        "number": bill.get("bill_number", "N/A"),
        "title": bill.get("title", "No title"),
        "status": STATUS_LABELS.get(bill.get("status", 0), "Unknown"),
        "status_date": bill.get("status_date", ""),
        "url": bill.get("url", ""),
        "subjects": ", ".join(filter(None, subject_names)),
        "sponsors": ", ".join(filter(None, sponsor_names)),
    }


def build_report(new_bills, updated_bills):
    """Build a plain-text report string."""
    lines = [
        "Tennessee Education Bill Watch",
        f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 62,
        "",
    ]

    if new_bills:
        lines += [f"NEW BILLS ({len(new_bills)})", "-" * 40]
        for bill in new_bills:
            s = _bill_summary(bill)
            lines += [
                f"  {s['number']}: {s['title']}",
                f"  Status   : {s['status']} ({s['status_date']})",
                f"  Subjects : {s['subjects'] or 'N/A'}",
                f"  Sponsors : {s['sponsors'] or 'N/A'}",
                f"  URL      : {s['url']}",
                "",
            ]

    if updated_bills:
        lines += [f"UPDATED BILLS ({len(updated_bills)})", "-" * 40]
        for bill, event_type, old_val, new_val in updated_bills:
            s = _bill_summary(bill)
            if event_type == "status_change":
                old_label = STATUS_LABELS.get(int(old_val or 0), "?")
                change = f"Status: {old_label} → {s['status']}"
            else:
                change = "Content updated"
            lines += [
                f"  {s['number']}: {s['title']}",
                f"  Change   : {change}",
                f"  URL      : {s['url']}",
                "",
            ]

    if not new_bills and not updated_bills:
        lines.append("No new or updated education bills since last check.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Notifiers
# ---------------------------------------------------------------------------

class ConsoleNotifier:
    """Prints the report to stdout. No configuration required."""

    def send(self, new_bills, updated_bills):
        print(build_report(new_bills, updated_bills))
        return True


class EmailNotifier:
    """Sends the report via SMTP (STARTTLS)."""

    def __init__(self, smtp_host, smtp_port, username, password, from_addr, to_addrs):
        self.smtp_host = smtp_host
        self.smtp_port = int(smtp_port)
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs if isinstance(to_addrs, list) else [to_addrs]

    def send(self, new_bills, updated_bills):
        """Send email. Returns True if sent, False if skipped (nothing to report)."""
        if not new_bills and not updated_bills:
            return False

        body = build_report(new_bills, updated_bills)
        subject = (
            f"TN Education Bill Alert: "
            f"{len(new_bills)} new, {len(updated_bills)} updated"
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(self.to_addrs)
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(self.username, self.password)
            server.sendmail(self.from_addr, self.to_addrs, msg.as_string())

        return True
