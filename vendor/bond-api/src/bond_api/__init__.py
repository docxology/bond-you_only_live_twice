"""BOND-API — the frozen mission protocol contract for the BOND film suite.

Manuscript identity: BOND-API · codename THE PROTOCOL.

This package is Layer 1 of the BOND suite. It freezes the contract the 27
film packages implement (see :mod:`bond_api.protocol`) and ships the
supporting machinery every coordinator needs: registries
(:mod:`bond_api.registry`), slug-based film discovery
(:mod:`bond_api.discovery`), deterministic JSON round-trip serialization
(:mod:`bond_api.serialization`), and capability helpers layered on the frozen
surface (:mod:`bond_api.capabilities`).
"""

from __future__ import annotations

from bond_api.capabilities import (
    BriefReport,
    brief_issues,
    derive_provenance,
    fingerprint,
    hash_provenance,
    normalize_debrief,
    normalize_lessons,
    plan_schema_issues,
    require_plan_schema,
    validate_brief,
)
from bond_api.discovery import DiscoveryError, discover, load_provider
from bond_api.protocol import (
    Asset,
    CODENAME,
    Constraint,
    Debrief,
    Finding,
    IDENTITY,
    MISSION_FLOW,
    MissionBrief,
    MissionOutcome,
    MissionPlan,
    MissionProvider,
    Provenance,
    ReconReport,
    ReconRequest,
    Step,
    protocol_surface,
    run_mission,
)
from bond_api.registry import GadgetRegistry, MissionRegistry
from bond_api.serialization import (
    SERIALIZATION_TAG,
    SerializationError,
    from_dict,
    from_json,
    to_dict,
    to_json,
)

__version__ = "0.1.0"

#: Manuscript identity and codename (single source of truth: ``protocol.py``).
MANUSCRIPT_IDENTITY = IDENTITY
CODENAME = CODENAME

__all__ = [
    # Identity
    "MANUSCRIPT_IDENTITY",
    "CODENAME",
    "__version__",
    # Protocol surface
    "Asset",
    "Constraint",
    "Debrief",
    "Finding",
    "MISSION_FLOW",
    "MissionBrief",
    "MissionOutcome",
    "MissionPlan",
    "MissionProvider",
    "Provenance",
    "ReconReport",
    "ReconRequest",
    "Step",
    "protocol_surface",
    "run_mission",
    # Discovery
    "DiscoveryError",
    "discover",
    "load_provider",
    # Registries
    "GadgetRegistry",
    "MissionRegistry",
    # Serialization
    "SERIALIZATION_TAG",
    "SerializationError",
    "from_dict",
    "from_json",
    "to_dict",
    "to_json",
    # Capabilities
    "BriefReport",
    "brief_issues",
    "derive_provenance",
    "fingerprint",
    "hash_provenance",
    "normalize_debrief",
    "normalize_lessons",
    "plan_schema_issues",
    "require_plan_schema",
    "validate_brief",
]
