"""Read the runtime settings that the API and Worker entrypoints need.

Every value arrives as an environment variable so that the same image runs unchanged on
the owner's machine, under Docker Compose, and in CI. ADR-0022 keeps that the only
entrance: secrets live in the local ``.env`` that Compose turns into these variables, and
no process reads a configuration file. This module only reads what it was given and fails
loudly when a required value is absent.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DATABASE_URL = "CARD_PULSE_DATABASE_URL"
API_HOST = "CARD_PULSE_API_HOST"
API_PORT = "CARD_PULSE_API_PORT"
ARTIFACT_ROOT = "CARD_PULSE_ARTIFACT_ROOT"
WORKER_HEARTBEAT_PATH = "CARD_PULSE_WORKER_HEARTBEAT_PATH"
WORKER_INTERVAL_SECONDS = "CARD_PULSE_WORKER_INTERVAL_SECONDS"

# ADR-0012 keeps the API off the network by default. Compose overrides the bind address
# with 0.0.0.0 because inside a container the network boundary is the container itself,
# and the published port is bound to the host loopback instead.
DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8000
DEFAULT_ARTIFACT_ROOT = Path("var/raw")
DEFAULT_HEARTBEAT_PATH = Path("var/logs/worker-heartbeat.json")
DEFAULT_INTERVAL_SECONDS = 30.0

# Three missed cycles, with a floor for very short intervals, before a heartbeat counts
# as stale. A single slow cycle must not restart a healthy worker.
MISSED_CYCLES_BEFORE_STALE = 3
MINIMUM_HEARTBEAT_MAX_AGE_SECONDS = 15.0


class SettingsError(RuntimeError):
    """Raised when a required environment variable is missing or cannot be parsed."""


def _environment(environ: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if environ is None else environ


def _required(environ: Mapping[str, str], name: str) -> str:
    value = environ.get(name, "").strip()
    if not value:
        raise SettingsError(f"{name} is required but was not set")
    return value


def _positive_number(environ: Mapping[str, str], name: str, default: float) -> float:
    raw = environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as error:
        raise SettingsError(f"{name} must be a number, got {raw!r}") from error
    if value <= 0:
        raise SettingsError(f"{name} must be greater than zero, got {raw!r}")
    return value


def api_port(environ: Mapping[str, str] | None = None) -> int:
    """Read the API port on its own, for callers such as the container health check."""
    source = _environment(environ)
    raw = source.get(API_PORT, "").strip()
    if not raw:
        return DEFAULT_API_PORT
    try:
        port = int(raw)
    except ValueError as error:
        raise SettingsError(f"{API_PORT} must be an integer, got {raw!r}") from error
    if not 1 <= port <= 65535:
        raise SettingsError(f"{API_PORT} must be a TCP port number, got {raw!r}")
    return port


def worker_heartbeat_path(environ: Mapping[str, str] | None = None) -> Path:
    """Read the heartbeat path on its own, for callers such as the health check."""
    source = _environment(environ)
    raw = source.get(WORKER_HEARTBEAT_PATH, "").strip()
    return Path(raw) if raw else DEFAULT_HEARTBEAT_PATH


def worker_interval_seconds(environ: Mapping[str, str] | None = None) -> float:
    """Read the worker cycle length on its own, for callers such as the health check."""
    return _positive_number(
        _environment(environ), WORKER_INTERVAL_SECONDS, DEFAULT_INTERVAL_SECONDS
    )


def heartbeat_max_age_seconds(interval_seconds: float) -> float:
    """Return the age at which a heartbeat written every ``interval_seconds`` is stale."""
    return max(interval_seconds * MISSED_CYCLES_BEFORE_STALE, MINIMUM_HEARTBEAT_MAX_AGE_SECONDS)


@dataclass(frozen=True, slots=True)
class ApiSettings:
    """Everything the API entrypoint reads from its environment."""

    host: str
    port: int
    database_url: str

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> ApiSettings:
        source = _environment(environ)
        return cls(
            host=source.get(API_HOST, "").strip() or DEFAULT_API_HOST,
            port=api_port(source),
            database_url=_required(source, DATABASE_URL),
        )


@dataclass(frozen=True, slots=True)
class WorkerSettings:
    """Everything the Worker entrypoint reads from its environment."""

    database_url: str
    artifact_root: Path
    heartbeat_path: Path
    interval_seconds: float

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> WorkerSettings:
        source = _environment(environ)
        raw_root = source.get(ARTIFACT_ROOT, "").strip()
        return cls(
            database_url=_required(source, DATABASE_URL),
            artifact_root=Path(raw_root) if raw_root else DEFAULT_ARTIFACT_ROOT,
            heartbeat_path=worker_heartbeat_path(source),
            interval_seconds=worker_interval_seconds(source),
        )
