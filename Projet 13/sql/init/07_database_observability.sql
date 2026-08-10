-- sql/database_observability.sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

CREATE USER "db-o11y" WITH PASSWORD 'Db0b5rv4b1l1ty';
GRANT pg_monitor TO "db-o11y";
GRANT pg_read_all_stats TO "db-o11y";
ALTER ROLE "db-o11y" SET pg_stat_statements.track = 'none';
GRANT pg_read_all_data TO "db-o11y";