#!/usr/bin/env bash
# APIとWorkerがsuperuserで接続しないよう、login roleを分けて作る（ADR-0014）。
#
# このscriptはdata directoryが空のときの初期化でだけ実行される。既存volumeへ後から
# roleを足す場合は、`docker compose exec db psql` から同じSQLを実行する。
#
# object権限はまだ与えない。対象schemaが無く、role別のgrantは`CP-0022`で決めるため、
# ここで作るのは「superuserではない接続主体」までとする。
set -euo pipefail

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --no-psqlrc --quiet \
	--set ON_ERROR_STOP=1 \
	--set api_password="$CARD_PULSE_API_DB_PASSWORD" \
	--set worker_password="$CARD_PULSE_WORKER_DB_PASSWORD" <<'SQL'
CREATE ROLE card_pulse_api WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'api_password';
CREATE ROLE card_pulse_worker WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'worker_password';
SQL
