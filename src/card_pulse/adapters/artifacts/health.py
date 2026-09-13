"""Check that the directory holding raw artifacts can be written.

The Worker must store an artifact before parsing it (ADR-0002). A read-only or missing
storage mount has to surface as a dependency failure rather than as a lost fetch.
"""

from __future__ import annotations

import os
from pathlib import Path

from card_pulse.application.health import ARTIFACT_STORAGE, DependencyStatus


def probe_artifact_storage(root: Path) -> DependencyStatus:
    """Create the artifact root if needed, then write and remove a probe file."""
    probe_file = root / f".write-probe-{os.getpid()}"
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe_file.write_bytes(b"")
        probe_file.unlink()
    except OSError as error:
        detail = f"{type(error).__name__}: {error.strerror or error}"
        return DependencyStatus(name=ARTIFACT_STORAGE, healthy=False, detail=detail)
    return DependencyStatus(name=ARTIFACT_STORAGE, healthy=True, detail=f"{root} is writable")
