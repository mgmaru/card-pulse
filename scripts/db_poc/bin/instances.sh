#!/usr/bin/env bash
# Manage the local PostgreSQL 18.6 and MariaDB 12.3.3 instances used by the
# CP-0009 PoC. Both run on non-default ports with dedicated data directories
# under var/db-poc so they never touch other local databases.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
POC_ROOT="${REPO_ROOT}/var/db-poc"
PG_HOME="/opt/homebrew/opt/postgresql@18"
MARIA_HOME="/opt/homebrew/opt/mariadb"
PG_PORT="${POC_PG_PORT:-55432}"
PG_RESTORE_PORT="${POC_PG_RESTORE_PORT:-55433}"
MARIA_PORT="${POC_MARIA_PORT:-53306}"
MARIA_RESTORE_PORT="${POC_MARIA_RESTORE_PORT:-53307}"
ROLE_PASSWORD="poc_local_only"
DB_NAME="card_pulse_poc"

pg_dir() { echo "${POC_ROOT}/pg-${1}"; }
maria_dir() { echo "${POC_ROOT}/maria-${1}"; }

pg_port_for() { if [ "$1" = "main" ]; then echo "$PG_PORT"; else echo "$PG_RESTORE_PORT"; fi; }
maria_port_for() { if [ "$1" = "main" ]; then echo "$MARIA_PORT"; else echo "$MARIA_RESTORE_PORT"; fi; }

pg_init() {
  local inst="${1:-main}" dir port
  dir="$(pg_dir "$inst")"; port="$(pg_port_for "$inst")"
  # A previous instance may still own this port and data directory.
  if [ -f "${dir}/data/postmaster.pid" ]; then
    "${PG_HOME}/bin/pg_ctl" -D "${dir}/data" -m immediate -w stop >/dev/null 2>&1 || true
  fi
  rm -rf "$dir"
  mkdir -p "$dir"
  "${PG_HOME}/bin/initdb" -D "${dir}/data" -U cp_admin --encoding=UTF8 --locale=C \
    --auth-local=trust --auth-host=scram-sha-256 >/dev/null
  cat >> "${dir}/data/postgresql.conf" <<CONF

# CP-0009 PoC settings
port = ${port}
listen_addresses = '127.0.0.1'
unix_socket_directories = '${dir}'
max_connections = 50
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 64MB
maintenance_work_mem = 1GB
max_wal_size = 8GB
min_wal_size = 1GB
checkpoint_timeout = 15min
random_page_cost = 1.1
effective_io_concurrency = 200
synchronous_commit = on
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.track = all
track_io_timing = on
log_destination = 'stderr'
logging_collector = on
log_directory = '${POC_ROOT}/logs'
log_filename = 'pg-${inst}-%Y%m%d.log'
log_min_duration_statement = 1000
log_lock_waits = on
log_checkpoints = on
log_connections = on
log_disconnections = on
log_line_prefix = '%m [%p] %u@%d '
deadlock_timeout = 1s
CONF
  echo "initialized postgres ${inst} at ${dir} (port ${port})"
}

pg_start() {
  local inst="${1:-main}" dir port
  dir="$(pg_dir "$inst")"; port="$(pg_port_for "$inst")"
  mkdir -p "${POC_ROOT}/logs"
  "${PG_HOME}/bin/pg_ctl" -D "${dir}/data" -l "${POC_ROOT}/logs/pg-${inst}-ctl.log" -w start
  "${PG_HOME}/bin/psql" -h "${dir}" -p "${port}" -U cp_admin -d postgres -v ON_ERROR_STOP=1 -q \
    -c "ALTER ROLE cp_admin WITH PASSWORD '${ROLE_PASSWORD}';" >/dev/null
}

pg_stop() {
  local inst="${1:-main}" dir mode
  dir="$(pg_dir "$inst")"; mode="${2:-fast}"
  "${PG_HOME}/bin/pg_ctl" -D "${dir}/data" -m "${mode}" -w stop || true
}

pg_kill() {
  local inst="${1:-main}" dir pid
  dir="$(pg_dir "$inst")"
  pid="$(head -1 "${dir}/data/postmaster.pid")"
  kill -9 "${pid}"
  echo "killed postgres ${inst} pid ${pid}"
}

maria_init() {
  local inst="${1:-main}" dir port
  dir="$(maria_dir "$inst")"; port="$(maria_port_for "$inst")"
  if [ -S "${dir}/mysql.sock" ]; then
    "${MARIA_HOME}/bin/mariadb-admin" --socket="${dir}/mysql.sock" -u root shutdown >/dev/null 2>&1 || true
    sleep 1
  fi
  rm -rf "$dir"
  mkdir -p "${dir}/data" "${POC_ROOT}/logs"
  cat > "${dir}/my.cnf" <<CONF
[mariadbd]
datadir = ${dir}/data
port = ${port}
socket = ${dir}/mysql.sock
pid-file = ${dir}/mariadb.pid
bind-address = 127.0.0.1
tmpdir = ${dir}
max_connections = 50
innodb_buffer_pool_size = 2G
innodb_log_file_size = 2G
innodb_flush_log_at_trx_commit = 1
innodb_file_per_table = 1
innodb_lock_wait_timeout = 10
innodb_print_all_deadlocks = 1
local_infile = 1
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
performance_schema = ON
slow_query_log = 1
long_query_time = 1
slow_query_log_file = ${POC_ROOT}/logs/maria-${inst}-slow.log
log_error = ${POC_ROOT}/logs/maria-${inst}-error.log
log_warnings = 3

[mariadb-client]
port = ${port}
socket = ${dir}/mysql.sock
local_infile = 1
CONF
  "${MARIA_HOME}/bin/mariadb-install-db" --defaults-file="${dir}/my.cnf" \
    --datadir="${dir}/data" --auth-root-authentication-method=normal >/dev/null 2>&1
  echo "initialized mariadb ${inst} at ${dir} (port ${port})"
}

maria_start() {
  local inst="${1:-main}" dir port
  dir="$(maria_dir "$inst")"; port="$(maria_port_for "$inst")"
  "${MARIA_HOME}/bin/mariadbd-safe" --defaults-file="${dir}/my.cnf" >/dev/null 2>&1 &
  for _ in $(seq 1 60); do
    if "${MARIA_HOME}/bin/mariadb-admin" --socket="${dir}/mysql.sock" -u root ping >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  "${MARIA_HOME}/bin/mariadb" --socket="${dir}/mysql.sock" -u root <<SQL
CREATE USER IF NOT EXISTS 'cp_admin'@'127.0.0.1' IDENTIFIED BY '${ROLE_PASSWORD}';
GRANT ALL PRIVILEGES ON *.* TO 'cp_admin'@'127.0.0.1' WITH GRANT OPTION;
FLUSH PRIVILEGES;
SQL
  echo "started mariadb ${inst} on port ${port}"
}

maria_stop() {
  local inst="${1:-main}" dir
  dir="$(maria_dir "$inst")"
  "${MARIA_HOME}/bin/mariadb-admin" --socket="${dir}/mysql.sock" -u root shutdown || true
  sleep 1
}

maria_kill() {
  local inst="${1:-main}" dir pid
  dir="$(maria_dir "$inst")"
  pid="$(cat "${dir}/mariadb.pid")"
  pkill -9 -f "mariadbd-safe --defaults-file=${dir}/my.cnf" || true
  kill -9 "${pid}"
  echo "killed mariadb ${inst} pid ${pid}"
}

status() {
  echo "postgres main: $("${PG_HOME}/bin/pg_isready" -h 127.0.0.1 -p "${PG_PORT}" 2>&1 || true)"
  echo "postgres restore: $("${PG_HOME}/bin/pg_isready" -h 127.0.0.1 -p "${PG_RESTORE_PORT}" 2>&1 || true)"
  for inst in main restore; do
    local dir; dir="$(maria_dir "$inst")"
    if "${MARIA_HOME}/bin/mariadb-admin" --socket="${dir}/mysql.sock" -u root ping >/dev/null 2>&1; then
      echo "mariadb ${inst}: alive"
    else
      echo "mariadb ${inst}: no response"
    fi
  done
}

cmd="${1:?usage: instances.sh <command> [instance]}"
shift || true
case "$cmd" in
  pg-init) pg_init "$@" ;;
  pg-start) pg_start "$@" ;;
  pg-stop) pg_stop "$@" ;;
  pg-kill) pg_kill "$@" ;;
  maria-init) maria_init "$@" ;;
  maria-start) maria_start "$@" ;;
  maria-stop) maria_stop "$@" ;;
  maria-kill) maria_kill "$@" ;;
  status) status ;;
  *) echo "unknown command: ${cmd}" >&2; exit 2 ;;
esac
