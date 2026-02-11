"""Data models for DemoScripter."""

from dataclasses import dataclass, field
from typing import List
import uuid
from datetime import datetime


@dataclass
class Step:
    """A single step in a demo script — one message to be typed out."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    press_enter: bool = True     # Press Enter after typing to send
    delay_before: float = 0.3    # Seconds to wait before typing starts

    def preview(self, max_len: int = 60) -> str:
        """Return a truncated preview of the step text."""
        text = self.text.replace("\n", " ")
        if len(text) > max_len:
            return text[:max_len - 3] + "..."
        return text


@dataclass
class Script:
    """A complete demo script containing ordered steps."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "New Script"
    description: str = ""
    steps: List[Step] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def touch(self):
        """Update the modified timestamp."""
        self.updated_at = datetime.now().isoformat()
