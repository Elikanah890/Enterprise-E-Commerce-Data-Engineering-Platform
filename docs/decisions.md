# Architecture Decision Records

Short ADR-style notes for the choices a reviewer is most likely to question.
Each record states context, decision, consequences, and what would trigger a
revisit.

---

## ADR-001 — Airflow LocalExecutor for a single-node stack

**Status:** Accepted

**Context.** The platform runs on one workstation with a static dataset and a
single warehouse. The orchestration workload is a five-task linear DAG; there is
no need for distributed workers, and a Celery deployment would add Redis, a
broker, and more containers to operate.

**Decision.** Use Airflow 2.9.3 with `LocalExecutor`, a scheduler, a webserver,
and a dedicated metadata database.

**Consequences.**

- Simple topology and low resource use.
- Task parallelism is bounded by the host; not suitable for many concurrent
  DAGs or heavy per-task compute.
- Scaling out later means switching to CeleryExecutor/KubernetesExecutor and
  externalising task state.

**Revisit when** task runtime or concurrency outgrows one host, or when the DAG
must run on a shared multi-tenant cluster.

---

## ADR-002 — Manual schedule (`schedule=None`) for static data

**Status:** Accepted

**Context.** The source is a fixed Olist snapshot copied into `data/raw/`.
There is no upstream system that produces new rows. A cron schedule would
re-run identical work and create misleading “freshness” history.

**Decision.** Default the DAG to manual runs. Allow an override through
`ECOMMERCE_PIPELINE_SCHEDULE` for a future live source.

**Consequences.**

- Runs are intentional and reproducible.
- No automatic freshness signal; operators must trigger the DAG.
- Adding a live source requires a schedule **and** an arrival sensor or
  watermark, not just a cron string.

**Revisit when** a real source feed exists and freshness becomes a service-level
objective.

---

## ADR-003 — Separate Airflow metadata database

**Status:** Accepted

**Context.** Airflow stores DAG runs, task instances, connections, and logs
metadata in a SQL database. The warehouse `ecommerce_dw` stores analytical data
and is rebuilt by pipeline jobs.

**Decision.** Keep Airflow metadata in its own PostgreSQL container
(`postgres:13`) and volume, separate from the warehouse PostgreSQL 16 instance.

**Consequences.**

- Pipeline rebuilds cannot damage scheduler state.
- Independent backup, upgrade, and retention policies.
- Two database servers to operate; connection configuration must be explicit.
- The Airflow metadata version (13) and warehouse version (16) differ, which is
  acceptable because they are unrelated workloads.

**Revisit when** consolidating onto a managed Airflow service or a shared
PostgreSQL cluster with separate databases and roles.

---

## ADR-004 — Isolate dbt in `dbt_dev_*` schemas

**Status:** Accepted

**Context.** dbt introduces a second transformation path. Letting it write to
`gold` would make two systems compete for the same production objects and would
make rollback ambiguous. dbt also needs different privileges than the Python
loader.

**Decision.** dbt reads the nine Silver tables read-only and writes only to
`dbt_dev_staging`, `dbt_dev_intermediate`, and `dbt_dev_marts`. A
`generate_schema_name` macro fails closed on any target other than `dbt_dev` or
any resource type that is not a model/test. A separate `dbt_dev_user` has no
superuser/createdb/createrole/inherit, no Bronze/Gold access, and only
`USAGE`/`CREATE` on the three dev schemas.

**Consequences.**

- Gold remains the comparison baseline; dbt cannot overwrite it.
- Corrected metrics can be validated side by side before any migration.
- Two warehouse paths coexist until a migration is approved.
- The macro and grants must be maintained if schemas are renamed.

**Revisit when** a corrected dbt model is approved to replace a Gold object,
using a blue/green schema or view swap rather than in-place writes.

---

## ADR-005 — Hash-based Bronze skip (SHA-256)

**Status:** Accepted

**Context.** Re-running the loader must not duplicate rows, and a partial failed
load must be retryable. Timestamps and filenames alone are weak identities.

**Decision.** Hash each source file with SHA-256. Store one row per hash in
`bronze.load_batches`. If the batch status is `success`, skip the file. If it is
`failed` or `started`, clear that batch's partial rows and retry in place.

**Consequences.**

- Idempotent ingestion without a full-table diff.
- Audit trail per file version.
- A byte-identical file is never reloaded; changing one byte creates a new
  batch, which is usually the desired behaviour for a snapshot.
- A retry does not currently clear `bronze.rejected_rows` for the batch, so
  rejected-row counts can duplicate across retries (known gap).
- Hashing large files adds I/O proportional to file size.

**Revisit when** incremental/CDC ingestion is introduced, or when rejected-row
retry semantics need exact-once accounting.

---

## ADR-006 — SQL as the source of truth for warehouse logic

**Status:** Accepted

**Context.** Cleaning, constraints, and star-schema logic can live in Python or
SQL. Python is convenient for exploration; SQL is auditable, portable, and
enforced by PostgreSQL.

**Decision.** Bronze/Silver/Gold transformations live in `sql/`. Python handles
extraction, profiling, validation helpers, and orchestration; the loaders are
thin wrappers that execute SQL atomically.

**Consequences.**

- Constraints and types are enforced by the database, not only by pandas.
- Logic is reviewable and testable with standard SQL tools.
- Python transformation modules still exist for local preview and duplicate
  some cleaning rules; they must not be mistaken for the warehouse path.
- Complex procedural logic is harder to express than in Python.

**Revisit when** the duplicate Python transform path is removed or a
dbt-first migration is approved.

---

## ADR-007 — Full rebuild for Silver and Gold (current)

**Status:** Accepted, with known limits

**Context.** The snapshot is small enough to rebuild in minutes, and full
rebuilds are easier to reason about than merge logic. There is no incremental
watermark yet.

**Decision.** Silver runs `TRUNCATE ... RESTART IDENTITY CASCADE` and reloads
from all Bronze rows. Gold runs `DROP ... CASCADE` and recreates every object.

**Consequences.**

- Reproducible, simple, and deterministic.
- No partial-batch isolation; late-arriving data cannot be applied selectively.
- `CASCADE` destroys external dependents; concurrent readers can see a missing
  object during the rebuild.
- Cost grows with history.

**Revisit when** data volume or freshness requirements make rebuild time
unacceptable. The target is a `_load_id`-aware merge with a staging-table swap
and incremental dbt facts.

---

## ADR-008 — Deterministic MD5 keys in dbt

**Status:** Accepted

**Context.** Gold uses `ROW_NUMBER()` for `dim_category` and Silver's reset
sequence for `review_sk`. Both change across rebuilds, which breaks stable
joins, incremental loads, and cross-run comparisons.

**Decision.** dbt derives dimension and fact keys as MD5 hashes over
length-prefixed natural identifiers (`generate_stable_key`). Natural IDs remain
in the models for lineage.

**Consequences.**

- Keys are stable across rebuilds; verified on consecutive builds.
- Hashes are opaque; debugging requires the natural key columns.
- Composite keys must be ordered consistently to remain stable.
- MD5 is used as a deterministic identifier, not for security.

**Revisit when** a surrogate-key service or a different hashing standard is
adopted.

---

## ADR-009 — Retain and flag anomalies instead of dropping rows

**Status:** Accepted

**Context.** Profiling found 775 orders without items, 1 payment-less order, 768
unreviewed orders, 1,076 payment mismatches, 610 uncategorised products, 1,382
delivery anomalies, and 33 geolocation outliers. Dropping them would silently
change business totals.

**Decision.** Keep suspicious rows in Silver/Gold and expose explicit boolean
flags and quality views. Write only structurally malformed rows to
`rejected_rows`.

**Consequences.**

- Analysts can choose the population for each metric.
- Reconciliation numbers remain explainable.
- Consumers must filter flags deliberately; naive aggregates can be misleading.
- Flag definitions become part of the data contract and need tests.

**Revisit when** a governed quarantine/exception workflow with business
sign-off replaces ad-hoc flags.

---

## ADR-010 — Container path overrides via environment variables

**Status:** Accepted

**Context.** The project's `.env` uses relative paths (`RAW_DIR=./data/raw`),
which resolve correctly when the pipeline runs from the project root on the host,
but resolve to `/opt/airflow/data/raw` (wrong) when Airflow's worker runs with
CWD `/opt/airflow`.

**Decision.** Override the four `*_DIR` variables in the Airflow Compose
environment block. The values must be the **container** mount paths
(`/opt/airflow/project/data...`), because `ECOMMERCE_PROJECT_ROOT` is a
host-side variable and expands to a host path that does not exist inside the
container. The volume mount itself continues to use
`${ECOMMERCE_PROJECT_ROOT}`, so the Compose file stays portable across clones.
Do not change `.env`, which must continue to work for host-side runs.

**Consequences.** Container runs and host runs both resolve paths correctly from
a single source of truth. When the Airflow Compose is vendored into
`infrastructure/airflow/` (audit item C3), the env block moves with it and the
fix is preserved.

---

## ADR-011 — Execution timeouts on DAG tasks

**Status:** Proposed (not yet applied; DAG logic change requires explicit
approval)

**Context.** The earlier 11-hour stuck run was caused by an unreachable
warehouse, but a future hang (for example, a database lock) could still occupy
the single LocalExecutor slot for the full six-hour DAG timeout.

**Decision.** Add
`execution_timeout=timedelta(minutes=15)` to the DAG `default_args`, so each
task fails and retries instead of blocking the queue for hours. Keep the
existing six-hour DAG-run timeout as a backstop.

**Consequences.** A hung task becomes visible within 15 minutes and frees the
worker. The timeout must be longer than the slowest legitimate task
(`silver_rebuild`, ~45 s on this dataset), and must be revisited if data volume
grows. Apply this together with the Compose vendoring so the operational
contract lives in the repository.
