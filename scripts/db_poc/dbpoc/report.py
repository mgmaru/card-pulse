"""Aggregate the result files into one comparison summary.

Reads var/db-poc/results and prints Markdown, so the PoC document quotes
measured values instead of hand-copied ones.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from . import config

ENGINES = ("postgres", "mariadb")
LABEL = {"postgres": "PostgreSQL 18.6", "mariadb": "MariaDB 12.3.3"}


def load(engine: str, scale: int | None, step: str) -> dict | None:
    folder = "common" if scale is None else f"scale{scale}"
    path = config.RESULT_DIR / engine / folder / f"{step}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def mb(value: float | None) -> str:
    return "-" if value is None else f"{value / 1_000_000:,.0f}"


def ms(value: float | None) -> str:
    return "-" if value is None else f"{value:,.2f}"


def seconds(value: float | None) -> str:
    return "-" if value is None else f"{value:,.1f}"


def sizes_table(scale: int) -> list[str]:
    rows = ["| 項目 | PostgreSQL 18.6 | MariaDB 12.3.3 |", "| --- | ---: | ---: |"]
    data = {e: load(e, scale, "load") for e in ENGINES}
    if not all(data.values()):
        return []
    fields = [
        ("投入行数", lambda d: f"{d['total_rows']:,}"),
        ("投入時間 (秒)", lambda d: seconds(d["load_seconds"])),
        ("統計更新 (秒)", lambda d: seconds(d["analyze_seconds"])),
        ("table (MB)", lambda d: mb(d["sizes"]["table_bytes_total"])),
        ("index (MB)", lambda d: mb(d["sizes"]["index_bytes_total"])),
        ("table+index (MB)", lambda d: mb(d["sizes"]["table_bytes_total"]
                                          + d["sizes"]["index_bytes_total"])),
        ("data directory (MB)", lambda d: mb(d["storage_footprint"]["data_dir_bytes"])),
        ("WAL・redo log (MB)", lambda d: mb(d["storage_footprint"]["wal_bytes"])),
    ]
    for label, getter in fields:
        rows.append(f"| {label} | {getter(data['postgres'])} | {getter(data['mariadb'])} |")
    return rows


def query_table(scale: int) -> list[str]:
    rows = ["| Query | 目標p95 | PG cold | PG warm単独 | PG 同時実行p95 | Maria cold |"
            " Maria warm単独 | Maria 同時実行p95 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    bench = {e: load(e, scale, "bench") for e in ENGINES}
    cold = {e: load(e, scale, "bench-cold") for e in ENGINES}
    if not all(bench.values()):
        return []
    for name, verdict in bench["postgres"]["verdict"].items():
        cells = [name, f"{verdict['target_p95_ms']:.0f} ms"]
        for engine in ENGINES:
            cold_ms = (cold[engine]["cold_single_ms"][name][0]
                       if cold.get(engine) else None)
            warm = bench[engine]["warm_single_ms"][name]
            cells += [ms(cold_ms), ms(min(warm)),
                      ms(bench[engine]["verdict"][name]["p95_ms"])]
        rows.append("| " + " | ".join(cells) + " |")
    return rows


def concurrency_table(scale: int) -> list[str]:
    bench = {e: load(e, scale, "bench") for e in ENGINES}
    if not all(bench.values()):
        return []
    rows = ["| 項目 | PostgreSQL 18.6 | MariaDB 12.3.3 |", "| --- | ---: | ---: |"]
    fields = [
        ("測定時間 (秒)", lambda d: seconds(d["duration_seconds"])),
        ("reader / writer", lambda d: f"{d['readers']} / {d['writers']}"),
        ("writer batch p95 (ms)", lambda d: ms(d["writer_batch_ms"]["p95_ms"])),
        ("writer batch 最大 (ms)", lambda d: ms(d["writer_batch_ms"]["max_ms"])),
        ("追記した観測数", lambda d: f"{d['observations_written']:,}"),
        ("query実行数", lambda d: f"{sum(v['count'] for v in d['concurrent'].values()):,}"),
        ("失敗数", lambda d: str(d["error_count"])),
        ("最大接続数", lambda d: str(d["peak_connections"])),
        ("deadlock", lambda d: str(d["counters_after"].get("deadlocks")
                                   if "deadlocks" in d["counters_after"]
                                   else d["counters_after"].get("Innodb_deadlocks"))),
    ]
    for label, getter in fields:
        rows.append(f"| {label} | {getter(bench['postgres'])} | {getter(bench['mariadb'])} |")
    return rows


def ingest_table(scale: int) -> list[str]:
    daily = {e: load(e, scale, "ingest-daily") for e in ENGINES}
    reparse = {e: load(e, scale, "ingest-reparse") for e in ENGINES}
    if not all(daily.values()):
        return []
    rows = ["| 項目 | 基準 | PostgreSQL 18.6 | MariaDB 12.3.3 |", "| --- | --- | ---: | ---: |"]
    rows.append("| 1日分の取込時間 (秒) | 600以内 | "
                f"{seconds(daily['postgres']['seconds'])} | {seconds(daily['mariadb']['seconds'])} |")
    rows.append("| 1日分の追記行数 | - | "
                f"{daily['postgres']['total_rows_written']:,} |"
                f" {daily['mariadb']['total_rows_written']:,} |")
    rows.append("| 取込中のread p95 (ms) | - | "
                f"{ms(daily['postgres']['concurrent_read_ms']['p95_ms'])} |"
                f" {ms(daily['mariadb']['concurrent_read_ms']['p95_ms'])} |")
    if all(reparse.values()):
        rows.append("| 28日分の再解析 (秒) | 28,800以内 | "
                    f"{seconds(reparse['postgres']['seconds'])} |"
                    f" {seconds(reparse['mariadb']['seconds'])} |")
        rows.append("| 再解析で増えた確定観測 | 0 | "
                    f"{reparse['postgres']['new_observations']} |"
                    f" {reparse['mariadb']['new_observations']} |")
        rows.append("| 重複した冪等key | 0 | "
                    f"{reparse['postgres']['duplicate_idempotency_keys']} |"
                    f" {reparse['mariadb']['duplicate_idempotency_keys']} |")
    return rows


def backup_table(scale: int) -> list[str]:
    data = {e: {"backup": load(e, scale, "backup"), "restore": load(e, scale, "restore")}
            for e in ENGINES}
    if not all(v["backup"] and v["restore"] for v in data.values()):
        return []
    rows = ["| 項目 | PostgreSQL 18.6 | MariaDB 12.3.3 |", "| --- | ---: | ---: |"]
    fields = [
        ("backup取得 (秒)", lambda d: seconds(d["backup"]["dump_seconds"])),
        ("暗号化 (秒)", lambda d: seconds(d["backup"]["encrypt_seconds"])),
        ("backup容量 (MB)", lambda d: mb(d["backup"]["backup_bytes"])),
        ("空環境の準備 (秒)", lambda d: seconds(d["restore"]["prepare_seconds"])),
        ("復元 (秒)", lambda d: seconds(d["restore"]["restore_seconds"])),
        ("検証 (秒)", lambda d: seconds(d["restore"]["verify_seconds"])),
        ("復元+検証 合計 (秒)", lambda d: seconds(d["restore"]["total_seconds"])),
        ("件数一致", lambda d: "はい" if d["restore"]["counts_match"] else "いいえ"),
        ("代表行hash一致", lambda d: "はい" if d["restore"]["sample_hash_match"] else "いいえ"),
        ("constraint一致", lambda d: "はい" if d["restore"]["constraints_match"] else "いいえ"),
        ("欠落artifact", lambda d: str(d["restore"]["artifacts"]["missing_count"])),
    ]
    for label, getter in fields:
        rows.append(f"| {label} | {getter(data['postgres'])} | {getter(data['mariadb'])} |")
    return rows


def checks_table(scale: int) -> list[str]:
    integrity = {e: load(e, scale, "integrity") for e in ENGINES}
    crash = {e: load(e, scale, "crash") for e in ENGINES}
    roles = {e: load(e, scale, "roles") for e in ENGINES}
    monitor = {e: load(e, scale, "monitor") for e in ENGINES}
    if not all(integrity.values()):
        return []

    def mark(value: Any) -> str:
        return "合格" if value else "不合格"

    rows = ["| 検証 | PostgreSQL 18.6 | MariaDB 12.3.3 |", "| --- | --- | --- |"]
    names = [k for k in integrity["postgres"] if isinstance(integrity["postgres"][k], dict)]
    for name in names:
        rows.append(f"| {name} | {mark(integrity['postgres'][name].get('pass'))} |"
                    f" {mark(integrity['mariadb'][name].get('pass'))} |")
    for label, source in (("killed_client", crash), ("server_crash", crash)):
        rows.append(f"| {label} | {mark(source['postgres'][label]['pass'])} |"
                    f" {mark(source['mariadb'][label]['pass'])} |")
    rows.append(f"| role separation | {mark(roles['postgres']['roles']['pass'])} |"
                f" {mark(roles['mariadb']['roles']['pass'])} |")
    rows.append(f"| network exposure | {mark(roles['postgres']['network']['pass'])} |"
                f" {mark(roles['mariadb']['network']['pass'])} |")
    if all(monitor.values()):
        for name in ("connection_usage", "slow_query", "lock_wait", "long_transaction",
                     "backup_age"):
            if name in monitor["postgres"]:
                rows.append(f"| monitor: {name} | {mark(monitor['postgres'][name]['pass'])} |"
                            f" {mark(monitor['mariadb'][name]['pass'])} |")
    return rows


def migration_table() -> list[str]:
    rows = ["| 項目 | PostgreSQL 18.6 | MariaDB 12.3.3 |", "| --- | --- | --- |"]
    initial = {e: load(e, None, "migrate-initial") for e in ENGINES}
    offline = {e: load(e, None, "migrate-offline") for e in ENGINES}
    failing = {e: load(e, None, "migrate-failing") for e in ENGINES}
    compat = {e: (load(e, 10, "migrate-compat") or load(e, 1, "migrate-compat"))
              for e in ENGINES}
    if not all(initial.values()):
        return []
    rows.append(f"| 空DBへのupgrade (秒) | {seconds(initial['postgres']['upgrade']['seconds'])} |"
                f" {seconds(initial['mariadb']['upgrade']['seconds'])} |")
    rows.append(f"| offline SQL文数 | {offline['postgres']['statements']} |"
                f" {offline['mariadb']['statements']} |")
    if all(compat.values()):
        rows.append(f"| 後方互換migration (秒) |"
                    f" {seconds(compat['postgres']['migration']['seconds'])} |"
                    f" {seconds(compat['mariadb']['migration']['seconds'])} |")
        rows.append(f"| migration中の旧query p95 (ms) |"
                    f" {ms(compat['postgres']['old_query_p95_ms'])} |"
                    f" {ms(compat['mariadb']['old_query_p95_ms'])} |")
        rows.append(f"| migration中の旧query最大 (ms) |"
                    f" {ms(compat['postgres']['old_query_max_ms'])} |"
                    f" {ms(compat['mariadb']['old_query_max_ms'])} |")
    rows.append(f"| 失敗migrationの部分適用 |"
                f" {'あり' if failing['postgres']['partially_applied'] else 'なし'} |"
                f" {'あり' if failing['mariadb']['partially_applied'] else 'なし'} |")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scale", type=int, nargs="*", default=[1, 10])
    args = parser.parse_args()

    print("## Migration\n")
    print("\n".join(migration_table()) or "(結果なし)")
    for scale in args.scale:
        print(f"\n## 容量と投入 (scale {scale})\n")
        print("\n".join(sizes_table(scale)) or "(結果なし)")
        print(f"\n## Query (scale {scale})\n")
        print("\n".join(query_table(scale)) or "(結果なし)")
        print(f"\n## 同時実行 (scale {scale})\n")
        print("\n".join(concurrency_table(scale)) or "(結果なし)")
        print(f"\n## 取込と再解析 (scale {scale})\n")
        print("\n".join(ingest_table(scale)) or "(結果なし)")
        print(f"\n## Backupと復元 (scale {scale})\n")
        print("\n".join(backup_table(scale)) or "(結果なし)")
        print(f"\n## 整合性・障害・権限 (scale {scale})\n")
        print("\n".join(checks_table(scale)) or "(結果なし)")


if __name__ == "__main__":
    main()
