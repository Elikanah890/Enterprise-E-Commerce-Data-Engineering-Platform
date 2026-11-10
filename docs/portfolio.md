# Portfolio Kit

Reusable, factual material for a resume, portfolio page, and scholarship
application. Every number below is traceable to the repository or the audited
live run; no estimates are presented as measurements.

---

## 1. One-line pitch

> A production-shaped medallion data warehouse for the Olist e-commerce
> dataset: Airflow-orchestrated PostgreSQL, dbt-tested marts, and quality gates
> that fail loudly.

## 2. Resume bullets

### 2.1 Data Engineering angle

- Built a Bronze/Silver/Gold warehouse in PostgreSQL 16 for **9 sources and
  1,550,922 rows**, with **0 rejected rows** on the audited snapshot.
- Engineered **SHA-256 idempotent Bronze ingestion** with batch audit tables
  (`load_batches`, `rejected_rows`); repeated loads are safe no-ops.
- Orchestrated a **5-task Airflow DAG** with **2 quality gates**, exponential
  backoff retries, `max_active_runs=1`, and a 6-hour timeout.
- Modeled a Gold star schema of **6 dimensions, 4 facts, and 9 analytical
  views**, pre-aggregating satellites to prevent fan-out.

### 2.2 Analytics Engineering angle

- Authored **33 dbt models** (9 staging, 5 intermediate, 19 dimension/fact/mart
  tables) backed by **162 tests** and a **195-check full build** with 0 errors.
- Replaced unstable `ROW_NUMBER()`/serial keys with **deterministic MD5 keys**
  verified stable across repeated builds.
- Corrected three metric families with test-backed definitions: carrier-handoff
  shipping flag (**10,423 vs 23,000 rows**), order-weighted seller late rate
  (**366 sellers changed >1pp**), and order-weighted category review scores
  (**69 of 74 categories changed**).
- Enforced schema isolation with a **fail-closed `generate_schema_name` macro**
  and a least-privilege `dbt_dev_user` role.

### 2.3 Cloud / DevOps angle

- Containerized PostgreSQL 16 and the Python app with **Docker Compose**; ran
  **Airflow 2.9.3 (LocalExecutor)** with a separate metadata database.
- Wrote a **runbook** covering connection setup, DAG triggers, log locations,
  and a 12-row troubleshooting matrix, including the
  `host.docker.internal:5432` failure mode.
- Implemented **least-privilege database roles** and environment-variable-only
  credentials; no secrets are committed.
- Defined reproducibility boundaries explicitly: warehouse build is
  reproducible, Airflow Compose is the next vendoring step.

---

## 3. Scholarship application summary (~150 words)

> This project is an end-to-end data engineering platform for the Olist
> Brazilian e-commerce dataset. I built a medallion warehouse in PostgreSQL
> that lands nine raw CSVs in a text-only Bronze layer with SHA-256 load
> auditing, transforms them into a typed and constrained Silver layer, and
> publishes a Gold star schema with six dimensions, four facts, and nine
> analytical views. Apache Airflow orchestrates five gated tasks with retries,
> while dbt Core maintains an isolated 33-model development branch with 162
> tests. I enforced contracts and quality gates at every boundary: exact row
> counts, key uniqueness, seven relationships, and zero rejected rows. The
> repository documents profiling findings, corrected metrics, and a runbook. It
> demonstrates production habits: idempotent ingestion, reproducible builds,
> deterministic keys, least-privilege roles, and honest trade-offs between full
> rebuilds and incremental loads.

---

## 4. Engineering highlights

1. **Ingestion at scale with proof.** Nine CSVs, 1,550,922 Bronze rows, 9
   successful `load_batches`, 0 rejects, and hash-based skip on repeat runs.
2. **Gated orchestration.** A 5-task DAG with 2 blocking gates, 2 retries with
   exponential backoff, a 6-hour timeout, and single-run concurrency.
3. **dbt depth.** 33 models, 9 sources, 162 tests, and a 195-check build — 100%
   pass — including singular tests for delivery-rate arithmetic, seller
   weighting, payment reconciliation, and shipping-flag semantics.
4. **Warehouse modelling.** 6 dimensions, 4 facts, and 9 views; `fact_orders`
   aggregates items, payments, and reviews independently to prevent fan-out.
5. **Data-quality transparency.** Flags for 1,076 payment mismatches, 775
   itemless orders, 768 unreviewed orders, 610 uncategorised products, 1,382
   delivery anomalies, and 33 geolocation outliers — retained, not hidden.
6. **Corrected, documented metrics.** Carrier-handoff shipping flag (10,423 vs
   23,000), order-weighted seller late rate (366 sellers >1pp, max 37.40pp),
   order-weighted category review scores (69/74, max 0.48 stars), and a
   delivery late rate of 7,827 / 96,476 = 8.11%.

---

## 5. What to show in a portfolio page

| Artifact | Source | Why it matters |
|---|---|---|
| Architecture diagram | `docs/architecture.md` §2 | Shows system thinking |
| DAG graph screenshot | Airflow UI → `ecommerce_pipeline` | Proves orchestration |
| Quality-gate log | `logs/pipeline.log` / Airflow task log | Proves gates run |
| dbt lineage graph | `dbt docs generate` (if enabled) | Shows model DAG |
| Gold query result | `sql/analysis/sales_queries.sql` | Shows business value |
| Data-quality report | `docs/data_quality/data_quality_report.md` | Shows rigour |
| Runbook | `docs/runbook.md` | Shows operability |
| Test output | `pytest -q`, `dbt test` | Shows verification |

## 6. Honest limitations to state

- The dataset is static; scheduling is manual by design.
- Silver and Gold are full rebuilds, not incremental.
- Dashboards and notebooks are placeholders.
- Airflow Compose is not yet vendored into the repository.
- The live environment currently cannot reach the warehouse from the Airflow
  container until PostgreSQL is exposed to the Docker bridge.

Stating these explicitly is stronger than implying a production scale the
project does not yet operate at.
