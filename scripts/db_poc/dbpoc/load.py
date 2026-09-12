"""Bulk load the generated profile into one candidate and measure it.

Both candidates load the same files with foreign key enforcement deferred for
the seed, then re-enable it and verify referential integrity. Runtime ingestion
keeps the constraints on; this only affects the initial seed.
"""

from __future__ import annotations

import argparse
import json

import sqlalchemy as sa

from . import config, measure
from .generate import COLUMNS, out_dir
from .schema import BULK_TABLES
from .util import Result, make_engine, timer


def _load_postgres(conn, table: str, path, columns: tuple[str, ...]) -> int:
    raw = conn.connection.dbapi_connection
    collist = ", ".join(columns)
    with raw.cursor() as cur:
        with cur.copy(f"COPY {table} ({collist}) FROM STDIN") as copy:
            with path.open("rb") as handle:
                while chunk := handle.read(1 << 22):
                    copy.write(chunk)
        return cur.rowcount


def _load_mariadb(conn, table: str, path, columns: tuple[str, ...]) -> int:
    collist = ", ".join(f"`{c}`" for c in columns)
    sql = (
        f"LOAD DATA LOCAL INFILE '{path}' INTO TABLE `{table}` "
        "CHARACTER SET utf8mb4 "
        "FIELDS TERMINATED BY '\\t' ESCAPED BY '\\\\' "
        "LINES TERMINATED BY '\\n' "
        f"({collist})"
    )
    result = conn.exec_driver_sql(sql)
    return result.rowcount


def load(engine: str, scale: int, port: int | None = None) -> dict:
    directory = out_dir(scale)
    eng = make_engine(engine, port=port)
    per_table: dict[str, dict] = {}

    with eng.connect() as conn:
        if engine == "postgres":
            conn.exec_driver_sql("SET session_replication_role = 'replica'")
        else:
            conn.exec_driver_sql("SET foreign_key_checks = 0")
            conn.exec_driver_sql("SET unique_checks = 1")

        total_start = timer()
        with total_start as total:
            for table in BULK_TABLES:
                path = directory / f"{table}.tsv"
                columns = COLUMNS[table]
                with timer() as step:
                    if engine == "postgres":
                        rows = _load_postgres(conn, table, path, columns)
                    else:
                        rows = _load_mariadb(conn, table, path, columns)
                    conn.commit()
                per_table[table] = {
                    "rows": rows,
                    "seconds": step["seconds"],
                    "file_bytes": path.stat().st_size,
                    "rows_per_second": rows / step["seconds"] if step["seconds"] else None,
                }
                print(f"  {table}: {rows} rows in {step['seconds']:.1f}s", flush=True)
        if engine == "postgres":
            conn.exec_driver_sql("SET session_replication_role = 'origin'")
        else:
            conn.exec_driver_sql("SET foreign_key_checks = 1")
        conn.commit()

    with eng.connect() as conn, timer() as analyze:
        if engine == "postgres":
            conn.exec_driver_sql("ANALYZE")
        else:
            for table in BULK_TABLES:
                conn.exec_driver_sql(f"ANALYZE TABLE `{table}`")
        conn.commit()
    eng.dispose()

    return {
        "per_table": per_table,
        "load_seconds": total["seconds"],
        "analyze_seconds": analyze["seconds"],
        "loaded_rows": sum(t["rows"] for t in per_table.values()),
    }


def verify_foreign_keys(engine: str, port: int | None = None) -> dict:
    """Confirm the seed left no dangling reference after constraints are back on."""

    checks = {
        "raw_artifact_to_ingest_run":
            "SELECT COUNT(*) FROM raw_artifact a LEFT JOIN ingest_run r ON r.id = a.ingest_run_id"
            " WHERE r.id IS NULL",
        "processing_run_to_artifact":
            "SELECT COUNT(*) FROM processing_run p LEFT JOIN raw_artifact a ON a.id ="
            " p.raw_artifact_id WHERE a.id IS NULL",
        "extracted_record_to_processing_run":
            "SELECT COUNT(*) FROM extracted_record e LEFT JOIN processing_run p ON p.id ="
            " e.processing_run_id WHERE p.id IS NULL",
        "candidate_to_record":
            "SELECT COUNT(*) FROM observation_candidate c LEFT JOIN extracted_record e ON e.id ="
            " c.extracted_record_id WHERE e.id IS NULL",
        "attempt_to_candidate":
            "SELECT COUNT(*) FROM identity_resolution_attempt t LEFT JOIN observation_candidate c"
            " ON c.id = t.observation_candidate_id WHERE c.id IS NULL",
        "observation_to_card":
            "SELECT COUNT(*) FROM price_observation o LEFT JOIN card_identity k ON k.id ="
            " o.card_identity_id WHERE k.id IS NULL",
        "review_to_run":
            "SELECT COUNT(*) FROM review_item v LEFT JOIN ingest_run r ON r.id = v.ingest_run_id"
            " WHERE r.id IS NULL",
    }
    eng = make_engine(engine, port=port)
    out = {}
    with eng.connect() as conn:
        for name, sql in checks.items():
            out[name] = int(conn.execute(sa.text(sql)).scalar_one())
    eng.dispose()
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["postgres", "mariadb"])
    parser.add_argument("--scale", type=int, choices=[1, 10], required=True)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    print(f"loading scale {args.scale} into {args.engine}", flush=True)
    loaded = load(args.engine, args.scale, args.port)
    dangling = verify_foreign_keys(args.engine, args.port)
    sizes = measure.table_sizes(args.engine, args.port)
    footprint = measure.storage_footprint(args.engine)
    counts = measure.row_counts(args.engine, args.port)

    result = Result(step="load", engine=args.engine, scale=args.scale, data={
        **loaded,
        "dangling_references": dangling,
        "sizes": sizes,
        "storage_footprint": footprint,
        "row_counts": counts,
        "total_rows": sum(counts.values()),
    })
    print(json.dumps({
        "load_seconds": round(loaded["load_seconds"], 1),
        "analyze_seconds": round(loaded["analyze_seconds"], 1),
        "total_rows": sum(counts.values()),
        "table_bytes_total": sizes["table_bytes_total"],
        "index_bytes_total": sizes["index_bytes_total"],
        "dangling": dangling,
    }, indent=2))
    print(f"wrote {result.write()}")


if __name__ == "__main__":
    main()
