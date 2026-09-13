"""Check the Worker heartbeat that the container health check reads."""

import json
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from card_pulse.application.health import DependencyStatus, HealthReport
from card_pulse.entrypoints.settings import WorkerSettings
from card_pulse.entrypoints.worker import service
from card_pulse.entrypoints.worker.healthcheck import heartbeat_age_seconds
from card_pulse.entrypoints.worker.service import run, write_heartbeat

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)


def _report(healthy: bool) -> HealthReport:
    return HealthReport((DependencyStatus(name="database", healthy=healthy, detail="stub"),))


def test_heartbeat_records_the_check_time_and_each_dependency(tmp_path: Path) -> None:
    path = tmp_path / "state" / "worker-heartbeat.json"

    write_heartbeat(path, _report(healthy=False), NOW)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["service"] == "worker"
    assert payload["status"] == "degraded"
    assert payload["checked_at"] == NOW.isoformat()
    assert payload["dependencies"][0]["name"] == "database"


def test_heartbeat_replaces_the_previous_file_without_leaving_a_temporary(
    tmp_path: Path,
) -> None:
    path = tmp_path / "worker-heartbeat.json"

    write_heartbeat(path, _report(healthy=True), NOW)
    write_heartbeat(path, _report(healthy=True), NOW + timedelta(seconds=30))

    assert [entry.name for entry in tmp_path.iterdir()] == ["worker-heartbeat.json"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["checked_at"] == (NOW + timedelta(seconds=30)).isoformat()


def test_heartbeat_age_is_measured_from_the_recorded_time(tmp_path: Path) -> None:
    path = tmp_path / "worker-heartbeat.json"
    write_heartbeat(path, _report(healthy=True), NOW)

    assert heartbeat_age_seconds(path, NOW + timedelta(seconds=45)) == 45.0


def test_a_degraded_heartbeat_still_counts_as_alive(tmp_path: Path) -> None:
    """Losing the database must not restart a Worker that is reporting the outage."""
    path = tmp_path / "worker-heartbeat.json"
    write_heartbeat(path, _report(healthy=False), NOW)

    assert heartbeat_age_seconds(path, NOW) == 0.0


def test_a_missing_heartbeat_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot be read"):
        heartbeat_age_seconds(tmp_path / "absent.json", NOW)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("not json", "not valid JSON"),
        ('{"service": "worker"}', "no checked_at"),
        ('{"checked_at": "yesterday"}', "unreadable checked_at"),
        ('{"checked_at": "2026-09-13T12:00:00"}', "without a timezone"),
    ],
)
def test_an_unusable_heartbeat_is_rejected(tmp_path: Path, content: str, message: str) -> None:
    path = tmp_path / "worker-heartbeat.json"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        heartbeat_age_seconds(path, NOW)


def test_the_worker_writes_a_heartbeat_before_waiting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first cycle runs immediately so the health check has something to read."""
    monkeypatch.setattr(
        service,
        "probe_database",
        lambda dsn: DependencyStatus(name="database", healthy=False, detail="stub"),
    )
    settings = WorkerSettings(
        database_url="postgresql://user@db:5432/card_pulse",
        artifact_root=tmp_path / "artifacts",
        heartbeat_path=tmp_path / "worker-heartbeat.json",
        interval_seconds=30.0,
    )
    stop = threading.Event()
    stop.set()

    assert run(settings, stop) == 0
    payload = json.loads(settings.heartbeat_path.read_text(encoding="utf-8"))
    assert payload["status"] == "degraded"
    assert [dependency["name"] for dependency in payload["dependencies"]] == [
        "database",
        "artifact-storage",
    ]
