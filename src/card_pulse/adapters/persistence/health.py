"""Check that the PostgreSQL service accepts a connection.

ADR-0014 fixes psycopg 3 as the driver, so the check belongs in the persistence
adapter: domain and application code keep no knowledge of the database product.
"""

from __future__ import annotations

import psycopg

from card_pulse.application.health import DATABASE, DependencyStatus

DEFAULT_CONNECT_TIMEOUT_SECONDS = 5


def probe_database(
    dsn: str, *, connect_timeout: int = DEFAULT_CONNECT_TIMEOUT_SECONDS
) -> DependencyStatus:
    """Open a connection, run ``SELECT 1``, and report whether the server answered."""
    try:
        with (
            psycopg.connect(dsn, connect_timeout=connect_timeout, autocommit=True) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except psycopg.Error as error:
        return DependencyStatus(name=DATABASE, healthy=False, detail=_describe(error))
    return DependencyStatus(name=DATABASE, healthy=True, detail="connection accepted")


def _describe(error: psycopg.Error) -> str:
    """Summarise a driver error in one line, without echoing the connection string."""
    lines = str(error).strip().splitlines()
    return f"{type(error).__name__}: {lines[0] if lines else 'no detail reported'}"
