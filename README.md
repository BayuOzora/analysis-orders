# Detailed Analytics Dashboard (Python)

This dashboard analyzes CSV backup data with richer insights than the standard POS report.

## Features

- Date-range filtering
- Payment-method filtering
- Status filtering
- Order-type filtering
- Paid-only toggle
- KPI cards (revenue, transactions, items sold, average ticket, unique customers)
- Jam rame (hourly peak analysis)
- Sales trend by day
- Payment mix analysis
- Weekday-hour heatmap
- Top selling menu by quantity and revenue
- Downloadable filtered CSV outputs

## Files

- `dashboard.py`: Streamlit analytics app
- `orders_rows.csv`: orders export
- `order_items_rows.csv`: order items export

## Setup

```bash
cd /Users/rickydarmawan/Documents/Code/exa-warkop/data-backup
/opt/homebrew/bin/python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Run

```bash
cd /Users/rickydarmawan/Documents/Code/exa-warkop/data-backup
.venv/bin/python -m streamlit run dashboard.py
```

Streamlit will show a local URL (usually `http://localhost:8501`).

## Deploy

### Option A: Render (recommended)

This folder includes production files:

- `Dockerfile`
- `.dockerignore`
- `render.yaml`

Steps:

1. Push this project to your GitHub repo.
2. In Render, create a new Web Service from that repo.
3. Set Root Directory to `data-backup`.
4. Render auto-detects `render.yaml` + Docker setup.
5. Deploy and open the generated Render URL.

Notes:

- `orders_rows.csv` and `order_items_rows.csv` must exist in `data-backup` in your deployed repo.
- App binds to `0.0.0.0` and uses Render `PORT` automatically.

### Option B: Streamlit Community Cloud

1. Push this `data-backup` folder to GitHub.
2. Open Streamlit Community Cloud and create a new app.
3. Set:
	- Main file path: `data-backup/dashboard.py`
	- Python dependencies: `data-backup/requirements.txt`
4. Deploy.
