"""Aggregate the dependency checks that the API and Worker report.

The application layer owns the shape of a health report so that an entrypoint can
combine probes from different adapters without those adapters knowing about each
other. Probes themselves live next to the technology they touch.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

DATABASE = "database"
ARTIFACT_STORAGE = "artifact-storage"


@dataclass(frozen=True, slots=True)
class DependencyStatus:
    """Result of checking one runtime dependency."""

    name: str
    healthy: bool
    detail: str


DependencyProbe = Callable[[], DependencyStatus]


@dataclass(frozen=True, slots=True)
class HealthReport:
    """Result of checking every dependency at one point in time."""

    dependencies: tuple[DependencyStatus, ...]

    @property
    def healthy(self) -> bool:
        return all(dependency.healthy for dependency in self.dependencies)


def check_dependencies(probes: Iterable[DependencyProbe]) -> HealthReport:
    """Run every probe in the given order and collect the results.

    A probe reports failure as an unhealthy status rather than an exception, so one
    unreachable dependency never hides the state of the others.
    """
    return HealthReport(tuple(probe() for probe in probes))


def describe(dependencies: Sequence[DependencyStatus]) -> str:
    """Render a one-line summary suitable for a log record."""
    return ", ".join(
        f"{dependency.name}={'ok' if dependency.healthy else 'failed'}"
        for dependency in dependencies
    )
