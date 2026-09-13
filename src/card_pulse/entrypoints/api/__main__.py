"""Start the Card Pulse API: ``python -m card_pulse.entrypoints.api``."""

from card_pulse.entrypoints.api.server import main

if __name__ == "__main__":
    raise SystemExit(main())
