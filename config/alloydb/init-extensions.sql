-- Runs once, on an empty data directory, via /docker-entrypoint-initdb.d/.
-- pg_stat_statements is preloaded in postgresql.conf; the extension still
-- has to be created before the pg_stat_statements view exists.
-- On a pre-existing alloydb_data volume this file does NOT run - create the
-- extension by hand (see the guide, Backup & Observability sections).
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
