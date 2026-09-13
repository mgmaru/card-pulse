"""Container health check for the API service.

Liveness only: it passes while the process answers ``/health``. Whether the database is
reachable is reported through ``/health/dependencies``, so an unreachable database does
not mark the API container itself as failed.
"""

from __future__ import annotations

import sys
import urllib.request
from http.client import HTTPException

from card_pulse.entrypoints.settings import SettingsError, api_port

REQUEST_TIMEOUT_SECONDS = 3.0


def main() -> int:
    try:
        port = api_port()
    except SettingsError as error:
        print(error, file=sys.stderr)
        return 2
    url = f"http://127.0.0.1:{port}/health"
    try:
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                print(f"{url} returned HTTP {response.status}", file=sys.stderr)
                return 1
    except (OSError, HTTPException) as error:
        print(f"{url} is not answering: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
