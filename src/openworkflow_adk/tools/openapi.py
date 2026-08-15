"""Backward-compatible facade for :mod:`openworkflow_adk.interop.openapi`.

The ``tools`` package was split into ``interop`` (cross-runtime formats) and
``devtools`` (diagnostics/devUX) under C24.25. This module re-exports the
implementation for existing callers; new code should import from the new
location.
"""

from openworkflow_adk.interop.openapi import export_openapi, generate_openapi

__all__ = ["export_openapi", "generate_openapi"]
