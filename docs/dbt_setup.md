# dbt Core setup and execution

## Current status

**Implemented and live-validated on 2026-11-05.**
`dbt debug`, `dbt compile`, `dbt build`, and `dbt test` all pass against the
isolated PostgreSQL development layer. Gold is not a dbt target and was not
modified.

| Item | Value |
|---|---|
| dbt Core | 1.9.4 |
| dbt-postgres | 1.9.0 |
| Python | 3.11.10 |
| PostgreSQL server | 16.15 |
| dbt login | `dbt_dev_user` |
| Profile target | `dbt_dev` (routing label; literal schema not created) |
| Output schemas | `dbt_dev_staging`, `dbt_dev_intermediate`, `dbt_dev_marts` |
| Models / sources / tests | 33 / 9 / 162 |
| Full build result | 195 passed, 0 warnings, 0 errors |

## What the dbt layer does

The project lives in `dbt_project/ecommerce_dbt`. It reads the existing
`silver` schema as sources and writes only to the three `dbt_dev_*` schemas:

```text
silver.* -> staging views      -> dbt_dev_staging
         -> intermediate views -> dbt_dev_intermediate
         -> dimensions/facts/marts tables -> dbt_dev_marts
```

The profile target schema is `dbt_dev`. The custom `generate_schema_name`
macro rejects any other target and allows only the `staging`, `intermediate`,
and `marts` layer names. It fails closed for unsupported resource types.

## Install

From the project root:

```bash
python3.11 -m venv .venv-dbt
source .venv-dbt/bin/activate
python -m pip install -r requirements-dbt.txt
```

`requirements-dbt.txt` pins `dbt-core==1.9.4` and `dbt-postgres==1.9.0`.
No dbt packages are used. `.venv-dbt` is ignored by Git.

## Restricted PostgreSQL login

The verified role is `dbt_dev_user`. It is a login with:

- `NOSUPERUSER`, `NOCREATEDB`, `NOCREATEROLE`, `NOINHERIT`,
  `NOREPLICATION`, `NOBYPASSRLS`.
- `CONNECT` on `ecommerce_dw`; no database-level `CREATE`.
- `USAGE` on `silver`; `SELECT` on the 9 declared Silver sources.
- No `USAGE` or `CREATE` on `bronze` or `gold`.
- `USAGE` and `CREATE` only on `dbt_dev_staging`,
  `dbt_dev_intermediate`, and `dbt_dev_marts`.
- Ownership of the dbt-created relations in those three schemas.

The administrator setup is in
[`sql/security/create_dbt_dev_role.sql`](../sql/security/create_dbt_dev_role.sql).
It was run once with `ON_ERROR_STOP=1`. Do not rerun a create-once script if
the role or schemas already exist; audit and migrate instead.

The one-time bootstrap password is not in the repository. It must be moved to
the approved secret manager and rotated before shared or production-like use.

## Environment variables

The project never uses the Python pipeline's `POSTGRES_*` credentials. Set
only `DBT_POSTGRES_*` in the dbt shell:

```bash
export DBT_POSTGRES_HOST=localhost
export DBT_POSTGRES_PORT=5432
export DBT_POSTGRES_DB=ecommerce_dw
export DBT_POSTGRES_USER=dbt_dev_user
read -rsp 'dbt_dev_user password: ' DBT_POSTGRES_PASSWORD
printf '\n'
export DBT_POSTGRES_PASSWORD
```

`profiles.yml` contains environment-variable references only and is ignored by
Git. `profiles.yml.example` is the tracked safe template. Unset the variables
when finished:

```bash
unset DBT_POSTGRES_HOST DBT_POSTGRES_PORT DBT_POSTGRES_DB
unset DBT_POSTGRES_USER DBT_POSTGRES_PASSWORD
```

## Commands

From the project root:

```bash
export DBT_PROJECT_DIR="$PWD/dbt_project/ecommerce_dbt"
export DBT_PROFILES_DIR="$PWD/dbt_project/ecommerce_dbt"

.venv-dbt/bin/dbt debug
.venv-dbt/bin/dbt compile
.venv-dbt/bin/dbt test --select 'source:*'
.venv-dbt/bin/dbt build
.venv-dbt/bin/dbt test
```

The project uses `DBT_PROJECT_DIR` and `DBT_PROFILES_DIR` because this dbt
version accepts those paths through the environment more reliably than as
global options before the subcommand.

## Running dbt locally

From the project root, source `scripts/dbt_env.sh` once per terminal to activate the dbt environment and load the project settings, then run `dbt debug` to verify the connection and `dbt build` to build the development models.

## Verified results

| Command | Result |
|---|---|
| `dbt debug` | All checks passed |
| `dbt compile` | Exit 0; 33 models, 162 data tests, 9 sources |
| `dbt test --select 'source:*'` | 39 passed |
| `dbt build` | 195 passed; 19 table models + 14 view models + 162 tests |
| `dbt test` | 162 passed |
| `python3 -m pytest -q` | 27 passed |

Full build runtime was approximately 25 seconds on the local database.

## Safety rules

- Never point the dbt profile at `gold`, `bronze`, `silver`, or `public`.
- Never alias a dbt model to a `gold.*` relation.
- Do not add dbt packages, seeds, snapshots, or incremental models.
- Do not use `--full-refresh`.
- If a future change would write to Bronze, Silver, or Gold, stop and obtain
  explicit approval first.
- Re-run the privilege verification in
  [`dbt_security_setup.md`](./dbt_security_setup.md) after any role or schema
  change.

## Related documents

- [`dbt_architecture.md`](./dbt_architecture.md) — layers, grains, keys, and
  corrected metric definitions.
- [`dbt_models.md`](./dbt_models.md) — model-by-model purpose and tests.
- [`dbt_security_setup.md`](./dbt_security_setup.md) — role/schema verification.
- [`progress/dbt_implementation_report.md`](./progress/dbt_implementation_report.md)
  — live reconciliation against Gold.
