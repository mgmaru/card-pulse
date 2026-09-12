"""Shared configuration for the CP-0009 database PoC."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
POC_ROOT = REPO_ROOT / "var" / "db-poc"

DATA_DIR = POC_ROOT / "data"
ARTIFACT_DIR = POC_ROOT / "artifacts"
BACKUP_DIR = POC_ROOT / "backup"
RESULT_DIR = POC_ROOT / "results"
LOG_DIR = POC_ROOT / "logs"

PG_PORT = int(os.environ.get("POC_PG_PORT", "55432"))
PG_RESTORE_PORT = int(os.environ.get("POC_PG_RESTORE_PORT", "55433"))
MARIA_PORT = int(os.environ.get("POC_MARIA_PORT", "53306"))
MARIA_RESTORE_PORT = int(os.environ.get("POC_MARIA_RESTORE_PORT", "53307"))

PG_HOME = Path("/opt/homebrew/opt/postgresql@18")
MARIA_HOME = Path("/opt/homebrew/opt/mariadb")

DB_NAME = "card_pulse_poc"

# Role passwords are PoC-local only and never used outside this harness.
ROLE_PASSWORD = "poc_local_only"

ROLES = ("cp_api", "cp_worker", "cp_migration", "cp_backup", "cp_admin")

BACKUP_PASSPHRASE_FILE = POC_ROOT / "secret" / "backup.passphrase"


@dataclass(frozen=True)
class Profile:
    """Row counts for one load profile.

    The 28-day counts come from the initial load profile in
    docs/architecture/database-requirements.md. ``history_*`` adds one year of
    history for representative cards so DB-QRY-03 has a realistic target.
    """

    scale: int
    days: int = 28
    history_cards: int = 200
    history_days: int = 365
    history_shops: int = 3

    @property
    def raw_artifact(self) -> int:
        return 500 * self.days * self.scale

    @property
    def extracted_record(self) -> int:
        return 30_000 * self.days * self.scale

    @property
    def observation_candidate(self) -> int:
        return 30_000 * self.days * self.scale

    @property
    def identity_resolution_attempt(self) -> int:
        return 60_000 * self.days * self.scale

    @property
    def price_observation(self) -> int:
        return 30_000 * self.days * self.scale

    @property
    def review_item(self) -> int:
        return 3_000 * self.days * self.scale

    @property
    def history_rows(self) -> int:
        return self.history_cards * self.history_days * self.history_shops

    @property
    def cards(self) -> int:
        return 12_000 * self.scale

    @property
    def total_rows(self) -> int:
        return (
            self.raw_artifact
            + self.extracted_record
            + self.observation_candidate
            + self.identity_resolution_attempt
            + self.price_observation
            + self.review_item
            + self.history_rows
        )


PROFILES = {1: Profile(scale=1), 10: Profile(scale=10)}

SOURCES = [
    (1, "hareruya2", "web", "active"),
    (2, "yuyutei", "web", "active"),
    (3, "fullcomp-ikebukuro", "web", "active"),
    (4, "manual-import", "manual", "active"),
]

SHOPS = [
    (1, "hareruya2", "晴れる屋2"),
    (2, "yuyutei", "遊々亭"),
    (3, "fullcomp-ikebukuro", "フルコンプ池袋店"),
    (4, "manual", "手動取込"),
]

PRICE_TYPES = ("buy", "sell")
CONDITIONS = ("A", "B", "C", "PSA10")
CURRENCY = "JPY"
TCG = "pokemon"


def pg_dsn(role: str = "cp_admin", port: int | None = None, dbname: str = DB_NAME) -> str:
    return (
        f"postgresql://{role}:{ROLE_PASSWORD}@127.0.0.1:{port or PG_PORT}/{dbname}"
    )


def maria_dsn(role: str = "cp_admin", port: int | None = None, dbname: str = DB_NAME) -> str:
    return (
        f"mariadb+pymysql://{role}:{ROLE_PASSWORD}@127.0.0.1:{port or MARIA_PORT}/{dbname}"
    )


def dsn(engine: str, role: str = "cp_admin", port: int | None = None, dbname: str = DB_NAME) -> str:
    return pg_dsn(role, port, dbname) if engine == "postgres" else maria_dsn(role, port, dbname)


def ensure_dirs() -> None:
    for path in (DATA_DIR, ARTIFACT_DIR, BACKUP_DIR, RESULT_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)
