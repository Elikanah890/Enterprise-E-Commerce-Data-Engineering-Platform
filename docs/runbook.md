# Runbook

Operational guide for bringing the platform up, running the DAG, reading logs,
diagnosing failures, and tearing down cleanly. Commands assume the project root:

```bash
cd enterprise-ecommerce-data-platform
```

> **Secrets:** never paste real passwords into commands, logs, issues, or
> screenshots. Use `.env` (mode 600) or a secret manager. The examples below use
> placeholders.

## 1. Prerequisites

| Requirement | Check |
|---|---|
| Python 3.11+ | `python3 --version` |
| Docker + Compose | `docker --version && docker compose version` |
| PostgreSQL client | `psql --version` |
| Free ports | `5432` (warehouse), `8080` (Airflow UI) |
| Raw data | `ls data/raw/*.csv` returns 9 files |

## 2. Bring up the warehouse

The repository ships a Postgres 16 + app Compose file:

```bash
cd infrastructure/docker
cp ../../.env.example ../../.env      # then edit values; never commit .env
docker compose up -d postgres
docker compose ps
```

The `postgres` service mounts `sql/database/` into
`/docker-entrypoint-initdb.d`, so the database and schemas are created on the
first run of an empty volume. For an existing host PostgreSQL, skip Compose and
create the database/schemas manually:

```bash
psql -U postgres -f sql/database/01_create_database.sql
psql -U ecommerce_etl -d ecommerce_dw -f sql/database/02_create_schemas.sql
psql -U ecommerce_etl -d ecommerce_dw -f sql/bronze/create_bronze_tables.sql
psql -U ecommerce_etl -d ecommerce_dw -f sql/silver/create_silver_tables.sql
```

Verify:

```bash
pg_isready -h localhost -p 5432
psql -U ecommerce_etl -d ecommerce_dw -c "select schema_name from information_schema.schemata where schema_name in ('bronze','silver','gold');"
```

## 3. Bring up Airflow

### 3.1 Current local setup

The running Airflow stack is an **external** Compose project. On this
workstation it lives at `~/projects/airflow` and mounts this repository at
`/opt/airflow/project`; the DAG is symlinked into `/opt/airflow/dags`.

```bash
cd ~/projects/airflow
docker compose up -d
docker compose ps
```

Open the UI at <http://localhost:8080>. The scheduler and webserver containers
share the repository bind mount, so DAG edits are picked up automatically.

### 3.2 Target setup (not yet in the repo)

To make this repository self-contained, vendor the Airflow Compose project into
`infrastructure/airflow/`, mount `..` at `/opt/airflow/project`, and symlink or
copy `orchestration/airflow/dags/ecommerce_pipeline_dag.py` into
`/opt/airflow/dags`. See `docs/architecture.md` §9.

## 4. Configure the warehouse connection

The DAG reads connection id `ecommerce_postgres` by default (override with
`ECOMMERCE_AIRFLOW_CONN_ID`).

Create it once in the UI (**Admin → Connections**) or via CLI inside the
scheduler container:

```bash
docker exec -it airflow_airflow-scheduler_1 airflow connections add ecommerce_postgres \
  --conn-type postgres \
  --conn-host host.docker.internal \
  --conn-schema ecommerce_dw \
  --conn-login ecommerce_etl \
  --conn-password 'REPLACE_WITH_SECRET' \
  --conn-port 5432
```

Host choice depends on where PostgreSQL runs:

| Warehouse location | `--conn-host` |
|---|---|
| Host PostgreSQL (current) | `host.docker.internal` |
| Postgres in the same Compose network | `postgres` (service name) |
| Remote managed Postgres | the hostname/FQDN |

Test the connection:

```bash
docker exec -it airflow_airflow-scheduler_1 airflow connections test ecommerce_postgres
```

> If `host.docker.internal` resolves but the port is refused, PostgreSQL is
> probably listening only on `127.0.0.1`. See §7.

## 5. Trigger the DAG

Via UI: open `ecommerce_pipeline` → **Trigger DAG**.

Via CLI:

```bash
docker exec -it airflow_airflow-scheduler_1 airflow dags trigger ecommerce_pipeline
docker exec -it airflow_airflow-scheduler_1 airflow dags list-runs -d ecommerce_pipeline
```

Check task states:

```bash
RUN_ID='manual__YYYY-MM-DDTHH:MM:SS+00:00'
docker exec -it airflow_airflow-scheduler_1 \
  airflow tasks states-for-dag-run ecommerce_pipeline "$RUN_ID"
```

Expected task order:

```text
bronze_load → bronze_quality_gate → silver_rebuild →
silver_quality_gate → gold_build
```

## 6. Read logs

| Source | Command / location |
|---|---|
| Scheduler | `docker compose -f ~/projects/airflow/docker-compose.yaml logs -f airflow-scheduler` |
| Webserver | `docker compose -f ~/projects/airflow/docker-compose.yaml logs -f airflow-webserver` |
| Task log (bind mount) | `~/projects/airflow/logs/dag_id=ecommerce_pipeline/run_id=<run_id>/task_id=<task>/attempt=1.log` |
| Pipeline file log | `logs/pipeline.log` (inside the project) |
| Airflow UI | Grid → task → **Logs** |

Follow a task log:

```bash
tail -f "$HOME/projects/airflow/logs/dag_id=ecommerce_pipeline/run_id=<run_id>/task_id=bronze_load/attempt=1.log"
```

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `connection to server at "host.docker.internal" ... port 5432 failed: Connection refused` | Host PostgreSQL listens only on `127.0.0.1`; Docker bridge cannot reach it | Bind PostgreSQL to `0.0.0.0` (or the Docker bridge), add a `pg_hba.conf` rule, or run Postgres in Compose; then retest the connection |
| `password authentication failed` | Wrong `ecommerce_postgres` credentials | Update the Airflow connection; do not log the password |
| `bronze_load` skips a file | Same SHA-256 already loaded successfully | Expected idempotency; use a new file version to reload |
| `bronze_quality_gate` row-count mismatch | Source file changed or partial load | Inspect `bronze.load_batches`; compare with `settings.EXPECTED_ROWS` |
| `bronze_quality_gate` reports rejected rows | Malformed CSV rows | Inspect `bronze.rejected_rows` for line numbers and reasons |
| `silver_quality_gate` duplicate keys | Bad source data or logic change | Inspect the named table/columns in the failure message |
| `silver_quality_gate` orphan rows | Missing parent row (customer/product/seller/order) | Check Silver load order and rejected rows |
| `gold_build` fails on a view | Upstream Silver object missing or renamed | Re-run Silver; verify the 9 Silver tables exist |
| DAG never starts | DAG import error or paused DAG | `airflow dags list`; unpause in the UI; inspect scheduler logs |
| `ModuleNotFoundError: ecommerce_pipeline` | Project not on `PYTHONPATH` | Ensure the repo is mounted at `/opt/airflow/project` and the DAG adds `src/` |
| `psycopg2` missing in Airflow | Provider/driver not installed in the image | Install `psycopg2-binary` in the Airflow image |
| dbt cannot connect | `DBT_POSTGRES_*` unset or role missing | Export variables; run `dbt debug`; verify `dbt_dev_user` grants |
| dbt refuses schema | Target is not `dbt_dev` | Set `schema: dbt_dev` in the profile; the macro fails closed |

### 7.1 Verify the current failure mode

```bash
pg_isready -h localhost -p 5432        # host
pg_isready -h 172.17.0.1 -p 5432       # Docker bridge
ss -ltn | grep ':5432'
```

If the host accepts but the bridge does not, the Airflow connection cannot work
until PostgreSQL is exposed or the warehouse is containerised.

### 7.2 `docker-compose` v1.29.2 recreate workaround

On newer Docker engines, `docker-compose up --force-recreate` can fail with
`KeyError: 'ContainerConfig'`. Recreate the ephemeral services by bringing the
project down **without deleting volumes**, then up:

```bash
cd ~/projects/airflow
docker compose down
docker compose up -d
```

`down` without `-v` preserves the Airflow metadata volume.

### 7.3 DAG is paused after a metadata reset

After deleting DAG records or recreating the metadata database, the scheduler
may show `is_paused = None` and queue runs without executing them. Unpause it:

```bash
docker-compose exec -T airflow-scheduler airflow dags unpause ecommerce_pipeline
```

### 7.4 Container path overrides

The Airflow Compose file must set the four data-path variables to the
**container** mount path, not the host path:

```yaml
DATA_DIR: /opt/airflow/project/data
RAW_DIR: /opt/airflow/project/data/raw
PROCESSED_DIR: /opt/airflow/project/data/processed
WAREHOUSE_DIR: /opt/airflow/project/data/warehouse
```

Using `${ECOMMERCE_PROJECT_ROOT}` in these values expands to the host path and
fails inside the container. See `docs/decisions.md` ADR-010.

## 8. Run the pipeline without Airflow

Useful for local debugging and CI:

```bash
python scripts/run_pipeline.py --stage inventory
python scripts/run_pipeline.py --stage validate
python scripts/run_pipeline.py --stage load
```

`load` executes schemas → Bronze → Silver → Gold. It is idempotent for Bronze
(hash skip) but **rebuilds** Silver and Gold.

## 9. Run dbt

```bash
export DBT_PROJECT_DIR="$PWD/dbt_project/ecommerce_dbt"
export DBT_PROFILES_DIR="$PWD/dbt_project/ecommerce_dbt"
export DBT_POSTGRES_HOST=localhost
export DBT_POSTGRES_PORT=5432
export DBT_POSTGRES_DB=ecommerce_dw
export DBT_POSTGRES_USER=dbt_dev_user
read -rsp 'dbt password: ' DBT_POSTGRES_PASSWORD; printf '\n'; export DBT_POSTGRES_PASSWORD

.venv-dbt/bin/dbt debug
.venv-dbt/bin/dbt build
.venv-dbt/bin/dbt test
```

Rules:

- Never point dbt at `gold`.
- Never use `--full-refresh` casually; the project is dev-only.
- Never commit `profiles.yml` or dbt credentials.

## 10. Teardown

Stop containers without deleting data:

```bash
cd infrastructure/docker
docker compose down

cd ~/projects/airflow
docker compose down
```

Delete volumes (destroys warehouse and Airflow history — use with care):

```bash
docker compose down -v
```

Do not delete `data/raw/`; it is the only copy of the source snapshot in the
project tree.

## 11. Safety rules

1. Do not run `load` against a shared database without confirming the target.
2. Do not edit `profiles.yml` in place; use environment variables.
3. Do not commit `.env`, `*.key`, `*.pem`, dumps, logs, or credentials.
4. Do not add `--full-refresh` to dbt runs without a reviewed plan.
5. Trigger the DAG manually until a live source and schedule are approved.
