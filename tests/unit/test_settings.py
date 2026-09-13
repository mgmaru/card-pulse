"""Check the environment contract that the API and Worker entrypoints depend on."""

from pathlib import Path

import pytest

from card_pulse.entrypoints.settings import (
    ApiSettings,
    SettingsError,
    WorkerSettings,
    api_port,
    heartbeat_max_age_seconds,
    worker_heartbeat_path,
    worker_interval_seconds,
)

MINIMAL = {"CARD_PULSE_DATABASE_URL": "postgresql://user@db:5432/card_pulse"}


def test_api_binds_to_loopback_unless_told_otherwise() -> None:
    """ADR-0012 keeps the API off the network by default; Compose widens it explicitly."""
    settings = ApiSettings.from_environment(MINIMAL)

    assert settings.host == "127.0.0.1"
    assert settings.port == 8000


def test_api_reads_an_explicit_bind_address() -> None:
    settings = ApiSettings.from_environment(
        MINIMAL | {"CARD_PULSE_API_HOST": "0.0.0.0", "CARD_PULSE_API_PORT": "9000"}
    )

    assert (settings.host, settings.port) == ("0.0.0.0", 9000)


def test_missing_database_url_is_an_error() -> None:
    with pytest.raises(SettingsError, match="CARD_PULSE_DATABASE_URL"):
        ApiSettings.from_environment({})


def test_blank_database_url_is_an_error() -> None:
    with pytest.raises(SettingsError, match="CARD_PULSE_DATABASE_URL"):
        ApiSettings.from_environment({"CARD_PULSE_DATABASE_URL": "   "})


@pytest.mark.parametrize("value", ["not-a-port", "0", "70000"])
def test_unusable_api_port_is_an_error(value: str) -> None:
    with pytest.raises(SettingsError, match="CARD_PULSE_API_PORT"):
        api_port({"CARD_PULSE_API_PORT": value})


def test_worker_defaults_stay_inside_the_git_ignored_var_directory() -> None:
    settings = WorkerSettings.from_environment(MINIMAL)

    assert settings.artifact_root == Path("var/raw")
    assert settings.heartbeat_path == Path("var/logs/worker-heartbeat.json")
    assert settings.interval_seconds == 30.0


def test_worker_reads_the_container_paths() -> None:
    settings = WorkerSettings.from_environment(
        MINIMAL
        | {
            "CARD_PULSE_ARTIFACT_ROOT": "/srv/card-pulse/artifacts",
            "CARD_PULSE_WORKER_HEARTBEAT_PATH": "/srv/card-pulse/state/worker-heartbeat.json",
            "CARD_PULSE_WORKER_INTERVAL_SECONDS": "5",
        }
    )

    assert settings.artifact_root == Path("/srv/card-pulse/artifacts")
    assert settings.heartbeat_path == Path("/srv/card-pulse/state/worker-heartbeat.json")
    assert settings.interval_seconds == 5.0


@pytest.mark.parametrize("value", ["never", "0", "-1"])
def test_unusable_worker_interval_is_an_error(value: str) -> None:
    with pytest.raises(SettingsError, match="CARD_PULSE_WORKER_INTERVAL_SECONDS"):
        worker_interval_seconds({"CARD_PULSE_WORKER_INTERVAL_SECONDS": value})


def test_health_check_helpers_read_the_same_variables_alone() -> None:
    """The container health check runs without the settings the service itself needs."""
    environ = {
        "CARD_PULSE_WORKER_HEARTBEAT_PATH": "/srv/card-pulse/state/worker-heartbeat.json",
        "CARD_PULSE_WORKER_INTERVAL_SECONDS": "20",
    }

    assert worker_heartbeat_path(environ) == Path("/srv/card-pulse/state/worker-heartbeat.json")
    assert worker_interval_seconds(environ) == 20.0


def test_a_short_interval_still_tolerates_one_slow_cycle() -> None:
    assert heartbeat_max_age_seconds(1.0) == 15.0
    assert heartbeat_max_age_seconds(30.0) == 90.0
