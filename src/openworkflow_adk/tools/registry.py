"""Backward-compatible facade for the workflow registry.

``WorkflowRegistry`` moved to the core :mod:`openworkflow_adk.registry` module
under C24.18 so the translator/runtime never import from ``tools`` (which sits
above core). This module re-exports the names for existing callers; new code
should import from :mod:`openworkflow_adk.registry`.
"""

from openworkflow_adk.registry import WorkflowRegistry, WorkflowSearchResult

__all__ = ["WorkflowRegistry", "WorkflowSearchResult"]
