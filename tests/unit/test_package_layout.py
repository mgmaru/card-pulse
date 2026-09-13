"""Verify that the package skeleton declared in the architecture overview stays importable."""

import importlib

import pytest

PACKAGES = [
    "card_pulse",
    "card_pulse.domain",
    "card_pulse.application",
    "card_pulse.adapters",
    "card_pulse.adapters.sources",
    "card_pulse.adapters.sources.manual",
    "card_pulse.adapters.persistence",
    "card_pulse.adapters.artifacts",
    "card_pulse.entrypoints",
    "card_pulse.entrypoints.api",
    "card_pulse.entrypoints.worker",
    "card_pulse.entrypoints.cli",
]


@pytest.mark.parametrize("name", PACKAGES)
def test_package_is_importable(name: str) -> None:
    assert importlib.import_module(name).__name__ == name


def test_version_is_exported() -> None:
    import card_pulse

    assert card_pulse.__version__
