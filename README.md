# TN Bill Watch

A tool for monitoring Tennessee legislative bills related to education. It tracks new bills, status changes, and content updates using the [LegiScan API](https://legiscan.com/legiscan), stores data in SQLite, and sends notifications via email or console. A web dashboard is included for browsing tracked bills.

## Features

- Discovers education-related bills via LegiScan master list and full-text search
- Tracks changes (new bills, status updates, content edits) using content hash comparison
- Notifies via console output or email (SMTP/Gmail)
- Web dashboard with bill statistics, filtering, activity feed, and detail pages
- Docker support with an automated daily scheduler

## Project Structure

```
tn-bill-watch/
├── main.py              # CLI entry point
├── monitor.py           # Core monitoring logic and bill filtering
├── database.py          # SQLite data access layer
├── legiscan.py          # LegiScan API client
├── notify.py            # Console and email notifiers
├── web.py               # Flask web dashboard
├── templates/           # Jinja2 HTML templates
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

## Requirements

- Python 3.12+
- A free [LegiScan API key](https://legiscan.com/legiscan)
- (Optional) An SMTP server for email notifications

## Setup

1. **Clone the repository** and enter the directory.

2. **Create a `.env` file** from the example:
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env`** and set at minimum:
   ```env
   LEGISCAN_API_KEY=your_api_key_here
   DB_PATH=bills.db
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

All configuration is done via environment variables (`.env` file).

| Variable        | Required | Description |
|-----------------|----------|-------------|
| `LEGISCAN_API_KEY` | Yes | Free API key from [legiscan.com](https://legiscan.com/legiscan) |
| `DB_PATH`       | Yes | Path to the SQLite database file (e.g. `bills.db`) |
| `SMTP_HOST`     | No | SMTP server hostname (e.g. `smtp.gmail.com`) |
| `SMTP_PORT`     | No | SMTP port (default: `587`) |
| `SMTP_USER`     | No | SMTP login username |
| `SMTP_PASS`     | No | SMTP password or [Gmail App Password](https://support.google.com/accounts/answer/185833) |
| `EMAIL_FROM`    | No | Sender email address |
| `EMAIL_TO`      | No | Comma-separated list of recipient addresses |

If `SMTP_HOST` is not set, notifications are printed to the console.

## Usage

### CLI

```bash
# Scan for new or updated bills
python main.py check

# Scan and force a notification even if nothing changed
python main.py check --notify

# List all tracked bills
python main.py list

# Print a full status report with recent activity
python main.py report
```

### Web Dashboard

```bash
python web.py
```

Then open [http://localhost:5000](http://localhost:5000) in your browser.

The dashboard shows:
- Summary statistics (total, active, passed, failed/vetoed bills)
- A filterable table of all tracked bills
- A recent activity feed
- Individual bill detail pages with metadata, subjects, sponsors, and change history
- A button to trigger a manual scan from the UI

## Docker

A `docker-compose.yml` is provided with three services:

| Service     | Description |
|-------------|-------------|
| `web`       | Flask dashboard on port 5000 |
| `scheduler` | Runs `check --notify` automatically once per day |
| `app`       | One-shot manual commands (started with `run --rm`) |

```bash
# Start the web dashboard and daily scheduler
docker compose up -d

# Run a one-shot scan
docker compose run --rm app check

# List tracked bills
docker compose run --rm app list

# Print a report
docker compose run --rm app report
```

> **Note:** When running in Docker, set `DB_PATH=/data/bills.db` in your `.env` so the database persists in the mounted volume.

## How It Works

1. **Discovery**: On each scan, the monitor fetches the LegiScan master list for the current Tennessee legislative session and runs several targeted search queries (e.g. "education school", "teacher curriculum", "charter school voucher").
2. **Filtering**: Bills are matched against 38+ education-related keywords and subject categories. Honorary resolutions are excluded automatically.
3. **Change detection**: Each bill's content is hashed. Bills are only fetched in full when the hash changes, minimizing API calls.
4. **Storage**: New bills and change events are saved to SQLite (`bills` and `bill_events` tables).
5. **Notification**: A report is built and delivered via console or email.

## License

This project is unlicensed. See the repository for details.
