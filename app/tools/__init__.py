"""Deterministic M3 tools. Keep calculations and transforms out of agent prose.

This package init must stay import-light. Importing ``app.tools.fingerprints``
must not load ADK tools or create a circular import with model manifests.
"""
