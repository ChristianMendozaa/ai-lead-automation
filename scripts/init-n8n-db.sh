#!/bin/sh
# Runs once, only on first container init (empty data dir), via Postgres's
# own /docker-entrypoint-initdb.d convention. n8n gets its own database in
# the same Postgres instance so we don't need a second container.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE n8n OWNER $POSTGRES_USER;
EOSQL
