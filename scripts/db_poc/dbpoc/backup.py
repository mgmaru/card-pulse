"""Encrypted logical backup, restore into an empty instance, and verification.

Covers DB-REC-02 to DB-REC-07 and PoC condition 8: one backup set holds the
basis time, the database dump, global objects, the migration revision, an
artifact manifest, and a checksum per file, and the restore is verified against
the source database without using it as the restore target.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import sqlalchemy as sa

from . import config, measure
from .schema import TABLE_ORDER
from .util import Result, make_engine, timer

INSTANCES = Path(__file__).resolve().parents[1] / "bin" / "instances.sh"
PG_BIN = config.PG_HOME / "bin"
MARIA_BIN = config.MARIA_HOME / "bin"
ARTIFACT_HASH_SAMPLE = 2000
ROW_HASH_SAMPLE = 1000


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def passphrase_file() -> Path:
    """A local key file kept out of the repository and out of the manifest."""

    target = config.BACKUP_PASSPHRASE_FILE
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(hashlib.sha256(os.urandom(32)).hexdigest())
        target.chmod(0o600)
    return target


def _encrypt(source: Path) -> Path:
    target = source.with_suffix(source.suffix + ".enc")
    subprocess.run(
        ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-in", str(source),
         "-out", str(target), "-pass", f"file:{passphrase_file()}"],
        check=True, capture_output=True,
    )
    source.unlink()
    return target


def _decrypt(source: Path) -> Path:
    target = source.with_suffix("")
    subprocess.run(
        ["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-in", str(source),
         "-out", str(target), "-pass", f"file:{passphrase_file()}"],
        check=True, capture_output=True,
    )
    return target


def artifact_manifest(engine_name: str, scale: int, port: int | None) -> dict:
    """Every artifact the database references, with a hashed sample."""

    root = config.ARTIFACT_DIR / f"scale{scale}"
    eng = make_engine(engine_name, role="cp_backup", port=port)
    missing: list[str] = []
    hashed: dict[str, str] = {}
    total = 0
    with eng.connect() as conn:
        rows = conn.execution_options(stream_results=True, yield_per=10_000).execute(
            sa.text("SELECT storage_ref FROM raw_artifact ORDER BY id"))
        for index, (storage_ref,) in enumerate(rows):
            total += 1
            path = root / storage_ref.removeprefix("artifacts/")
            if not path.exists():
                if len(missing) < 50:
                    missing.append(storage_ref)
                continue
            if index % max(total // ARTIFACT_HASH_SAMPLE, 1) == 0 and len(hashed) < ARTIFACT_HASH_SAMPLE:
                hashed[storage_ref] = _sha256(path)
    eng.dispose()
    return {
        "artifact_root": str(root),
        "referenced_artifacts": total,
        "missing_artifacts": missing,
        "missing_count": len(missing),
        "hashed_sample": hashed,
    }


def entity_fingerprint(engine_name: str, port: int | None,
                       dbname: str = config.DB_NAME) -> dict:
    """Row counts plus a hash over representative rows, for restore comparison."""

    eng = make_engine(engine_name, port=port, dbname=dbname)
    counts: dict[str, int] = {}
    with eng.connect() as conn:
        for table in TABLE_ORDER:
            counts[table] = int(conn.execute(
                sa.text(f"SELECT COUNT(*) FROM {table}")).scalar_one())
        sample = conn.execute(sa.text(
            "SELECT id, card_identity_id, shop_id, amount_minor, currency, price_type,"
            " card_condition, observed_at, idempotency_key"
            " FROM price_observation ORDER BY id LIMIT :limit"), {"limit": ROW_HASH_SAMPLE}
        ).fetchall()
        digest = hashlib.sha256()
        for row in sample:
            digest.update("|".join(str(value) for value in row).encode("utf-8"))
        constraint_counts = _constraint_counts(conn, engine_name, dbname)
    eng.dispose()
    return {
        "row_counts": counts,
        "total_rows": sum(counts.values()),
        "sample_rows": len(sample),
        "sample_sha256": digest.hexdigest(),
        "constraints": constraint_counts,
    }


def _constraint_counts(conn: sa.Connection, engine_name: str, dbname: str) -> dict[str, int]:
    if engine_name == "postgres":
        rows = conn.execute(sa.text(
            "SELECT contype, COUNT(*) FROM pg_constraint c"
            " JOIN pg_class t ON t.oid = c.conrelid"
            " JOIN pg_namespace n ON n.oid = t.relnamespace"
            " WHERE n.nspname = 'public' GROUP BY contype")).fetchall()
        mapping = {"p": "primary_key", "f": "foreign_key", "u": "unique", "c": "check"}
        return {mapping.get(str(kind), str(kind)): int(count) for kind, count in rows}
    rows = conn.execute(sa.text(
        "SELECT constraint_type, COUNT(*) FROM information_schema.table_constraints"
        " WHERE table_schema = :schema GROUP BY constraint_type"), {"schema": dbname}).fetchall()
    checks = int(conn.execute(sa.text(
        "SELECT COUNT(*) FROM information_schema.check_constraints WHERE constraint_schema = :schema"),
        {"schema": dbname}).scalar_one())
    out = {str(kind).lower().replace(" ", "_"): int(count) for kind, count in rows}
    out["check_constraints_total"] = checks
    return out


def _alembic_revision(engine_name: str, port: int | None, dbname: str = config.DB_NAME) -> str:
    eng = make_engine(engine_name, port=port, dbname=dbname)
    with eng.connect() as conn:
        value = conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one()
    eng.dispose()
    return str(value)


def backup(engine_name: str, scale: int, port: int | None) -> dict:
    directory = config.BACKUP_DIR / engine_name
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True, exist_ok=True)
    port = port or (config.PG_PORT if engine_name == "postgres" else config.MARIA_PORT)
    basis = datetime.now(UTC)
    env = dict(os.environ, PGPASSWORD=config.ROLE_PASSWORD)
    files: dict[str, dict] = {}

    if engine_name == "postgres":
        dump_path = directory / "database.dump"
        with timer() as dump_timer:
            subprocess.run(
                [str(PG_BIN / "pg_dump"), "--format=custom", "--compress=9",
                 "--file", str(dump_path), "--host", "127.0.0.1", "--port", str(port),
                 "--username", "cp_backup", "--no-password", config.DB_NAME],
                check=True, env=env, capture_output=True,
            )
        globals_path = directory / "globals.sql"
        with timer() as globals_timer:
            with globals_path.open("w") as handle:
                subprocess.run(
                    [str(PG_BIN / "pg_dumpall"), "--globals-only", "--no-role-passwords",
                     "--host", "127.0.0.1", "--port", str(port), "--username", "cp_admin",
                     "--no-password"],
                    check=True, env=env, stdout=handle, stderr=subprocess.PIPE,
                )
    else:
        dump_path = directory / "database.sql.gz"
        with timer() as dump_timer:
            proc = subprocess.Popen(
                [str(MARIA_BIN / "mariadb-dump"), "--single-transaction", "--routines",
                 "--hex-blob", "--host", "127.0.0.1", "--port", str(port),
                 "--user", "cp_backup", f"--password={config.ROLE_PASSWORD}",
                 "--databases", config.DB_NAME],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            with gzip.open(dump_path, "wb") as handle:
                shutil.copyfileobj(proc.stdout, handle)
            proc.wait()
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.read().decode()[:500])
        globals_path = directory / "globals.sql"
        with timer() as globals_timer:
            with globals_path.open("w") as handle:
                subprocess.run(
                    [str(MARIA_BIN / "mariadb-dump"), "--system=users", "--host", "127.0.0.1",
                     "--port", str(port), "--user", "cp_admin",
                     f"--password={config.ROLE_PASSWORD}"],
                    check=True, stdout=handle, stderr=subprocess.PIPE,
                )

    plain_sizes = {"database": dump_path.stat().st_size, "globals": globals_path.stat().st_size}
    with timer() as encrypt_timer:
        encrypted_dump = _encrypt(dump_path)
        encrypted_globals = _encrypt(globals_path)
    for label, path in (("database", encrypted_dump), ("globals", encrypted_globals)):
        files[label] = {
            "path": path.name,
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
            "encryption": "aes-256-cbc/pbkdf2",
        }

    manifest_artifacts = artifact_manifest(engine_name, scale, port)
    fingerprint = entity_fingerprint(engine_name, port)
    manifest = {
        "basis_time": basis.isoformat(),
        "engine": engine_name,
        "scale": scale,
        "migration_revision": _alembic_revision(engine_name, port),
        "files": files,
        "plain_bytes": plain_sizes,
        "artifacts": {k: v for k, v in manifest_artifacts.items() if k != "hashed_sample"},
        "artifact_hash_sample_size": len(manifest_artifacts["hashed_sample"]),
        "source_fingerprint": fingerprint,
        "notes": "Worker stopped for the backup window; no credentials or keys are stored here.",
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    (directory / "artifact-hashes.json").write_text(
        json.dumps(manifest_artifacts["hashed_sample"], indent=2))
    return {
        "directory": str(directory),
        "dump_seconds": dump_timer["seconds"],
        "globals_seconds": globals_timer["seconds"],
        "encrypt_seconds": encrypt_timer["seconds"],
        "backup_bytes": sum(f["bytes"] for f in files.values()),
        "plain_bytes": plain_sizes,
        "manifest": manifest,
    }


def restore(engine_name: str, scale: int) -> dict:
    """Restore into a freshly initialized instance that never held this data."""

    directory = config.BACKUP_DIR / engine_name
    manifest = json.loads((directory / "manifest.json").read_text())
    checksum_results = {
        label: _sha256(directory / info["path"]) == info["sha256"]
        for label, info in manifest["files"].items()
    }
    port = config.PG_RESTORE_PORT if engine_name == "postgres" else config.MARIA_RESTORE_PORT
    env = dict(os.environ, PGPASSWORD=config.ROLE_PASSWORD)

    with timer() as prepare:
        init_cmd = "pg-init" if engine_name == "postgres" else "maria-init"
        start_cmd = "pg-start" if engine_name == "postgres" else "maria-start"
        subprocess.run([str(INSTANCES), init_cmd, "restore"], check=True, capture_output=True)
        subprocess.run([str(INSTANCES), start_cmd, "restore"], check=True, capture_output=True)

    decrypted_dump = _decrypt(directory / manifest["files"]["database"]["path"])
    decrypted_globals = _decrypt(directory / manifest["files"]["globals"]["path"])

    with timer() as restore_timer:
        if engine_name == "postgres":
            with decrypted_globals.open("rb") as handle:
                subprocess.run(
                    [str(PG_BIN / "psql"), "--host", "127.0.0.1", "--port", str(port),
                     "--username", "cp_admin", "--dbname", "postgres", "--quiet"],
                    stdin=handle, env=env, capture_output=True,
                )
            subprocess.run(
                [str(PG_BIN / "createdb"), "--host", "127.0.0.1", "--port", str(port),
                 "--username", "cp_admin", "--owner", "cp_migration", config.DB_NAME],
                check=True, env=env, capture_output=True,
            )
            completed = subprocess.run(
                [str(PG_BIN / "pg_restore"), "--host", "127.0.0.1", "--port", str(port),
                 "--username", "cp_admin", "--dbname", config.DB_NAME, "--jobs", "4",
                 "--no-owner", str(decrypted_dump)],
                env=env, capture_output=True, text=True,
            )
            restore_stderr = completed.stderr[-1500:]
        else:
            with decrypted_globals.open("rb") as handle:
                subprocess.run(
                    [str(MARIA_BIN / "mariadb"), "--host", "127.0.0.1", "--port", str(port),
                     "--user", "root"],
                    stdin=handle, capture_output=True,
                )
            unzipped = decrypted_dump.with_suffix("")
            with gzip.open(decrypted_dump, "rb") as source, unzipped.open("wb") as target:
                shutil.copyfileobj(source, target)
            with unzipped.open("rb") as handle:
                completed = subprocess.run(
                    [str(MARIA_BIN / "mariadb"), "--host", "127.0.0.1", "--port", str(port),
                     "--user", "root"],
                    stdin=handle, capture_output=True, text=True,
                )
            restore_stderr = completed.stderr[-1500:]
            unzipped.unlink(missing_ok=True)

    with timer() as verify_timer:
        restored = entity_fingerprint(engine_name, port)
        source = manifest["source_fingerprint"]
        artifact_check = _verify_artifacts(engine_name, scale, port, directory)
    decrypted_dump.unlink(missing_ok=True)
    decrypted_globals.unlink(missing_ok=True)

    counts_match = restored["row_counts"] == source["row_counts"]
    sample_match = restored["sample_sha256"] == source["sample_sha256"]
    constraints_match = restored["constraints"] == source["constraints"]
    return {
        "checksums_verified": checksum_results,
        "prepare_seconds": prepare["seconds"],
        "restore_seconds": restore_timer["seconds"],
        "verify_seconds": verify_timer["seconds"],
        "restore_stderr": restore_stderr,
        "restored_fingerprint": restored,
        "counts_match": counts_match,
        "sample_hash_match": sample_match,
        "constraints_match": constraints_match,
        "constraints_source": source["constraints"],
        "constraints_restored": restored["constraints"],
        "artifacts": artifact_check,
        "total_seconds": prepare["seconds"] + restore_timer["seconds"] + verify_timer["seconds"],
        "pass": all(checksum_results.values()) and counts_match and sample_match
                and constraints_match and artifact_check["pass"],
    }


def _verify_artifacts(engine_name: str, scale: int, port: int, directory: Path) -> dict:
    """Every artifact referenced by the restored database must exist and match."""

    root = config.ARTIFACT_DIR / f"scale{scale}"
    hashes = json.loads((directory / "artifact-hashes.json").read_text())
    eng = make_engine(engine_name, port=port)
    missing: list[str] = []
    total = 0
    with eng.connect() as conn:
        rows = conn.execution_options(stream_results=True, yield_per=10_000).execute(
            sa.text("SELECT storage_ref FROM raw_artifact ORDER BY id"))
        for (storage_ref,) in rows:
            total += 1
            if not (root / storage_ref.removeprefix("artifacts/")).exists():
                if len(missing) < 50:
                    missing.append(storage_ref)
    eng.dispose()
    mismatched = [ref for ref, digest in hashes.items()
                  if _sha256(root / ref.removeprefix("artifacts/")) != digest]
    return {
        "referenced_artifacts": total,
        "missing_count": len(missing),
        "missing_examples": missing[:10],
        "hash_checked": len(hashes),
        "hash_mismatched": len(mismatched),
        "pass": not missing and not mismatched,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["postgres", "mariadb"])
    parser.add_argument("--scale", type=int, choices=[1, 10], required=True)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--step", choices=["backup", "restore", "both"], default="both")
    args = parser.parse_args()

    data: dict[str, Any] = {}
    # Each part writes its own result file; a shared file would be overwritten
    # when backup and restore run as separate steps.
    if args.step in {"backup", "both"}:
        data["backup"] = backup(args.engine, args.scale, args.port)
        print(f"  backup: {data['backup']['dump_seconds']:.1f}s dump,"
              f" {data['backup']['backup_bytes']} bytes", flush=True)
        print(f"wrote {Result(step='backup', engine=args.engine, scale=args.scale, data=data['backup']).write()}")
    if args.step in {"restore", "both"}:
        data["restore"] = restore(args.engine, args.scale)
        print(f"  restore: {data['restore']['restore_seconds']:.1f}s,"
              f" pass={data['restore']['pass']}", flush=True)
        print(f"wrote {Result(step='restore', engine=args.engine, scale=args.scale, data=data['restore']).write()}")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in {"manifest"}}
                      for k, v in data.items()}, indent=2, default=str)[:3000])


if __name__ == "__main__":
    main()
