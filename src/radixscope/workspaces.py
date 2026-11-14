"""Canonical workspace identities shared by navigation, transfers and saved state."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkspaceDefinition:
    title: str
    label: str
    group: str
    navigation_order: int


WORKSPACES = (
    WorkspaceDefinition("Conversion", "Conversion", "Calculate", 4),
    WorkspaceDefinition("Trace", "Trace", "Calculate", 6),
    WorkspaceDefinition("Programmer", "Integer operations", "Inspect", 3),
    WorkspaceDefinition("IEEE 754", "IEEE 754", "Inspect", 2),
    WorkspaceDefinition("Number Inspector", "Number Inspector", "Inspect", 0),
    WorkspaceDefinition("Byte Inspector", "Byte Inspector", "Inspect", 1),
    WorkspaceDefinition("Batch Conversion", "Batch Conversion", "Calculate", 5),
)
LEGACY_WORKSPACE_ORDER = (
    "Conversion", "Trace", "Programmer", "IEEE 754", "Number Inspector",
    "Byte Inspector", "Binary Comparison", "Batch Conversion",
)
TRANSFER_ORDER = (
    "Number Inspector", "Programmer", "IEEE 754", "Conversion", "Byte Inspector",
    "Batch Conversion", "Trace",
)
RETIRED_WORKSPACES = frozenset({"Binary Comparison"})


def workspace_titles() -> tuple[str, ...]:
    return tuple(item.title for item in WORKSPACES)


def navigation_groups() -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for item in sorted(WORKSPACES, key=lambda entry: entry.navigation_order):
        groups.setdefault(item.group, []).append(item.title)
    return groups


def transfer_destinations(source: str) -> tuple[str, ...]:
    supported = workspace_titles()
    return tuple(title for title in TRANSFER_ORDER if title != source and title in supported)


def restored_workspace(
    preferences: Mapping[str, object], supported: Sequence[str] | None = None,
) -> str:
    titles = workspace_titles() if supported is None else tuple(supported)
    if not titles:
        raise ValueError("at least one workspace is required")
    active = preferences.get("active_workspace")
    if isinstance(active, str) and active in titles:
        return active
    index = preferences.get("active_tab", 0)
    if type(index) is int and 0 <= index < len(LEGACY_WORKSPACE_ORDER):
        legacy = LEGACY_WORKSPACE_ORDER[index]
        if legacy in titles:
            return legacy
    return titles[0]
