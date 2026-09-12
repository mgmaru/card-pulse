"""Create the PoC database, least-privilege roles, and dimension rows."""

from __future__ import annotations

import argparse

import sqlalchemy as sa

from . import config
from .util import make_engine

EVIDENCE_TABLES = (
    "raw_artifact",
    "extracted_record",
    "observation_candidate",
    "identity_resolution_attempt",
    "price_observation",
    "price_observation_correction",
)
WORKER_UPDATABLE = ("review_item", "ingest_run", "processing_run", "source")


def _admin_engine(engine: str, port: int | None = None) -> sa.Engine:
    dbname = "postgres" if engine == "postgres" else "mysql"
    return make_engine(engine, role="cp_admin", port=port, dbname=dbname,
                       isolation_level="AUTOCOMMIT")


def reset_database(engine: str, port: int | None = None, dbname: str = config.DB_NAME) -> None:
    eng = _admin_engine(engine, port)
    with eng.connect() as conn:
        if engine == "postgres":
            conn.execute(sa.text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :d AND pid <> pg_backend_pid()"), {"d": dbname})
            conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{dbname}"'))
            conn.execute(sa.text(f'CREATE DATABASE "{dbname}" OWNER cp_migration'))
        else:
            conn.execute(sa.text(f"DROP DATABASE IF EXISTS `{dbname}`"))
            conn.execute(sa.text(
                f"CREATE DATABASE `{dbname}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            # MariaDB has no database owner, so the migration role needs its
            # grant before Alembic can create anything.
            conn.execute(sa.text(
                f"GRANT ALL PRIVILEGES ON `{dbname}`.* TO 'cp_migration'@'127.0.0.1'"))
    eng.dispose()


def create_roles(engine: str, port: int | None = None, dbname: str = config.DB_NAME) -> None:
    """Create API, Worker, migration, and backup roles (DB-SEC-02)."""

    eng = _admin_engine(engine, port)
    # DDL cannot take bind parameters. The PoC password is a local constant
    # defined in config.py and is never a production credential.
    password = config.ROLE_PASSWORD.replace("'", "''")
    with eng.connect() as conn:
        if engine == "postgres":
            for role in ("cp_api", "cp_worker", "cp_migration", "cp_backup"):
                exists = conn.execute(
                    sa.text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": role}
                ).scalar()
                if exists:
                    conn.execute(sa.text(f"ALTER ROLE {role} WITH LOGIN PASSWORD '{password}'"))
                else:
                    conn.execute(sa.text(f"CREATE ROLE {role} LOGIN PASSWORD '{password}'"))
            conn.execute(sa.text("GRANT pg_read_all_data TO cp_backup"))
        else:
            for role in ("cp_api", "cp_worker", "cp_migration", "cp_backup"):
                # CREATE OR REPLACE USER drops the account and every grant it
                # holds, so create it only when missing and set the password
                # separately.
                conn.execute(sa.text(
                    f"CREATE USER IF NOT EXISTS '{role}'@'127.0.0.1' IDENTIFIED BY '{password}'"))
                conn.execute(sa.text(
                    f"ALTER USER '{role}'@'127.0.0.1' IDENTIFIED BY '{password}'"))
            conn.execute(sa.text("GRANT PROCESS, RELOAD ON *.* TO 'cp_backup'@'127.0.0.1'"))
            conn.execute(sa.text("FLUSH PRIVILEGES"))
    eng.dispose()


def apply_grants(engine: str, port: int | None = None, dbname: str = config.DB_NAME) -> None:
    """Grant the least privilege each runtime role needs after migration."""

    eng = make_engine(engine, role="cp_admin", port=port, dbname=dbname,
                      isolation_level="AUTOCOMMIT")
    with eng.connect() as conn:
        if engine == "postgres":
            statements = [
                "GRANT CONNECT ON DATABASE \"%s\" TO cp_api, cp_worker, cp_backup" % dbname,
                "GRANT USAGE ON SCHEMA public TO cp_api, cp_worker, cp_backup",
                "REVOKE CREATE ON SCHEMA public FROM PUBLIC",
                "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM cp_api, cp_worker, cp_backup",
                "GRANT SELECT ON ALL TABLES IN SCHEMA public TO cp_api",
                "GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO cp_worker",
                "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cp_worker",
            ]
            statements += [f"GRANT UPDATE ON {t} TO cp_worker" for t in WORKER_UPDATABLE]
            for statement in statements:
                conn.execute(sa.text(statement))
        else:
            statements = [
                f"GRANT SELECT ON `{dbname}`.* TO 'cp_api'@'127.0.0.1'",
                f"GRANT SELECT, INSERT ON `{dbname}`.* TO 'cp_worker'@'127.0.0.1'",
                f"GRANT ALL PRIVILEGES ON `{dbname}`.* TO 'cp_migration'@'127.0.0.1'",
                f"GRANT SELECT, SHOW VIEW, LOCK TABLES ON `{dbname}`.* TO 'cp_backup'@'127.0.0.1'",
            ]
            statements += [
                f"GRANT UPDATE ON `{dbname}`.`{t}` TO 'cp_worker'@'127.0.0.1'"
                for t in WORKER_UPDATABLE
            ]
            statements.append("FLUSH PRIVILEGES")
            for statement in statements:
                conn.execute(sa.text(statement))
    eng.dispose()


def seed_dimensions(engine: str, port: int | None = None, dbname: str = config.DB_NAME) -> None:
    eng = make_engine(engine, role="cp_admin", port=port, dbname=dbname)
    with eng.begin() as conn:
        conn.execute(sa.text("DELETE FROM shop"))
        conn.execute(sa.text("DELETE FROM source"))
        for source_id, slug, kind, state in config.SOURCES:
            conn.execute(
                sa.text("INSERT INTO source (id, slug, kind, state) VALUES (:i, :s, :k, :st)"),
                {"i": source_id, "s": slug, "k": kind, "st": state},
            )
        for shop_id, slug, name in config.SHOPS:
            conn.execute(
                sa.text("INSERT INTO shop (id, slug, display_name, normalized_name)"
                        " VALUES (:i, :s, :d, :n)"),
                {"i": shop_id, "s": slug, "d": name, "n": slug},
            )
    eng.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["postgres", "mariadb"])
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--dbname", default=config.DB_NAME)
    parser.add_argument("--step", choices=["reset", "roles", "grants", "seed"], required=True)
    args = parser.parse_args()
    match args.step:
        case "reset":
            reset_database(args.engine, args.port, args.dbname)
        case "roles":
            create_roles(args.engine, args.port, args.dbname)
        case "grants":
            apply_grants(args.engine, args.port, args.dbname)
        case "seed":
            seed_dimensions(args.engine, args.port, args.dbname)
    print(f"{args.step} done for {args.engine}")


if __name__ == "__main__":
    main()
