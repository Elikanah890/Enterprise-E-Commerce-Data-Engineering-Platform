# System Architecture

## Purpose

The platform turns nine raw Olist CSVs into a governed analytical warehouse
with reproducible ingestion, cleaning, validation, and business-facing marts.

## Logical architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           Presentation / BI                              │
│  dashboards/business_dashboard   dashboards/engineering_dashboard         │
│  notebooks/03_business_analysis  notebooks/04_geospatial_analysis         │
└───────────────────────────────▲──────────────────────────────────────────┘
                                │ SQL
┌───────────────────────────────┴──────────────────────────────────────────┐
│                         Gold: star schema                                │
│  dim_customers  dim_products  dim_sellers  dim_geolocation  dim_date     │
│  fact_orders    fact_order_items    fact_payments                        │
│  vw_sales_daily vw_delivery_performance vw_customer_rfm ...              │
└───────────────────────────────▲──────────────────────────────────────────┘
                                │ SQL
┌───────────────────────────────┴──────────────────────────────────────────┐
│                    Silver: typed + constrained                           │
│  PK/FK, CHAR(5) zip, review unique (review_id, order_id),               │
│  geolocation deduplicated + filtered to Brazil                          │
└───────────────────────────────▲──────────────────────────────────────────┘
                                │ SQL / Python
┌───────────────────────────────┴──────────────────────────────────────────┐
│                     Bronze: raw text landing                             │
│  one table per CSV, every column TEXT, load audit columns                │
└───────────────────────────────▲──────────────────────────────────────────┘
                                │ copy / read
┌───────────────────────────────┴──────────────────────────────────────────┐
│                     Raw: data/raw/*.csv                                  │
│  UTF-8 CSVs, quoted fields, embedded newlines in reviews                │
└──────────────────────────────────────────────────────────────────────────┘
```

## Components

| Layer | Path | Responsibility |
|---|---|---|
| Raw | `data/raw/` | Immutable source CSVs copied from the original dataset |
| Ingestion | `src/ecommerce_pipeline/ingestion/` | Read CSVs as text, preserve leading zeros, strip BOM |
| Profiling | `src/ecommerce_pipeline/profiling/` | Inventory, schema, missing values, duplicates, relationships |
| Transformation | `src/ecommerce_pipeline/transformation/` | Type casting and normalisation rules |
| Validation | `src/ecommerce_pipeline/validation/` | PK, FK, null, duplicate, and business-rule checks |
| Loading | `src/ecommerce_pipeline/loading/` | PostgreSQL engine, DDL execution, bronze/silver/gold loads |
| SQL | `sql/` | Source of truth for DDL, cleaning, star schema, and analysis |
| Analytics | `src/ecommerce_pipeline/analytics/` | Reusable analysis functions over gold views |
| Orchestration | `orchestration/airflow/` | Daily scheduling |
| Infrastructure | `infrastructure/` | Docker, PostgreSQL, monitoring placeholders |
| dbt | `dbt_project/` | Optional transformation layer on top of bronze/silver |

## Technology choices

| Concern | Choice | Reason |
|---|---|---|
| File processing | pandas | Small-to-medium CSVs; strong text handling |
| Warehouse | PostgreSQL 16 | Reliable, free, supports window functions and `percentile_cont` |
| DB access | SQLAlchemy 2 + psycopg2 | Standard Python integration |
| Transformations | SQL-first | Auditable and portable; Python handles extraction |
| Orchestration | Airflow | Standard scheduling and retries |
| Optional modelling | dbt | Staging/intermediate/marts layering |
| Containers | Docker Compose | Reproducible local environment |

## Key architectural decisions

1. **SQL is the source of truth for warehouse logic.** Python reads, profiles,
   validates, and orchestrates; the cleaning and star-schema definitions live in
   `sql/`.
2. **Bronze is all text.** This preserves leading zeros and malformed values so
   that every cleaning decision is inspectable.
3. **Silver is typed and constrained.** PK/FK constraints catch relationship
   breakage early.
4. **Gold pre-aggregates before joining.** `fact_orders` aggregates items,
   payments, and reviews separately to prevent fan-out.
5. **Geolocation is aggregated to one row per zip.** The raw file is
   point-level and would multiply fact rows if joined directly.

## Deployment topology

- **Local:** Docker Compose with PostgreSQL and the Python app.
- **Scheduled:** Airflow DAG `ecommerce_pipeline` runs inventory, ingest,
  transform, validate, and load daily.
- **BI:** Dashboards read only gold views; they never touch bronze or silver.
