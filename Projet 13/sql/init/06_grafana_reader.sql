-- sql/grafana_reader.sql
CREATE ROLE grafana_reader LOGIN PASSWORD 'Gr4f4n4r34d3r!';
GRANT CONNECT ON DATABASE pulsevent TO grafana_reader;
GRANT USAGE ON SCHEMA public TO grafana_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO grafana_reader;