"""Story 2.12: Resolves data resource paths in both dev and PyInstaller onedir bundles.

In a PyInstaller onedir bundle, sys.frozen=True and sys._MEIPASS points to the
extracted bundle root. In dev mode, paths are resolved relative to the source tree.

Use _sys as an injectable dependency to allow tests to simulate bundled mode
without actually running inside PyInstaller.
"""
from __future__ import annotations

import sys as _sys_module
import types
from pathlib import Path

# Indirection allows tests to patch _sys with a SimpleNamespace(frozen=True, _MEIPASS=…)
_sys: types.ModuleType = _sys_module


def _is_bundled() -> bool:
    """Return True when running inside a PyInstaller onedir bundle."""
    return getattr(_sys, "frozen", False) and hasattr(_sys, "_MEIPASS")


def _meipass() -> Path:
    return Path(_sys._MEIPASS)  # type: ignore[attr-defined]


def contracts_dir() -> Path:
    """Return the contracts base directory (contains a schemas/ subdirectory).

    Bundle layout:  <_MEIPASS>/contracts/schemas/*.json
    Source layout:  <project_root>/packages/contracts/schemas/*.json
    """
    if _is_bundled():
        return _meipass() / "contracts"
    # engine/gracetree_engine/resource_resolver.py
    #   parents[0] = gracetree_engine/
    #   parents[1] = engine/
    #   parents[2] = project root
    return Path(__file__).resolve().parents[2] / "packages" / "contracts"


def migrations_dir() -> Path:
    """Return the migrations directory.

    Bundle layout:  <_MEIPASS>/migrations/*.sql
    Source layout:  <engine_root>/migrations/*.sql
    """
    if _is_bundled():
        return _meipass() / "migrations"
    # parents[1] = engine/
    return Path(__file__).resolve().parents[1] / "migrations"
