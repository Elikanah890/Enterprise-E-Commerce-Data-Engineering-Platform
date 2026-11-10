# Project Roadmap

## Phase 0 — Foundation (complete)

- [x] Create project structure.
- [x] Copy nine raw CSVs into `data/raw/`.
- [x] Add settings, logging, and CSV reader with BOM/zero handling.
- [x] Add profiling and quality report.
- [x] Add SQL DDL for bronze, silver, and gold.
- [x] Add Docker, Airflow, dbt, and test scaffolding.

## Phase 1 — Ingestion and quality (next)

- [ ] Implement the full bronze loader with `COPY` for speed.
- [ ] Add automated data-quality gates to CI.
- [ ] Persist profiling output as JSON/Parquet.
- [ ] Add a quarantine table for rejected rows.
- [ ] Write integration tests against a disposable PostgreSQL container.

## Phase 2 — Warehouse hardening

- [x] Materialise the star schema with dbt models in isolated `dbt_dev_*` schemas.
- [ ] Add incremental loads and `_loaded_at` watermarking.
- [x] Add deterministic surrogate keys for all dbt dimensions and facts.
- [x] Add a calendar date dimension (2016-01-01 to 2019-12-31).
- [x] Add dbt schema tests (unique, not null, relationships, accepted values).

The dbt development layer is implemented and validated: 33 models, 9 sources,
162 tests, and a 195-check full build. Gold remains unchanged. See
`docs/progress/dbt_implementation_report.md`.

## Phase 3 — Analytics and BI

- [ ] Build the business dashboard (sales, delivery, categories, sellers).
- [ ] Build the engineering dashboard (row counts, freshness, quality gates).
- [ ] Add cohort retention and CLV analyses.
- [ ] Add geospatial distance features.
- [ ] Add text/sentiment features from reviews.

## Phase 4 — Orchestration and observability

- [ ] Run the Airflow DAG in a container.
- [ ] Add retries, alerts, and SLA monitoring.
- [ ] Add Prometheus metrics and Grafana dashboards.
- [ ] Add lineage documentation.
- [ ] Add cost and runtime tracking.

## Phase 5 — Advanced modelling

- [ ] Late-delivery prediction (order features only).
- [ ] Review-score prediction (post-delivery features).
- [ ] Customer segmentation and churn.
- [ ] Seller risk scoring.
- [ ] Demand forecasting by category/state.

## Success metrics

| Area | Metric | Target |
|---|---|---|
| Ingestion | All 9 files load with expected row counts | 100% |
| Quality | FK orphans in fact tables | 0 |
| Quality | Duplicate keys in declared PKs | 0 |
| Warehouse | Gold build runtime | < 5 min |
| Analytics | Dashboard freshness | daily |
| Modelling | Late-delivery AUC | baseline + documented lift |
