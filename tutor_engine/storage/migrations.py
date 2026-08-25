"""Forward-only JSON schema migrations at the persistence boundary."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = 1
DOCUMENT_KINDS = frozenset(
    {"graph", "learner", "quiz", "attempt", "session", "blueprint"}
)


class SchemaError(ValueError):
    """Raised when a persisted document cannot be migrated safely."""


def migrate_payload(payload: Mapping[str, Any], kind: str) -> dict[str, Any]:
    if kind not in DOCUMENT_KINDS:
        raise SchemaError(f"unsupported document kind: {kind}")
    value = deepcopy(dict(payload))
    version = value.get("schema_version", 0)
    if isinstance(version, bool) or not isinstance(version, int) or version < 0:
        raise SchemaError("schema_version must be a non-negative integer")
    if version > SCHEMA_VERSION:
        raise SchemaError(
            f"document schema {version} is newer than supported schema {SCHEMA_VERSION}"
        )
    if version == 0:
        _migrate_v0_to_v1(value, kind)
        version = 1
    if version != SCHEMA_VERSION:
        raise SchemaError(f"no migration path from schema {version}")
    value["schema_version"] = SCHEMA_VERSION
    return value


def _migrate_v0_to_v1(value: dict[str, Any], kind: str) -> None:
    if kind == "learner":
        value.setdefault("active_session_id", None)
        for state in value.get("concepts", {}).values():
            state.setdefault(
                "review", {"stage": 0, "last_review": None, "next_review": None}
            )
    elif kind == "quiz":
        value.setdefault("purpose", "learning")
    elif kind == "attempt":
        value.setdefault("purpose", "learning")
    elif kind == "session":
        value.setdefault("events", [])
