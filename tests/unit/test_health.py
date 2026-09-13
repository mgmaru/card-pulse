"""Check how dependency results are aggregated and how the artifact probe reports."""

from pathlib import Path

from card_pulse.adapters.artifacts.health import probe_artifact_storage
from card_pulse.application.health import (
    ARTIFACT_STORAGE,
    DependencyProbe,
    DependencyStatus,
    check_dependencies,
    describe,
)


def _status(name: str, healthy: bool) -> DependencyProbe:
    return lambda: DependencyStatus(name=name, healthy=healthy, detail="stub")


def test_report_is_healthy_only_when_every_dependency_is() -> None:
    assert check_dependencies([_status("a", True), _status("b", True)]).healthy
    assert not check_dependencies([_status("a", True), _status("b", False)]).healthy


def test_report_keeps_probe_order() -> None:
    report = check_dependencies([_status("first", True), _status("second", False)])

    assert [dependency.name for dependency in report.dependencies] == ["first", "second"]


def test_report_with_no_probes_is_healthy() -> None:
    assert check_dependencies([]).healthy


def test_describe_names_the_failing_dependency() -> None:
    report = check_dependencies([_status("database", False), _status("artifact-storage", True)])

    assert describe(report.dependencies) == "database=failed, artifact-storage=ok"


def test_artifact_probe_creates_a_missing_root(tmp_path: Path) -> None:
    root = tmp_path / "artifacts" / "raw"

    status = probe_artifact_storage(root)

    assert status.healthy
    assert status.name == ARTIFACT_STORAGE
    assert root.is_dir()


def test_artifact_probe_leaves_no_probe_file_behind(tmp_path: Path) -> None:
    probe_artifact_storage(tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_artifact_probe_reports_an_unusable_root(tmp_path: Path) -> None:
    occupied = tmp_path / "not-a-directory"
    occupied.write_text("", encoding="utf-8")

    status = probe_artifact_storage(occupied)

    assert not status.healthy
    assert status.name == ARTIFACT_STORAGE
