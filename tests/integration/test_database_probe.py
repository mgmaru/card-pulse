"""Check the database probe against a running PostgreSQL service.

These tests need the Compose environment. Start it, then run pytest with the connection
string, as described in the local development Runbook:

    CARD_PULSE_DATABASE_URL=postgresql://card_pulse_api:...@127.0.0.1:5432/card_pulse \\
        uv run --locked pytest tests/integration

Without that variable the module is skipped, so the suite stays runnable offline and in
CI, where no database service exists yet.
"""

import os

import pytest

from card_pulse.adapters.persistence.health import probe_database

DSN = os.environ.get("CARD_PULSE_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not DSN, reason="set CARD_PULSE_DATABASE_URL to run against the Compose database"
)


def test_a_running_database_accepts_the_configured_role() -> None:
    status = probe_database(DSN)

    assert status.healthy, status.detail
    assert status.name == "database"


def test_an_unreachable_database_is_reported_in_one_line() -> None:
    """A failed probe must stay readable in a log record and must not echo the DSN."""
    status = probe_database("postgresql://card_pulse@127.0.0.1:1/card_pulse", connect_timeout=2)

    assert not status.healthy
    assert "\n" not in status.detail
