"""Start the Collection Worker: ``python -m card_pulse.entrypoints.worker``."""

from card_pulse.entrypoints.worker.service import main

if __name__ == "__main__":
    raise SystemExit(main())
