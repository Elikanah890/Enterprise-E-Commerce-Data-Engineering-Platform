# Olist Dashboards

Two Streamlit dashboards built on the Gold layer of the Olist medallion
warehouse. Both support a **CSV-first mode** for public deployment and a
**PostgreSQL mode** for local analysis.

```text
dashboards/
├── _shared.py                 # engine, loaders, colours, Plotly theme
├── data/                      # CSV exports (280 KB total)
├── business_dashboard/
│   ├── app.py
│   ├── requirements.txt
│   └── .streamlit/config.toml
├── engineering_dashboard/
│   ├── app.py
│   ├── requirements.txt
│   └── .streamlit/config.toml
├── screenshots/
│   ├── business.png           # add manually
│   └── engineering.png        # add manually
└── README.md
```

## Purpose

**Business dashboard** (`dashboards/business_dashboard/app.py`) answers how
revenue is trending, which categories and sellers drive it, how customers
segment by RFM, and whether delivery performance is improving. It reads five
Gold views and exposes date, category, and seller-state filters.

**Engineering dashboard** (`dashboards/engineering_dashboard/app.py`) answers
whether the latest Airflow run succeeded, where task time went, how many rows
landed in Bronze, whether rejects were produced, and which data-quality flags
are largest. It reads the Airflow CLI, the audit tables, and
`vw_data_quality_flags`.

## Screenshots

![Business dashboard](screenshots/business.png)

![Engineering dashboard](screenshots/engineering.png)

Place the captured images at `dashboards/screenshots/business.png` and
`dashboards/screenshots/engineering.png`.

## Run locally

### Business dashboard

```bash
cd dashboards/business_dashboard
pip install -r requirements.txt
streamlit run app.py
```

### Engineering dashboard

```bash
cd dashboards/engineering_dashboard
pip install -r requirements.txt
streamlit run app.py
```

The engineering dashboard calls:

```bash
docker-compose exec -T airflow-scheduler airflow ...
```

Run Streamlit from a shell that can access Docker (for example, after
`newgrp docker`). If `AIRFLOW_DIR` is not `~/projects/airflow`, set it before
starting Streamlit:

```bash
export AIRFLOW_DIR="/path/to/airflow"
```

## Data modes

### CSV mode (default for public deployment)

`_shared.load_csv_or_db()` reads `dashboards/data/<view>.csv` first. All nine
Gold views and three audit tables are exported:

| File | Rows | Size | Note |
|---|---:|---:|---|
| `vw_sales_daily.csv` | 614 | 34 KB | daily sales |
| `vw_delivery_performance.csv` | 25 | 802 B | monthly |
| `vw_customer_rfm.csv` | 5 | 290 B | **aggregated by segment** (94,990 raw rows would exceed 1 MB) |
| `vw_category_performance.csv` | 74 | 4.0 KB | full |
| `vw_seller_performance.csv` | 3,095 | 198 KB | full (under 1 MB) |
| `vw_payment_mix.csv` | 90 | 3.5 KB | full |
| `vw_review_summary.csv` | 23 | 964 B | full |
| `vw_payment_reconciliation.csv` | 8 | 398 B | full |
| `vw_data_quality_flags.csv` | 8 | 215 B | full |
| `bronze_load_batches.csv` | 9 | 1.6 KB | audit |
| `bronze_rejected_rows.csv` | 0 | 78 B | audit |
| `silver_rejected_rows.csv` | 0 | 66 B | audit |

Total: **280 KB**.

The business dashboard handles the aggregated RFM file by summing
`customer_count` for the unique-customer KPI and using the segment rows for the
donut and summary table.

### PostgreSQL mode

Set all five variables; if any is missing, the dashboards stay in CSV mode:

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=ecommerce_dw
export DB_USER=ecommerce_etl
export DB_PASSWORD='...'
```

Never commit real credentials. The dashboards read the environment only.

## Deploy to Streamlit Cloud

1. Push this repository to GitHub.
2. In Streamlit Cloud, create a new app and connect the repository.
3. Set **Main file path** to `dashboards/business_dashboard/app.py`.
4. Deploy. No secrets are required because the app reads CSVs from
   `dashboards/data/`.
5. For the engineering dashboard, use
   `dashboards/engineering_dashboard/app.py`. The Airflow CLI is not available
   on Streamlit Cloud, so run-history sections show `<TBD>` there; the CSV-backed
   quality and audit views still render.

## What each metric means

### Business KPIs

| KPI | Meaning |
|---|---|
| **Total Revenue** | Sum of `gross_value` from `vw_sales_daily` for the selected date range. |
| **Total Orders** | Sum of `orders` from `vw_sales_daily` for the selected date range. |
| **Average Order Value** | Total revenue divided by total orders for the selected range. |
| **Late Delivery Rate** | `late_rate_pct` for the latest month in `vw_delivery_performance`, with a month-over-month delta. |
| **Unique Customers** | Distinct people in `vw_customer_rfm` (or the sum of `customer_count` when the CSV is aggregated). |

### Engineering KPIs

| KPI | Meaning |
|---|---|
| **Bronze Rows Loaded** | Sum of `row_count` for successful rows in `bronze.load_batches`. |
| **Total Rejects** | Row count of `bronze.rejected_rows` plus `silver.rejected_rows`; zero is green, any positive value is red. |
| **Total Quality Flags** | Sum of `rows` across all flags in `vw_data_quality_flags`. |
| **Last Run Duration** | Wall-clock duration of the most recent `ecommerce_pipeline` run from the Airflow CLI. |

## Chart notes

- Revenue is aggregated to calendar month from the daily view; the view itself
  is not ordered, so the app sorts by `order_date` first.
- The category bar chart uses a continuous red→amber→green scale for average
  review score.
- The delivery chart uses a secondary y-axis: late rate on the left, average
  delivery days on the right.
- The engineering "waterfall" is a horizontal duration bar, ordered by task
  start time; task state drives the colour.
- `hash_skipped` is shown as `first load` for every batch: a hash-skipped re-run
  leaves no new `load_batches` row, so skips cannot be counted from that table.
