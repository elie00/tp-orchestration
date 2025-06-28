-- ==========================================
-- SCRIPT D'INITIALISATION POSTGRESQL
-- Configuration de la base de données MLflow
-- ==========================================

-- Création de la base de données si elle n'existe pas
SELECT 'CREATE DATABASE mlflow'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mlflow')\gexec

-- Configuration de l'utilisateur mlflow
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'mlflow') THEN

      CREATE ROLE mlflow LOGIN PASSWORD 'mlflow123';
   END IF;
END
$do$;

-- Attribution des privilèges
GRANT ALL PRIVILEGES ON DATABASE mlflow TO mlflow;

-- Connexion à la base mlflow
\c mlflow

-- Création du schéma et configuration des permissions
CREATE SCHEMA IF NOT EXISTS mlflow_schema;
GRANT ALL ON SCHEMA mlflow_schema TO mlflow;
GRANT ALL ON ALL TABLES IN SCHEMA mlflow_schema TO mlflow;
GRANT ALL ON ALL SEQUENCES IN SCHEMA mlflow_schema TO mlflow;

-- Configuration pour les futures tables
ALTER DEFAULT PRIVILEGES IN SCHEMA mlflow_schema GRANT ALL ON TABLES TO mlflow;
ALTER DEFAULT PRIVILEGES IN SCHEMA mlflow_schema GRANT ALL ON SEQUENCES TO mlflow;

-- Extensions utiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Configuration pour les performances
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Message de confirmation
\echo 'Base de données MLflow initialisée avec succès!'
