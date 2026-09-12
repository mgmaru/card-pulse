"""Role separation and network exposure checks (DB-SEC-01, DB-SEC-02)."""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import uuid
from typing import Any

import sqlalchemy as sa

from . import config
from .util import Result, make_engine

PROBE_TABLE = "poc_role_probe"


def _attempt(role: str, engine_name: str, sql: str, port: int | None,
             params: dict | None = None) -> dict[str, Any]:
    eng = make_engine(engine_name, role=role, port=port)
    outcome: dict[str, Any] = {"role": role, "statement": sql[:120]}
    try:
        with eng.begin() as conn:
            conn.execute(sa.text(sql), params or {})
        outcome["allowed"] = True
    except Exception as exc:  # noqa: BLE001 - denial is the expected result
        orig = getattr(exc, "orig", exc)
        outcome["allowed"] = False
        outcome["error"] = str(orig)[:160]
    finally:
        eng.dispose()
    return outcome


def check_roles(engine_name: str, port: int | None) -> dict:
    key = f"poc-role-{uuid.uuid4()}"
    select_sql = "SELECT COUNT(*) FROM price_observation"
    insert_sql = (
        "INSERT INTO review_item (id, ingest_run_id, raw_artifact_id, extracted_record_id,"
        " identity_resolution_attempt_id, reason, state, priority, created_at, decided_at,"
        " decided_by, decision, lock_version)"
        " SELECT 8999999999999, a.ingest_run_id, a.id, NULL, NULL,"
        " 'role_probe', 'pending', 5, a.fetched_at, NULL, NULL, NULL, 0"
        " FROM raw_artifact a ORDER BY a.id LIMIT 1"
    )
    update_observation = "UPDATE price_observation SET amount_minor = amount_minor + 1 WHERE id = 1"
    delete_observation = "DELETE FROM price_observation WHERE id = 1"
    update_review = "UPDATE review_item SET priority = priority WHERE id = 1"
    ddl_sql = f"CREATE TABLE {PROBE_TABLE} (id INT)"
    drop_sql = f"DROP TABLE {PROBE_TABLE}"

    expectations = [
        ("cp_api", select_sql, True, "API reads confirmed observations"),
        ("cp_api", insert_sql, False, "API must not append"),
        ("cp_api", update_observation, False, "API must not modify evidence"),
        ("cp_api", ddl_sql, False, "API must not run DDL"),
        ("cp_worker", select_sql, True, "Worker reads"),
        ("cp_worker", insert_sql, True, "Worker appends"),
        ("cp_worker", update_review, True, "Worker records review decisions"),
        ("cp_worker", update_observation, False, "Worker must not rewrite evidence"),
        ("cp_worker", delete_observation, False, "Worker must not delete evidence"),
        ("cp_worker", ddl_sql, False, "Worker must not run DDL"),
        ("cp_backup", select_sql, True, "Backup role reads"),
        ("cp_backup", insert_sql, False, "Backup role must not write"),
        ("cp_migration", ddl_sql, True, "Migration role owns DDL"),
        ("cp_migration", drop_sql, True, "Migration role can drop what it created"),
    ]
    results = []
    for role, sql, expected, purpose in expectations:
        outcome = _attempt(role, engine_name, sql, port)
        outcome["expected_allowed"] = expected
        outcome["purpose"] = purpose
        outcome["pass"] = outcome["allowed"] == expected
        results.append(outcome)

    # Clean up the probe row the Worker appended.
    admin = make_engine(engine_name, port=port)
    with admin.begin() as conn:
        conn.execute(sa.text("DELETE FROM review_item WHERE id = 8999999999999"))
        conn.execute(sa.text(f"DROP TABLE IF EXISTS {PROBE_TABLE}"))
    admin.dispose()
    return {"checks": results, "pass": all(item["pass"] for item in results)}


def _lan_address() -> str | None:
    for interface in ("en0", "en1"):
        try:
            value = subprocess.run(["ipconfig", "getifaddr", interface], capture_output=True,
                                   text=True, timeout=5).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            continue
        if value:
            return value
    return None


def check_network_exposure(engine_name: str, port: int | None) -> dict:
    """The server must not accept connections from outside loopback (DB-SEC-01)."""

    port = port or (config.PG_PORT if engine_name == "postgres" else config.MARIA_PORT)
    address = _lan_address()
    loopback = _probe_tcp("127.0.0.1", port)
    lan = _probe_tcp(address, port) if address else {"skipped": "no LAN address"}
    return {
        "port": port,
        "loopback": loopback,
        "lan_address": address,
        "lan": lan,
        "pass": loopback.get("connected") is True and (
            address is None or lan.get("connected") is False),
    }


def _probe_tcp(host: str, port: int, timeout: float = 3.0) -> dict:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"host": host, "connected": True}
    except OSError as exc:
        return {"host": host, "connected": False, "error": f"{type(exc).__name__}: {exc}"[:120]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["postgres", "mariadb"])
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    data = {
        "roles": check_roles(args.engine, args.port),
        "network": check_network_exposure(args.engine, args.port),
    }
    data["all_passed"] = all(v.get("pass") for v in data.values() if isinstance(v, dict))
    result = Result(step="roles", engine=args.engine, scale=args.scale, data=data)
    for item in data["roles"]["checks"]:
        flag = "ok" if item["pass"] else "MISMATCH"
        print(f"  {flag}: {item['role']} {'allowed' if item['allowed'] else 'denied'}"
              f" -- {item['purpose']}")
    print(f"  network: {json.dumps(data['network'], default=str)}")
    print(f"wrote {result.write()}")


if __name__ == "__main__":
    main()
