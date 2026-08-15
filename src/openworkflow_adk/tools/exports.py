"""Backward-compatible facade for :mod:`openworkflow_adk.interop.exports`.

The ``tools`` package was split into ``interop`` (cross-runtime formats) and
``devtools`` (diagnostics/devUX) under C24.25. This module re-exports the
implementation for existing callers; new code should import from the new
location.
"""

from openworkflow_adk.interop.exports import export_temporal

__all__ = ["export_temporal"]
