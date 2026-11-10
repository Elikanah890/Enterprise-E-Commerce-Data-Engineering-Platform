\set ON_ERROR_STOP on

-- Run once as a PostgreSQL administrator:
--   psql -X -v ON_ERROR_STOP=1 -d ecommerce_dw -f sql/security/create_dbt_dev_role.sql
--
-- This script deliberately does not set a password. Set it separately with
-- psql's interactive \password dbt_dev_user command or an approved secret
-- manager. Do not put credentials in this file.

DO $preflight$
BEGIN
    IF current_database() <> 'ecommerce_dw' THEN
        RAISE EXCEPTION
            'Connect to ecommerce_dw before running this dbt role setup script';
    END IF;

    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dbt_dev_user') THEN
        RAISE EXCEPTION
            'Role dbt_dev_user already exists; inspect it and prepare a reviewed migration instead';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_namespace
        WHERE nspname IN (
            'dbt_dev_staging', 'dbt_dev_intermediate', 'dbt_dev_marts'
        )
    ) THEN
        RAISE EXCEPTION
            'At least one dbt_dev schema already exists; inspect it before setup';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM (VALUES ('bronze'), ('silver'), ('gold'), ('public'))
            AS required_schemas(schema_name)
        WHERE NOT EXISTS (
            SELECT 1
            FROM pg_namespace AS n
            WHERE n.nspname = required_schemas.schema_name
        )
    ) THEN
        RAISE EXCEPTION
            'A required existing schema is missing; inspect the live database before setup';
    END IF;

    IF has_database_privilege('public', current_database(), 'CREATE') THEN
        RAISE EXCEPTION
            'PUBLIC has database CREATE on ecommerce_dw; review this shared privilege before setup';
    END IF;

    IF has_schema_privilege('public', 'public', 'CREATE') THEN
        RAISE EXCEPTION
            'PUBLIC has CREATE on schema public; review this shared privilege before setup';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_namespace AS n
        WHERE n.nspname IN ('bronze', 'silver', 'gold')
          AND has_schema_privilege('public', n.oid, 'CREATE')
    ) THEN
        RAISE EXCEPTION
            'PUBLIC has CREATE on a warehouse schema; review this shared privilege before setup';
    END IF;

    IF EXISTS (
        SELECT 1
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
    ) THEN
        RAISE EXCEPTION
            'PUBLIC has object-write privileges in a protected schema; review before setup';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname IN ('bronze', 'silver', 'gold', 'public')
          AND c.relkind = 'S'
          AND (
              has_sequence_privilege('public', c.oid, 'USAGE')
              OR has_sequence_privilege('public', c.oid, 'SELECT')
              OR has_sequence_privilege('public', c.oid, 'UPDATE')
          )
    ) THEN
        RAISE EXCEPTION
            'PUBLIC has sequence privileges in a protected schema; review before setup';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc AS p
        JOIN pg_namespace AS n ON n.oid = p.pronamespace
        WHERE n.nspname IN ('bronze', 'silver', 'gold', 'public')
          AND p.prosecdef
          AND has_function_privilege('public', p.oid, 'EXECUTE')
    ) THEN
        RAISE EXCEPTION
            'PUBLIC can execute a security-definer function in a protected schema; review before setup';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM (VALUES
            ('category_translation'), ('customers'), ('geolocation'),
            ('order_items'), ('order_payments'), ('order_reviews'), ('orders'),
            ('products'), ('rejected_rows'), ('sellers')
        ) AS source_tables(table_name)
        WHERE NOT EXISTS (
            SELECT 1
            FROM pg_class AS c
            JOIN pg_namespace AS n ON n.oid = c.relnamespace
            WHERE n.nspname = 'silver'
              AND c.relname = source_tables.table_name
              AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
        )
    ) THEN
        RAISE EXCEPTION
            'One or more declared Silver source tables are missing; review the live source list';
    END IF;
END
$preflight$;

BEGIN;

-- The role has no elevated attributes and is not allowed to inherit another
-- role. No memberships are granted below.
CREATE ROLE dbt_dev_user
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOREPLICATION
    NOBYPASSRLS;

REVOKE ALL PRIVILEGES ON DATABASE ecommerce_dw FROM dbt_dev_user;
GRANT CONNECT ON DATABASE ecommerce_dw TO dbt_dev_user;

-- This login must read only the source relations declared in the dbt project.
-- Revoke any direct grants first, then grant SELECT on those source tables.
REVOKE ALL PRIVILEGES ON SCHEMA bronze, silver, gold, public FROM dbt_dev_user;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA bronze FROM dbt_dev_user;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA silver FROM dbt_dev_user;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA gold FROM dbt_dev_user;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM dbt_dev_user;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA bronze FROM dbt_dev_user;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA silver FROM dbt_dev_user;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA gold FROM dbt_dev_user;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM dbt_dev_user;
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA bronze FROM dbt_dev_user;
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA silver FROM dbt_dev_user;
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA gold FROM dbt_dev_user;
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA public FROM dbt_dev_user;

GRANT USAGE ON SCHEMA silver TO dbt_dev_user;
GRANT SELECT ON TABLE
    silver.category_translation,
    silver.customers,
    silver.geolocation,
    silver.order_items,
    silver.order_payments,
    silver.order_reviews,
    silver.orders,
    silver.products,
    silver.rejected_rows,
    silver.sellers
TO dbt_dev_user;

-- Create new, isolated dbt schemas. Do not reuse gold or other existing schemas.
-- The administrator remains schema owner; relations created by dbt_dev_user
-- are owned by that login and can be replaced/dropped by it during dbt builds.
CREATE SCHEMA dbt_dev_staging;
CREATE SCHEMA dbt_dev_intermediate;
CREATE SCHEMA dbt_dev_marts;

GRANT USAGE, CREATE ON SCHEMA dbt_dev_staging TO dbt_dev_user;
GRANT USAGE, CREATE ON SCHEMA dbt_dev_intermediate TO dbt_dev_user;
GRANT USAGE, CREATE ON SCHEMA dbt_dev_marts TO dbt_dev_user;

-- PostgreSQL grants EXECUTE on newly created functions to PUBLIC by default.
-- dbt models do not require creating functions; remove this default for
-- functions owned by the dbt login. Tables and sequences have no PUBLIC
-- privileges by default, and this login has no default privileges configured
-- to grant them.
ALTER DEFAULT PRIVILEGES FOR ROLE dbt_dev_user
    REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

COMMIT;
