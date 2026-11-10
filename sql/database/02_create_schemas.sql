-- Logical schemas for the layered warehouse.

CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS analytics;

COMMENT ON SCHEMA bronze IS 'Raw text landing zone; one table per source CSV.';
COMMENT ON SCHEMA silver IS 'Typed, cleaned, constrained tables.';
COMMENT ON SCHEMA gold IS 'Star-schema dimensions, facts, and analytical views.';
COMMENT ON SCHEMA analytics IS 'Ad-hoc analytical queries and experiments.';
