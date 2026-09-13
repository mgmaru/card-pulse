"""Process-level concerns shared by the API and Worker entrypoints."""

from __future__ import annotations

import logging
import os
import signal
import threading
from types import FrameType

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
LOG_LEVEL = "CARD_PULSE_LOG_LEVEL"


def configure_logging() -> None:
    """Send structured-enough records to stdout, where the container log collects them."""
    logging.basicConfig(
        level=os.environ.get(LOG_LEVEL, "INFO").upper(),
        format=LOG_FORMAT,
    )


def install_shutdown_handlers(stop: threading.Event, logger: logging.Logger) -> None:
    """Set ``stop`` when the container runtime asks the process to terminate.

    Docker sends SIGTERM and waits before SIGKILL, so both entrypoints end their current
    cycle and close their resources instead of being killed mid-write.
    """

    def handle(signum: int, frame: FrameType | None) -> None:
        logger.info("received %s, shutting down", signal.Signals(signum).name)
        stop.set()

    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, handle)


def wait_for_shutdown(stop: threading.Event, poll_seconds: float = 0.5) -> None:
    """Block the main thread until a shutdown signal arrives.

    The wait polls rather than blocking forever so that the signal handler always runs
    in the main thread while another thread owns the real work.
    """
    while not stop.wait(poll_seconds):
        pass
