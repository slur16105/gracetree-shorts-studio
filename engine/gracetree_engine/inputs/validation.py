"""
Script input validation utilities for Story 1.6.

The ``validate_script`` CLI command calls the validator directly.
This module is reserved for future wrapper / composition functions
(e.g. combining script validation with input-record lookups in Story 2.x).
"""
from __future__ import annotations

from gracetree_engine.scripts.validator import validate_script as validate_script  # noqa: F401

__all__: list[str] = []
