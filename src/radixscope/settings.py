import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from radixscope.exports import json_safe
from radixscope.workspaces import RETIRED_WORKSPACES, migrate_workspace, restored_workspace

MAX_SETTINGS_BYTES = 32 * 1024 * 1024
MAX_HISTORY_REPORT_BYTES = 256 * 1024


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.preferences: dict[str, object] = {}
        self.history: list[dict[str, object]] = []
        self.warning = ""
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            if self.path.stat().st_size > MAX_SETTINGS_BYTES:
                raise ValueError("settings file exceeds 32 MiB")
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if (
                not isinstance(data, dict)
                or type(data.get("schema")) is not int
                or data["schema"] != 1
            ):
                raise ValueError("unsupported settings format")
            preferences = data.get("preferences", {})
            history = data.get("history", [])
            if not isinstance(preferences, dict) or not isinstance(history, list):
                raise ValueError("invalid settings structure")
            self.preferences = preferences
            for key in ("workspaces", "workspace_views"):
                states = self.preferences.get(key)
                if isinstance(states, dict):
                    for title in RETIRED_WORKSPACES:
                        states.pop(title, None)
            states = self.preferences.get("workspaces")
            if isinstance(states, dict):
                migrated: dict[str, object] = {}
                active_source = self.preferences.get("active_workspace")
                for title, state in states.items():
                    if isinstance(title, str) and isinstance(state, dict):
                        target, value = migrate_workspace(title, state)
                        if target not in migrated or title in (target, active_source):
                            migrated[target] = value
                self.preferences["workspaces"] = migrated
            active = self.preferences.get("active_workspace")
            if isinstance(active, str) and active in RETIRED_WORKSPACES:
                self.preferences["active_workspace"] = restored_workspace(self.preferences)
            valid_history = [entry for entry in history if self._valid_entry(entry)
                             and entry["workspace"] not in RETIRED_WORKSPACES]
            for entry in valid_history:
                title, state = entry["workspace"], entry["state"]
                assert isinstance(title, str) and isinstance(state, dict)
                entry["workspace"], entry["state"] = migrate_workspace(title, state)
            self.history = valid_history[:self.history_limit]
        except (OSError, ValueError, UnicodeError) as error:
            self.warning = f"Could not load preferences: {error}"

    @staticmethod
    def _valid_entry(entry: object) -> bool:
        return (
            isinstance(entry, dict)
            and isinstance(entry.get("workspace"), str)
            and isinstance(entry.get("state"), dict)
            and isinstance(entry.get("summary"), str)
            and isinstance(entry.get("created_at"), str)
        )

    @property
    def history_limit(self) -> int:
        limit = self.preferences.get("history_limit", 20)
        if isinstance(limit, int) and not isinstance(limit, bool) and 1 <= limit <= 100:
            return limit
        return 20

    @property
    def remember_history(self) -> bool:
        return self.preferences.get("remember_history", True) is True

    def record(
        self, workspace: str, state: dict[str, object], summary: str,
        report: dict[str, object] | None = None,
    ) -> None:
        if not self.remember_history:
            return
        self.history = [
            entry for entry in self.history
            if entry["workspace"] != workspace or entry["state"] != state
        ]
        kind = "Float Comparison" if workspace == "IEEE 754" and state.get("compare") is True else (
            "Expression" if workspace == "Conversion" and state.get("mode") == "Expression"
            else workspace
        )
        entry: dict[str, object] = {
            "workspace": workspace, "state": dict(state), "summary": summary[:200],
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "kind": kind,
        }
        if report is not None:
            serialized = json.dumps(json_safe(report), ensure_ascii=False, allow_nan=False)
            if len(serialized.encode("utf-8")) <= MAX_HISTORY_REPORT_BYTES:
                entry["report"] = json.loads(serialized)
        self.history.insert(0, entry)
        del self.history[self.history_limit:]

    def search_history(
        self, query: str = "", kind: str | None = None,
    ) -> list[tuple[int, dict[str, object]]]:
        matches = []
        needle = query.casefold().strip()
        for index, entry in enumerate(self.history):
            category = entry.get("kind", entry["workspace"])
            if kind is not None and category != kind:
                continue
            state = entry["state"]
            assert isinstance(state, dict)
            haystack = " ".join(str(value) for value in (
                entry["workspace"], category, entry["summary"], state.get("input", ""),
                state.get("other_input", ""),
            )).casefold()
            if not needle or needle in haystack:
                matches.append((index, entry))
        return matches

    def save(self) -> None:
        content = json.dumps(
            {"schema": 1, "preferences": self.preferences, "history": self.history},
            ensure_ascii=False, allow_nan=False, indent=2,
        ).encode("utf-8")
        if len(content) > MAX_SETTINGS_BYTES:
            raise ValueError("settings file exceeds 32 MiB; reduce recent history")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=self.path.parent, suffix=".tmp", delete=False
            ) as handle:
                temporary = Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
