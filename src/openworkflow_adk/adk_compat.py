"""Consolidated compatibility seam over Google ADK private workflow APIs.

Several modules need ADK's internal workflow primitives (``FunctionNode``,
``DEFAULT_ROUTE``, ``JoinNode``) plus the public ``Workflow`` graph class.
Importing the private ``google.adk.workflow._*`` modules directly from nine
places makes upgrades fragile; this module is the single point that must change
when ADK renames or moves them. The nightly canary CI job (see
``.github/workflows/canary.yml``) runs the full suite against the latest ADK to
detect drift here early.
"""

from __future__ import annotations

from google.adk.workflow import Workflow
from google.adk.workflow._function_node import FunctionNode
from google.adk.workflow._graph import DEFAULT_ROUTE
from google.adk.workflow._join_node import JoinNode

__all__ = ["Workflow", "FunctionNode", "DEFAULT_ROUTE", "JoinNode"]
