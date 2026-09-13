"""Hold the storage rules of ADR-0022 in place.

Configuration arrives as environment variables, secrets live only in ``.env``, and every
piece of local data belongs under ``var/``. Nothing in that arrangement fails loudly on
its own: a committed secret, a raw artifact added to the index, or a runtime default that
writes outside ``var/`` all keep the application working while breaking the rule. These
tests read the index and the ignore rules so that such a change fails in CI instead.
"""

import subprocess
from pathlib import Path

import pytest

from card_pulse.entrypoints.settings import DEFAULT_ARTIFACT_ROOT, DEFAULT_HEARTBEAT_PATH

ROOT = Path(__file__).resolve().parents[2]
LOCAL_DATA = Path("var")
CONFIGURATION = Path("config")

# ADR-0022 fixes these layers. A component that has no writer yet still keeps its place.
DATA_LAYERS = ("var/raw", "var/logs", "var/db", "var/review")

pytestmark = pytest.mark.skipif(
    not (ROOT / ".git").exists(), reason="the checks read the Git index of this repository"
)


def _git(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=False
    )


def _is_ignored(path: str) -> bool:
    """Report whether Git would ignore this path, whether or not it exists."""
    return _git("check-ignore", "--quiet", path).returncode == 0


def test_local_data_and_configuration_track_only_placeholders() -> None:
    """A raw artifact or a local database must never reach the index (ADR-0012)."""
    tracked = _git("ls-files", str(LOCAL_DATA), str(CONFIGURATION)).stdout.split()

    assert tracked, "nothing is tracked there at all, so the check proves nothing"
    unexpected = [path for path in tracked if Path(path).name != ".gitkeep"]
    assert not unexpected, f"tracked outside the placeholders: {unexpected}"


def test_every_documented_data_layer_exists() -> None:
    for layer in DATA_LAYERS:
        assert (ROOT / layer).is_dir(), f"{layer} is documented in ADR-0022 but missing"


def test_secrets_and_local_data_are_ignored() -> None:
    """The example file is the one thing under these names that belongs in the repository."""
    for path in (".env", ".env.local", "var/raw/page.html", "var/db-poc/measurement.csv"):
        assert _is_ignored(path), f"{path} would be committable"

    assert not _is_ignored(".env.example"), ".env.example is no longer tracked as the template"


def test_runtime_defaults_write_inside_the_local_data_area() -> None:
    """Running the Worker on the host, without Compose, must not scatter files elsewhere."""
    for default in (DEFAULT_ARTIFACT_ROOT, DEFAULT_HEARTBEAT_PATH):
        assert LOCAL_DATA in default.parents, f"{default} is written outside {LOCAL_DATA}"
