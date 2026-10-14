import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

MAX_SETTINGS_BYTES = 32 * 1024 * 1024


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
            valid_history = [entry for entry in history if self._valid_entry(entry)]
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

    def record(self, workspace: str, state: dict[str, object], summary: str) -> None:
        if not self.remember_history:
            return
        self.history = [
            entry for entry in self.history
            if entry["workspace"] != workspace or entry["state"] != state
        ]
        self.history.insert(0, {
            "workspace": workspace, "state": dict(state), "summary": summary[:200],
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        })
        del self.history[self.history_limit:]

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
