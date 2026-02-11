"""JSON-based persistence for demo scripts."""

import json
import os
import sys
from typing import List
from .models import Script, Step


def _get_data_dir() -> str:
    """Return a writable data directory.

    When running as a PyInstaller frozen exe, __file__ points inside a
    temporary extraction folder that is read-only / ephemeral.
    In that case, store data in the user's AppData (or home) directory.
    """
    if getattr(sys, "frozen", False):
        # Frozen exe — use user's local app data
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, "DemoScripter", "data")
    else:
        # Dev mode — store next to the project
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


DATA_DIR = _get_data_dir()
DATA_FILE = os.path.join(DATA_DIR, "scripts.json")


class Storage:
    """Loads and saves scripts to a local JSON file."""

    def __init__(self, filepath: str = DATA_FILE):
        self.filepath = filepath
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

    # ── Load ──────────────────────────────────────────────────────────
    def load(self) -> List[Script]:
        if not os.path.exists(self.filepath):
            return []
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [self._dict_to_script(d) for d in data]
        except (json.JSONDecodeError, KeyError):
            return []

    # ── Save ──────────────────────────────────────────────────────────
    def save(self, scripts: List[Script]):
        data = [self._script_to_dict(s) for s in scripts]
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ── Helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _dict_to_script(d: dict) -> Script:
        # Strip legacy 'role' field if present in saved data
        raw_steps = d.get("steps", [])
        for s in raw_steps:
            s.pop("role", None)
        steps = [Step(**s) for s in raw_steps]
        return Script(
            id=d["id"],
            name=d["name"],
            description=d.get("description", ""),
            steps=steps,
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
        )

    @staticmethod
    def _script_to_dict(s: Script) -> dict:
        return {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "steps": [
                {
                    "id": st.id,
                    "text": st.text,
                    "press_enter": st.press_enter,
                    "delay_before": st.delay_before,
                }
                for st in s.steps
            ],
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }
