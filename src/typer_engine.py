"""Typing simulation engine — types text into the focused window keystroke-by-keystroke."""

import ctypes
import time
import random
import threading
from pynput.keyboard import Controller, Key


def _is_caps_lock_on() -> bool:
    """Check if Caps Lock is currently active (Windows)."""
    try:
        return bool(ctypes.WinDLL("User32.dll").GetKeyState(0x14) & 1)
    except Exception:
        return False


def _disable_caps_lock():
    """Turn off Caps Lock if it is on (Windows)."""
    if _is_caps_lock_on():
        controller = Controller()
        controller.press(Key.caps_lock)
        controller.release(Key.caps_lock)


class TyperEngine:
    """Simulates realistic human typing into any focused window."""

    # Speed presets: seconds per character
    SPEED_PRESETS = {
        "Slow":      0.065,
        "Normal":    0.040,
        "Fast":      0.022,
        "Very Fast": 0.010,
    }

    def __init__(self):
        self.controller = Controller()
        self.base_delay: float = self.SPEED_PRESETS["Fast"]
        self.humanize: bool = True          # slight random jitter
        self.is_typing: bool = False
        self._stop = threading.Event()

    # ── Public API ────────────────────────────────────────────────────

    def set_speed(self, preset_name: str):
        """Set typing speed from a named preset."""
        self.base_delay = self.SPEED_PRESETS.get(preset_name, 0.022)

    def set_speed_value(self, delay: float):
        """Set typing speed directly (seconds per character)."""
        self.base_delay = max(0.003, delay)

    def type_text(
        self,
        text: str,
        press_enter: bool = True,
        delay_before: float = 0.3,
        on_char: callable = None,
        on_done: callable = None,
    ):
        """
        Type *text* character-by-character in a background thread.

        Args:
            text:         The string to type out.
            press_enter:  If True, press Enter after the text.
            delay_before: Seconds to wait before the first keystroke.
            on_char:      Optional callback(index, char) after each character.
            on_done:      Optional callback() when finished.
        """
        self._stop.clear()
        self.is_typing = True

        def _worker():
            try:
                # Initial pause so the user can position their cursor
                time.sleep(delay_before)

                # Turn off Caps Lock if accidentally left on
                _disable_caps_lock()

                for i, char in enumerate(text):
                    if self._stop.is_set():
                        break

                    # Type a single character
                    self.controller.type(char)

                    if on_char:
                        on_char(i, char)

                    # Delay between keystrokes
                    delay = self.base_delay
                    if self.humanize:
                        # Add natural variation — pauses at spaces / punctuation
                        if char in " .,!?;:\n":
                            delay += random.uniform(0.01, 0.05)
                        else:
                            delay += random.uniform(-0.008, 0.015)
                        delay = max(0.003, delay)

                    time.sleep(delay)

                # Optionally press Enter to send the message
                if press_enter and not self._stop.is_set():
                    time.sleep(0.08)
                    self.controller.press(Key.enter)
                    self.controller.release(Key.enter)
            finally:
                self.is_typing = False
                if on_done:
                    on_done()

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def stop(self):
        """Immediately stop typing."""
        self._stop.set()
        self.is_typing = False
