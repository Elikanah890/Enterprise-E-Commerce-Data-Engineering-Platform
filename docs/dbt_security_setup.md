# Restricted PostgreSQL access for dbt

## Purpose and safety boundary

dbt reads the existing `silver` schema and writes only to the separate
`dbt_dev_staging`, `dbt_dev_intermediate`, and `dbt_dev_marts` schemas. The
login is not the Python pipeline's `ecommerce_etl` role. It has no role
administration, database creation, database-level object creation, or
write access to Bronze, Silver, Gold, or `public`.

The setup script was executed once on 2026-11-05 with `ON_ERROR_STOP=1`.
The live role, schemas, and privileges were then verified. The script remains a
create-once bootstrap: do not rerun it while the role or schemas exist.

## Read-only audit of the current database

Read-only inspection was performed on `ecommerce_dw` as `ecommerce_etl`
against PostgreSQL 16.15. Observed facts:

- `ecommerce_etl` is a login but not a superuser, database creator, or role
  creator. It has no direct role memberships and has database-level `CREATE`,
  so it must not be used by dbt.
- The database has `bronze`, `silver`, `gold`, and `public`. The first three
  are owned by `ecommerce_etl`; `public` is owned by `pg_database_owner`.
- `PUBLIC` has database `CONNECT` and `TEMP`, but not database `CREATE`.
  `PUBLIC` has `USAGE` on `public`, but no `CREATE` on `public`, `bronze`,
  `silver`, or `gold`.
- No `PUBLIC` object-write grants were found on tables/views in the checked
  schemas.
- No custom default ACL entries and no security-definer functions were found
  in the checked schemas at the time of inspection.
- At audit time, no `dbt_dev_*` schemas or `dbt_dev_user` login existed. They
  were created later from the reviewed bootstrap script.

These are a point-in-time audit. Run the verification queries below again
immediately before and after the administrator setup. Do not infer safety from
schema ACLs alone: database `CREATE`, role memberships, `PUBLIC` grants, object
ACLs, default ACLs, and security-definer functions must also be reviewed.

## Exact access dbt requires

### Database

- `CONNECT` on `ecommerce_dw`.
- No database-level `CREATE`, `CREATEDB`, `CREATEROLE`, superuser, replication,
  bypass-RLS, or owner privileges.
- PostgreSQL currently grants `CONNECT` and `TEMP` to `PUBLIC` by default in
  this database. `TEMP` permits session-temporary objects; it does not grant
  persistent schema creation. The setup does not revoke these database-wide
  defaults because that would affect all database users.

### Sources

- `USAGE` on `silver`.
- `SELECT` on the 9 declared sources: `category_translation`, `customers`,
  `geolocation`, `order_items`, `order_payments`, `order_reviews`, `orders`,
  `products`, and `sellers`. The script also grants `SELECT` on
  `rejected_rows` for lineage, but no dbt model reads it.
- No `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES`, or `TRIGGER`
  privileges in `silver`; no access to Bronze or Gold is needed for dbt models.

### Development output

- `USAGE` and `CREATE` only on the three pre-created dbt schemas.
- dbt-created views/tables are owned by `dbt_dev_user`; the login can then
  replace or drop its own relations during normal dbt rebuilds.
- No database-level `CREATE` is required because an administrator pre-creates
  the schemas.
- Tests run as queries; if dbt failure storage is enabled later, its stored
  failure relations must remain in a development schema owned/creatable by the
  dbt login.

## Administrator setup

1. Review the current grants and role-membership chains with the queries below.
2. Verify no PUBLIC database/schema CREATE or protected-object write privilege
   has appeared. The SQL script deliberately raises an error rather than
   revoking such shared grants.
3. Review [create_dbt_dev_role.sql](../sql/security/create_dbt_dev_role.sql).
   It is intended to be run once by a PostgreSQL administrator, connected to
   `ecommerce_dw`:

   ```bash
   psql -X -v ON_ERROR_STOP=1 -d ecommerce_dw \
     -f sql/security/create_dbt_dev_role.sql
   ```

4. Set the login password out of band. Do not put it in the SQL script,
   command history, project files, or Git. For an interactive `psql` session,
   an administrator can use:

   ```text
   \password dbt_dev_user
   ```

   Alternatively use the organization's approved secret-management workflow.
5. Run the verification queries and inspect role memberships, effective
   privileges, schemas, object ACLs, and default ACLs. Configure the local
   `DBT_POSTGRES_*` environment variables only after the grants pass review.
6. If `dbt_dev_user` already exists, do not rerun this create-once script.
   Audit it and prepare a separately reviewed migration. The script does not
   silently alter or adopt an existing role or schema.

### Script effects

The SQL script creates a `LOGIN` role with `NOSUPERUSER`, `NOCREATEDB`,
`NOCREATEROLE`, `NOINHERIT`, `NOREPLICATION`, and `NOBYPASSRLS`; grants database
`CONNECT`; revokes direct privileges on protected schemas and their current
tables, sequences, and functions; grants read-only access to the declared
Silver sources; creates the three new dbt schemas; grants `USAGE, CREATE`
there; and removes the `PUBLIC EXECUTE` default for functions created by the
dbt role.

The script does not set a password, alter the Python role, modify existing
warehouse objects, revoke global `PUBLIC` privileges, or grant database-level
`CREATE`. The preflight will stop if it detects certain shared PUBLIC write
permissions, so an administrator can assess the broader impact instead of
silently changing access for other users. It also stops if the dedicated role
or any target schema already exists, or if expected Silver sources are missing;
it is intentionally a one-time bootstrap, not an idempotent migration.

## Verification queries

Run these as a PostgreSQL administrator after setup. These are inspection
queries; they do not modify data or privileges.

### Role attributes and direct/transitive memberships

```sql
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolcanlogin,
       rolinherit, rolreplication, rolbypassrls
FROM pg_roles
WHERE rolname = 'dbt_dev_user';

-- Direct memberships. A newly provisioned dbt role should have no rows.
SELECT member.rolname AS member, granted.rolname AS granted_role,
       m.inherit_option, m.set_option, m.admin_option
FROM pg_auth_members AS m
JOIN pg_roles AS member ON member.oid = m.member
JOIN pg_roles AS granted ON granted.oid = m.roleid
WHERE member.rolname = 'dbt_dev_user'
ORDER BY granted.rolname;

-- Roles reachable through memberships, including roles that can be SET ROLE
-- into even when inheritance is disabled. No rows are expected.
WITH RECURSIVE memberships(role_oid, role_name) AS (
    SELECT r.oid, r.rolname
    FROM pg_roles AS r
    WHERE r.rolname = 'dbt_dev_user'
  UNION
    SELECT parent.oid, parent.rolname
    FROM memberships AS child
    JOIN pg_auth_members AS m ON m.member = child.role_oid
    JOIN pg_roles AS parent ON parent.oid = m.roleid
)
SELECT role_name
FROM memberships
WHERE role_name <> 'dbt_dev_user'
ORDER BY role_name;
```

Also inspect memberships granted *to* `dbt_dev_user` even if `NOINHERIT` is
set: a membership can still permit `SET ROLE` unless it is absent. Do not grant
memberships to this login.

### Database and schema access

```sql
SELECT current_database() AS database_name,
       has_database_privilege('dbt_dev_user', current_database(), 'CONNECT')
           AS can_connect,
       has_database_privilege('dbt_dev_user', current_database(), 'CREATE')
           AS can_create_schema,
       has_database_privilege('dbt_dev_user', current_database(), 'TEMP')
           AS can_create_temp_objects;

SELECT n.nspname AS schema_name,
       pg_get_userbyid(n.nspowner) AS schema_owner,
       has_schema_privilege('dbt_dev_user', n.oid, 'USAGE') AS can_use,
       has_schema_privilege('dbt_dev_user', n.oid, 'CREATE') AS can_create
FROM pg_namespace AS n
WHERE n.nspname IN (
    'bronze', 'silver', 'gold', 'public',
    'dbt_dev_staging', 'dbt_dev_intermediate', 'dbt_dev_marts'
)
ORDER BY n.nspname;
```

Expected: `can_connect = true`; `can_create_schema = false`; `can_create` is
true only for the three `dbt_dev_*` schemas. `silver` needs `can_use = true`
and `can_create = false`. `public` may have `can_use = true` through its
existing PUBLIC grant, but must have `can_create = false`; `bronze` and `gold`
must not be writable.

### Silver source read privileges and protected-schema writes

```sql
SELECT sources.table_name,
       has_table_privilege(
           'dbt_dev_user', format('silver.%I', sources.table_name), 'SELECT'
       ) AS can_select
FROM (VALUES
    ('category_translation'), ('customers'), ('geolocation'),
    ('order_items'), ('order_payments'), ('order_reviews'), ('orders'),
    ('products'), ('rejected_rows'), ('sellers')
) AS sources(table_name)
ORDER BY sources.table_name;

SELECT n.nspname AS schema_name, c.relname AS relation_name,
       has_table_privilege('dbt_dev_user', c.oid, 'INSERT') AS can_insert,
       has_table_privilege('dbt_dev_user', c.oid, 'UPDATE') AS can_update,
       has_table_privilege('dbt_dev_user', c.oid, 'DELETE') AS can_delete,
       has_table_privilege('dbt_dev_user', c.oid, 'TRUNCATE') AS can_truncate,
       has_table_privilege('dbt_dev_user', c.oid, 'REFERENCES') AS can_reference,
       has_table_privilege('dbt_dev_user', c.oid, 'TRIGGER') AS can_trigger
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname IN ('bronze', 'silver', 'gold', 'public')
  AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
ORDER BY n.nspname, c.relname;
```

Expected: all ten granted rows are selectable (9 declared sources plus `rejected_rows`); no write privileges are effective
on protected objects. Review inherited memberships and PUBLIC ACLs as well as
direct ACLs when interpreting these results.

### PUBLIC, object grants, security-definer functions, and defaults

```sql
SELECT has_database_privilege('public', current_database(), 'CONNECT')
           AS public_connect,
       has_database_privilege('public', current_database(), 'CREATE')
           AS public_database_create,
       has_database_privilege('public', current_database(), 'TEMP')
           AS public_temp;

SELECT n.nspname AS schema_name,
       has_schema_privilege('public', n.oid, 'USAGE') AS public_usage,
       has_schema_privilege('public', n.oid, 'CREATE') AS public_create
FROM pg_namespace AS n
WHERE n.nspname IN ('bronze', 'silver', 'gold', 'public')
ORDER BY n.nspname;

SELECT n.nspname AS schema_name, c.relname AS relation_name,
       c.relkind,
       has_table_privilege('public', c.oid, 'INSERT') AS public_insert,
       has_table_privilege('public', c.oid, 'UPDATE') AS public_update,
       has_table_privilege('public', c.oid, 'DELETE') AS public_delete,
       has_table_privilege('public', c.oid, 'TRUNCATE') AS public_truncate
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname IN ('bronze', 'silver', 'gold', 'public')
  AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
  AND (
      has_table_privilege('public', c.oid, 'INSERT')
      OR has_table_privilege('public', c.oid, 'UPDATE')
      OR has_table_privilege('public', c.oid, 'DELETE')
      OR has_table_privilege('public', c.oid, 'TRUNCATE')
      OR has_table_privilege('public', c.oid, 'REFERENCES')
      OR has_table_privilege('public', c.oid, 'TRIGGER')
  )
ORDER BY n.nspname, c.relname;

SELECT n.nspname AS schema_name, c.relname AS sequence_name,
       has_sequence_privilege('public', c.oid, 'USAGE') AS public_usage,
       has_sequence_privilege('public', c.oid, 'SELECT') AS public_select,
       has_sequence_privilege('public', c.oid, 'UPDATE') AS public_update
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname IN ('bronze', 'silver', 'gold', 'public')
  AND c.relkind = 'S'
  AND (
      has_sequence_privilege('public', c.oid, 'USAGE')
      OR has_sequence_privilege('public', c.oid, 'SELECT')
      OR has_sequence_privilege('public', c.oid, 'UPDATE')
  )
ORDER BY n.nspname, c.relname;

SELECT n.nspname AS schema_name, p.oid::regprocedure AS function_name,
       pg_get_userbyid(p.proowner) AS owner,
       p.prosecdef AS security_definer,
       has_function_privilege('public', p.oid, 'EXECUTE') AS public_execute,
       has_function_privilege('dbt_dev_user', p.oid, 'EXECUTE')
           AS dbt_user_execute
FROM pg_proc AS p
JOIN pg_namespace AS n ON n.oid = p.pronamespace
WHERE n.nspname IN ('bronze', 'silver', 'gold', 'public')
  AND p.prosecdef
ORDER BY n.nspname, function_name;

SELECT pg_get_userbyid(d.defaclrole) AS creator_role,
       COALESCE(n.nspname, '<all schemas>') AS schema_name,
       d.defaclobjtype AS object_type,
       d.defaclacl AS default_acl
FROM pg_default_acl AS d
LEFT JOIN pg_namespace AS n ON n.oid = d.defaclnamespace
ORDER BY creator_role, schema_name, object_type;
```

Review every PUBLIC write grant and every executable security-definer function
before approving dbt access. Do not revoke PUBLIC privileges globally as a
shortcut: assess the effect on all existing users first. Default ACL changes
apply only to future objects created by the named owner; they do not repair
existing object grants.

## Administrator versus dbt-login operations

| Operation | Required identity |
|---|---|
| Create login role and set its password | PostgreSQL administrator with `CREATEROLE` (or superuser); password set securely out of band |
| Grant database `CONNECT` | Database owner or PostgreSQL administrator |
| Create the three schemas and configure default ACLs | Database/schema administrator with database `CREATE`, source grant authority, and authority to alter defaults for `dbt_dev_user`; a superuser can perform the full script |
| Verify current and effective privileges | PostgreSQL administrator (or an audited read-only security role) |
| Run `dbt debug` and `dbt compile` after configuration | `dbt_dev_user` |
| Build staging/intermediate/marts and run dbt tests | `dbt_dev_user`; persistent writes are confined to its development schemas |
| Run Python ingestion or existing Silver/Gold loaders | Not the dbt login; those are separate pipeline operations and are out of scope |

## Verified live result (2026-11-05)

| Check | Result |
|---|---|
| `dbt_dev_user` exists | Yes |
| Superuser / CREATEDB / CREATEROLE | All false |
| Three dbt schemas exist | Yes |
| Schema owners | `postgres`; dbt relations owned by `dbt_dev_user` |
| `silver` USAGE / CREATE | true / false |
| `bronze` USAGE / CREATE | false / false |
| `gold` USAGE / CREATE | false / false |
| Silver `SELECT` | true |
| Silver write privileges | false |
| Gold `SELECT` | false |
| dbt debug / compile / build / test | Passed |

The bootstrap script remains a one-time operation. For future changes, audit
the live role and ACLs again with the queries below; do not rerun the
create-once script.
