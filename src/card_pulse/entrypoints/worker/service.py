"""Run the Collection Worker process.

No ingestion job exists yet: the first source adapter arrives in ``CP-0024``. Until then
the Worker still has to be a real, long-running service, because that is what lets the
Compose topology and ``CP-0061`` show API, Worker, and database failing independently.

Each cycle checks the database and the artifact storage the Worker will use, then writes
a heartbeat file that the container health check reads. The heartbeat records liveness,
not dependency health: losing the database must not restart a Worker that is running
correctly and reporting the outage.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict
from datetime import UTC, datetime
from functools import partial
from pathlib import Path

from card_pulse.adapters.artifacts.health import probe_artifact_storage
from card_pulse.adapters.persistence.health import probe_database
from card_pulse.application.health import (
    DependencyProbe,
    HealthReport,
    check_dependencies,
    describe,
)
from card_pulse.entrypoints.runtime import configure_logging, install_shutdown_handlers
from card_pulse.entrypoints.settings import SettingsError, WorkerSettings

logger = logging.getLogger("card_pulse.worker")


def build_probes(settings: WorkerSettings) -> list[DependencyProbe]:
    """Wire the adapters the Worker depends on: the database and the artifact storage."""
    return [
        partial(probe_database, settings.database_url),
        partial(probe_artifact_storage, settings.artifact_root),
    ]


def write_heartbeat(path: Path, report: HealthReport, checked_at: datetime) -> None:
    """Replace the heartbeat file atomically so a reader never sees a partial write."""
    payload = {
        "service": "worker",
        "checked_at": checked_at.isoformat(),
        "status": "ok" if report.healthy else "degraded",
        "dependencies": [asdict(status) for status in report.dependencies],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def run(settings: WorkerSettings, stop: threading.Event) -> int:
    """Check dependencies and write a heartbeat until ``stop`` is set."""
    logger.info(
        "worker started: artifacts=%s heartbeat=%s interval=%ss",
        settings.artifact_root,
        settings.heartbeat_path,
        settings.interval_seconds,
    )
    logger.info("no ingestion job is implemented yet (CP-0024); idling between checks")
    while True:
        report = check_dependencies(build_probes(settings))
        write_heartbeat(settings.heartbeat_path, report, datetime.now(UTC))
        log = logger.info if report.healthy else logger.warning
        log("dependencies: %s", describe(report.dependencies))
        if stop.wait(settings.interval_seconds):
            break
    logger.info("worker stopped")
    return 0


def main() -> int:
    configure_logging()
    try:
        settings = WorkerSettings.from_environment()
    except SettingsError as error:
        logger.error("%s", error)
        return 2
    stop = threading.Event()
    install_shutdown_handlers(stop, logger)
    return run(settings, stop)
