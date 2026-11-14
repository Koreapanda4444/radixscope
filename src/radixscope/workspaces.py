"""Canonical workspace identities shared by navigation, transfers and saved state."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkspaceDefinition:
    title: str
    label: str


WORKSPACES = (
    WorkspaceDefinition("Conversion", "Conversion"),
    WorkspaceDefinition("Calculation", "Calculation"),
    WorkspaceDefinition("Number Inspector", "Number Inspector"),
    WorkspaceDefinition("Batch Conversion", "Batch Conversion"),
)
LEGACY_WORKSPACE_ORDER = (
    "Conversion", "Trace", "Programmer", "IEEE 754", "Number Inspector",
    "Byte Inspector", "Binary Comparison", "Batch Conversion",
)
TRANSFER_ORDER = ("Conversion", "Calculation", "Number Inspector", "Batch Conversion")
WORKSPACE_ALIASES = {"Trace": "Conversion", "Programmer": "Calculation",
                     "IEEE 754": "Number Inspector"}


def workspace_titles() -> tuple[str, ...]:
    return tuple(item.title for item in WORKSPACES)


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
        if width not in ("16", "32", "64", "bfloat16"):
            width = "32"
        result["data_type"] = "bfloat16" if width == "bfloat16" else "binary" + width
        result["bit_width"] = 16 if width == "bfloat16" else int(width)
        result["pattern"] = result.get("mode") == "decode"
        result["input_mode"] = "Number" if result["pattern"] else "Expression"
        result["analysis"] = "Format comparison" if result.get("compare") is True else (
            "Number representation"
        )
        result["base"] = result.get("base", 16) if result["pattern"] else 10
    elif title == "Conversion" and state.get("mode") == "Expression":
        title = "Calculation"
        result["calculation_mode"] = "Exact expression"
    target = WORKSPACE_ALIASES.get(title, title)
    for key in ("bitfields", "layout", "raw_hex", "swap_to"):
        result.pop(key, None)
    if target == "Number Inspector":
        for key in ("mode", "compare"):
            result.pop(key, None)
    return target, result


def work_kind(title: str, state: Mapping[str, object]) -> str:
    if title == "Calculation":
        return "Fixed-width integer" if (
            state.get("calculation_mode") == "Fixed-width integer"
        ) else (
            "Exact expression"
        )
    if title == "Number Inspector":
        analysis = state.get("analysis")
        if analysis in ("Numeric comparison", "Format comparison", "Floating-point arithmetic"):
            return str(analysis)
        return "IEEE 754" if state.get("data_type", "integer") != "integer" else title
    return title


def normalize_preferences(preferences: dict[str, object]) -> None:
    active_source = preferences.get("active_workspace")
    index = preferences.get("active_tab")
    if not isinstance(active_source, str) and type(index) is int:
        active_source = LEGACY_WORKSPACE_ORDER[index] if (
            0 <= index < len(LEGACY_WORKSPACE_ORDER)
        ) else ""
    original_states = preferences.get("workspaces")
    if isinstance(active_source, str):
        source_state = original_states.get(active_source, {}) if (
            isinstance(original_states, dict)
        ) else {}
        active, _ = migrate_workspace(
            active_source, source_state if isinstance(source_state, dict) else {}
        )
        preferences["active_workspace"] = active if active in workspace_titles() else "Conversion"
    for category in ("workspaces", "workspace_views"):
        states = preferences.get(category)
        if not isinstance(states, dict):
            continue
        migrated: dict[str, object] = {}
        priorities: dict[str, int] = {}
        for title, state in states.items():
            if not isinstance(title, str) or not isinstance(state, dict):
                continue
            target, normalized = migrate_workspace(title, state)
            if target not in workspace_titles():
                continue
            priority = 3 if title == active_source else 2 if title == target else 1
            if priority >= priorities.get(target, 0):
                migrated[target] = normalized if category == "workspaces" else dict(state)
                priorities[target] = priority
        preferences[category] = migrated
