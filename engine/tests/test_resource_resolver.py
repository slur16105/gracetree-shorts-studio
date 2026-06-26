"""Story 2.12: Tests for resource_resolver — dev and bundled path resolution."""
from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

from gracetree_engine import resource_resolver


def test_contracts_dir_returns_path_in_dev_mode():
    d = resource_resolver.contracts_dir()
    assert isinstance(d, Path)
    # In dev mode: engine/gracetree_engine/resource_resolver.py → parents[2] = project root
    assert d.name == "contracts"


def test_contracts_schemas_exist_in_dev_mode():
    schemas = resource_resolver.contracts_dir() / "schemas"
    assert schemas.is_dir(), f"schemas dir missing: {schemas}"
    json_files = list(schemas.glob("*.json"))
    assert len(json_files) > 0, "no schema JSON files found"


def test_migrations_dir_returns_path_in_dev_mode():
    d = resource_resolver.migrations_dir()
    assert isinstance(d, Path)
    assert d.name == "migrations"


def test_migrations_sql_exist_in_dev_mode():
    sql_files = list(resource_resolver.migrations_dir().glob("*.sql"))
    assert len(sql_files) > 0, "no migration SQL files found"


def test_contracts_dir_uses_meipass_when_bundled(tmp_path):
    fake_meipass = tmp_path / "bundle"
    (fake_meipass / "contracts" / "schemas").mkdir(parents=True)

    fake_sys = types.SimpleNamespace(
        frozen=True,
        _MEIPASS=str(fake_meipass),
    )
    with patch.object(resource_resolver, "_sys", fake_sys):
        d = resource_resolver.contracts_dir()
    assert d == fake_meipass / "contracts"


def test_migrations_dir_uses_meipass_when_bundled(tmp_path):
    fake_meipass = tmp_path / "bundle"
    (fake_meipass / "migrations").mkdir(parents=True)

    fake_sys = types.SimpleNamespace(
        frozen=True,
        _MEIPASS=str(fake_meipass),
    )
    with patch.object(resource_resolver, "_sys", fake_sys):
        d = resource_resolver.migrations_dir()
    assert d == fake_meipass / "migrations"


def test_is_bundled_false_in_dev_mode():
    assert not resource_resolver._is_bundled()


def test_is_bundled_true_when_frozen(tmp_path):
    fake_sys = types.SimpleNamespace(frozen=True, _MEIPASS=str(tmp_path))
    with patch.object(resource_resolver, "_sys", fake_sys):
        assert resource_resolver._is_bundled()
