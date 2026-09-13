"""Container health check for the Worker service.

Liveness only: it passes while the heartbeat file is fresh. A degraded heartbeat, such
as one written while the database is unreachable, still counts as alive, because the
Worker is doing its job by reporting the outage.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from card_pulse.entrypoints.settings import (
    SettingsError,
    heartbeat_max_age_seconds,
    worker_heartbeat_path,
    worker_interval_seconds,
)


def heartbeat_age_seconds(path: Path, now: datetime) -> float:
    """Return how long ago the heartbeat was written.

    Raises:
        ValueError: the file is missing, unreadable, or does not hold a timestamp.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"{path} cannot be read: {error.strerror or error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"{path} is not valid JSON: {error}") from error
    if not isinstance(payload, dict) or "checked_at" not in payload:
        raise ValueError(f"{path} has no checked_at field")
    try:
        checked_at = datetime.fromisoformat(str(payload["checked_at"]))
    except ValueError as error:
        raise ValueError(f"{path} has an unreadable checked_at: {error}") from error
    if checked_at.tzinfo is None:
        raise ValueError(f"{path} has a checked_at without a timezone")
    return (now - checked_at).total_seconds()


def main() -> int:
    try:
        path = worker_heartbeat_path()
        max_age = heartbeat_max_age_seconds(worker_interval_seconds())
    except SettingsError as error:
        print(error, file=sys.stderr)
        return 2
    try:
        age = heartbeat_age_seconds(path, datetime.now(UTC))
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    if age > max_age:
        print(f"heartbeat is {age:.0f}s old, limit is {max_age:.0f}s", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
