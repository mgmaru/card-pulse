"""Guard the local Compose environment against changes that break a recorded decision.

The build and start-up itself is checked by ``CP-0061`` on a runner with Docker. These
tests cover what can be read from the files alone and is easy to lose in an edit: the
publication boundary of ADR-0012, the digest pinning of ADR-0014, and the promise that
``.env.example`` lists every variable the environment needs.
"""

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = ROOT / "compose.yaml"
DOCKERFILE = ROOT / "Dockerfile"
ENV_EXAMPLE = ROOT / ".env.example"

VARIABLE_REFERENCE = re.compile(r"\$\{([A-Z0-9_]+)")
ENV_ASSIGNMENT = re.compile(r"^([A-Z0-9_]+)=", re.MULTILINE)
FROM_LINE = re.compile(r"^FROM\s+(\S+)", re.MULTILINE)


@pytest.fixture(scope="module")
def compose() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    return loaded


@pytest.fixture(scope="module")
def services(compose: dict[str, Any]) -> dict[str, Any]:
    found: dict[str, Any] = compose["services"]
    return found


def test_the_topology_has_one_service_per_runtime_role(services: dict[str, Any]) -> None:
    assert set(services) == {"api", "worker", "db"}


def test_pulled_images_are_pinned_by_digest(services: dict[str, Any]) -> None:
    """ADR-0014 requires the OS variant and the digest, not a moving tag."""
    for name, service in services.items():
        if "build" in service:
            continue
        assert "@sha256:" in service["image"], f"{name} does not pin an image digest"


def test_base_images_are_pinned_by_digest() -> None:
    stages = FROM_LINE.findall(DOCKERFILE.read_text(encoding="utf-8"))

    assert stages, "the Dockerfile declares no build stage"
    for reference in stages:
        assert "@sha256:" in reference, f"{reference} does not pin an image digest"


def test_every_published_port_binds_to_the_host_loopback(services: dict[str, Any]) -> None:
    """ADR-0012: nothing in this environment may be reachable from outside the host."""
    published = [
        (name, entry) for name, service in services.items() for entry in service.get("ports", [])
    ]

    assert published, "no service publishes a port, so the check proves nothing"
    for name, entry in published:
        assert str(entry).startswith("127.0.0.1:"), f"{name} publishes {entry} beyond loopback"


def test_the_application_services_wait_for_a_healthy_database(services: dict[str, Any]) -> None:
    for name in ("api", "worker"):
        assert services[name]["depends_on"]["db"]["condition"] == "service_healthy"


def test_every_service_reports_its_own_health(services: dict[str, Any]) -> None:
    for name, service in services.items():
        assert service.get("healthcheck"), f"{name} has no health check"


def test_only_the_worker_mounts_the_artifact_storage(services: dict[str, Any]) -> None:
    """The API reads observations from the database, never the stored originals."""
    assert _named_volumes(services["worker"]) == {"artifacts"}
    assert _named_volumes(services["api"]) == set()


def test_named_volumes_are_declared(compose: dict[str, Any]) -> None:
    declared = set(compose["volumes"])
    used = {
        volume for service in compose["services"].values() for volume in _named_volumes(service)
    }

    assert used <= declared


def test_env_example_documents_every_variable_the_environment_reads() -> None:
    referenced = set(VARIABLE_REFERENCE.findall(COMPOSE_FILE.read_text(encoding="utf-8")))
    documented = set(ENV_ASSIGNMENT.findall(ENV_EXAMPLE.read_text(encoding="utf-8")))

    assert referenced, "compose.yaml reads no variable, so the check proves nothing"
    assert referenced <= documented, f"undocumented: {sorted(referenced - documented)}"


def test_env_example_holds_no_secret_value() -> None:
    """The file is committed, so every secret entry stays empty."""
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        if "PASSWORD" in line and not line.startswith("#"):
            assert line.endswith("="), f"{line} carries a value"


def _named_volumes(service: dict[str, Any]) -> set[str]:
    """Return the named volumes a service mounts, ignoring bind mounts from the repository."""
    return {
        str(entry).split(":", 1)[0]
        for entry in service.get("volumes", [])
        if not str(entry).startswith(".")
    }
