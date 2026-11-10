-- Create the isolated warehouse database.
-- Run as a PostgreSQL superuser, outside a transaction.
-- The runtime role (`ecommerce_etl`) is created separately by the operator.

CREATE DATABASE ecommerce_dw
    WITH ENCODING = 'UTF8'
         LC_COLLATE = 'C'
         LC_CTYPE = 'C'
         TEMPLATE = template0;
