"""Serve the health endpoints of the Card Pulse API.

The API contract, authentication, and the framework that will carry them are decided in
Phase 4 (``CP-0034``, ``CP-0036``). Until then this entrypoint exists so that the Compose
topology has a real API service to start, and so that the isolation ADR-0005 and
ADR-0012 rely on can be observed: the API keeps answering while the database is down.

Two routes with different meanings:

``GET /health``
    Liveness. Answers as long as the process serves requests, and is what the container
    health check calls. It does not touch the database.
``GET /health/dependencies``
    The state of each dependency. Always returns 200 so that a database outage is
    reported rather than mistaken for a dead API.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Sequence
from dataclasses import asdict
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast
from urllib.parse import urlsplit

from card_pulse.adapters.persistence.health import probe_database
from card_pulse.application.health import DependencyProbe, check_dependencies, describe
from card_pulse.entrypoints.runtime import (
    configure_logging,
    install_shutdown_handlers,
    wait_for_shutdown,
)
from card_pulse.entrypoints.settings import ApiSettings, SettingsError

logger = logging.getLogger("card_pulse.api")

SHUTDOWN_TIMEOUT_SECONDS = 5.0


class HealthServer(ThreadingHTTPServer):
    """HTTP server that hands its dependency probes to each request handler."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], probes: Sequence[DependencyProbe]) -> None:
        super().__init__(address, _HealthHandler)
        self.probes = probes

    @property
    def bound_address(self) -> tuple[str, int]:
        """Report the address actually bound, which differs when port 0 is requested."""
        host, port = self.socket.getsockname()[:2]
        return str(host), int(port)


class _HealthHandler(BaseHTTPRequestHandler):
    server_version = "card-pulse"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        route = urlsplit(self.path).path.rstrip("/") or "/"
        if route == "/health":
            self._write(HTTPStatus.OK, {"service": "api", "status": "ok"})
        elif route == "/health/dependencies":
            report = check_dependencies(cast(HealthServer, self.server).probes)
            self._write(
                HTTPStatus.OK,
                {
                    "service": "api",
                    "status": "ok" if report.healthy else "degraded",
                    "dependencies": [asdict(status) for status in report.dependencies],
                },
            )
        else:
            self._write(HTTPStatus.NOT_FOUND, {"error": "unknown route"})

    def _write(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("%s %s", self.address_string(), format % args)


def build_probes(settings: ApiSettings) -> list[DependencyProbe]:
    """Wire the adapters the API depends on. The API reads the database, not artifacts."""
    return [partial(probe_database, settings.database_url)]


def serve(settings: ApiSettings) -> int:
    """Run the server until a shutdown signal arrives."""
    server = HealthServer((settings.host, settings.port), build_probes(settings))
    stop = threading.Event()
    install_shutdown_handlers(stop, logger)

    worker_thread = threading.Thread(target=server.serve_forever, name="card-pulse-api")
    worker_thread.start()
    host, port = server.bound_address
    logger.info("API listening on http://%s:%s", host, port)
    logger.info("dependencies: %s", describe(check_dependencies(server.probes).dependencies))
    try:
        wait_for_shutdown(stop)
    finally:
        server.shutdown()
        worker_thread.join(timeout=SHUTDOWN_TIMEOUT_SECONDS)
        server.server_close()
    logger.info("API stopped")
    return 0


def main() -> int:
    configure_logging()
    try:
        settings = ApiSettings.from_environment()
    except SettingsError as error:
        logger.error("%s", error)
        return 2
    return serve(settings)
