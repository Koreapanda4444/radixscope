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
    WorkspaceDefinition("Conversion", "Conversion", "Workspaces", 0),
    WorkspaceDefinition("Calculation", "Calculation", "Workspaces", 1),
    WorkspaceDefinition("Number Inspector", "Number Inspector", "Workspaces", 2),
    WorkspaceDefinition("Batch Conversion", "Batch Conversion", "Workspaces", 3),
)
LEGACY_WORKSPACE_ORDER = (
    "Conversion", "Trace", "Programmer", "IEEE 754", "Number Inspector",
    "Byte Inspector", "Binary Comparison", "Batch Conversion",
)
TRANSFER_ORDER = ("Conversion", "Calculation", "Number Inspector", "Batch Conversion")
WORKSPACE_ALIASES = {"Trace": "Conversion", "Programmer": "Calculation",
                     "IEEE 754": "Number Inspector"}
RETIRED_WORKSPACES = frozenset({"Binary Comparison", "Byte Inspector"})


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
    if isinstance(active, str):
        active = WORKSPACE_ALIASES.get(active, active)
        if active in titles:
            return active
    index = preferences.get("active_tab", 0)
    if type(index) is int and 0 <= index < len(LEGACY_WORKSPACE_ORDER):
        legacy = WORKSPACE_ALIASES.get(LEGACY_WORKSPACE_ORDER[index], LEGACY_WORKSPACE_ORDER[index])
        if legacy in titles:
            return legacy
    return titles[0]


def migrate_workspace(title: str, state: Mapping[str, object]) -> tuple[str, dict[str, object]]:
    """Map historical task identities without changing the meaning of their inputs."""
    result = dict(state)
    if title == "Trace":
        result.update({"mode": "Number", "show_trace": True})
    elif title == "Programmer":
        result["calculation_mode"] = "Fixed-width integer"
    elif title == "IEEE 754":
        width = str(result.get("bit_width", "32"))
        result["data_type"] = "bfloat16" if width == "bfloat16" else "binary" + width
        result["bit_width"] = 16 if width == "bfloat16" else int(width) if width.isdigit() else 32
        result["pattern"] = result.get("mode") == "decode"
        result["input_mode"] = "Number" if result["pattern"] else "Expression"
        result["base"] = result.get("base", 16) if result["pattern"] else 10
    elif title == "Conversion" and state.get("mode") == "Expression":
        title = "Calculation"
        result["calculation_mode"] = "Exact expression"
    return WORKSPACE_ALIASES.get(title, title), result
