"""Check that the API answers its health routes and survives a failed dependency."""

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

import pytest

from card_pulse.application.health import DependencyProbe, DependencyStatus
from card_pulse.entrypoints.api.server import HealthServer

TIMEOUT_SECONDS = 5.0


def _probe(name: str, healthy: bool) -> DependencyProbe:
    return lambda: DependencyStatus(name=name, healthy=healthy, detail="stub")


@contextmanager
def _running(probes: Sequence[DependencyProbe]) -> Iterator[str]:
    server = HealthServer(("127.0.0.1", 0), probes)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.bound_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=TIMEOUT_SECONDS)
        server.server_close()


def _get(url: str) -> tuple[int, dict[str, Any]]:
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
        return response.status, json.loads(response.read())


def test_liveness_does_not_depend_on_the_database() -> None:
    """A failing dependency must not make the API look dead to the container runtime."""
    with _running([_probe("database", False)]) as base_url:
        status, payload = _get(f"{base_url}/health")

    assert status == 200
    assert payload == {"service": "api", "status": "ok"}


def test_dependency_route_reports_each_probe() -> None:
    with _running([_probe("database", True)]) as base_url:
        status, payload = _get(f"{base_url}/health/dependencies")

    assert status == 200
    assert payload["status"] == "ok"
    assert payload["dependencies"] == [{"name": "database", "healthy": True, "detail": "stub"}]


def test_dependency_route_answers_200_while_degraded() -> None:
    """The outage has to be readable, so it is reported in the body, not as a 5xx."""
    with _running([_probe("database", False)]) as base_url:
        status, payload = _get(f"{base_url}/health/dependencies")

    assert status == 200
    assert payload["status"] == "degraded"


def test_unknown_route_is_not_found() -> None:
    with _running([]) as base_url, pytest.raises(urllib.error.HTTPError) as error:
        _get(f"{base_url}/prices")

    assert error.value.code == 404
