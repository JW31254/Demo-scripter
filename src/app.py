"""Main application window for DemoScripter — polished UI with light/dark mode."""

import ctypes
import json
import os
import sys
import threading
import customtkinter as ctk
from tkinter import messagebox, filedialog
from pynput import keyboard as kb
import pystray
from PIL import Image, ImageDraw, ImageFont

# Give the app its own taskbar identity on Windows
if sys.platform == "win32":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("demoscripter.app.1")


def _create_tray_image() -> Image.Image:
    """Draw a small purple lightning-bolt icon for the system tray."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Purple circle background
    draw.ellipse([4, 4, size - 4, size - 4], fill=(124, 92, 252))
    # Lightning bolt
    bolt = [(34, 10), (22, 30), (30, 30), (26, 54), (42, 26), (34, 26)]
    draw.polygon(bolt, fill=(255, 255, 255))
    return img

from .models import Script, Step
from .storage import Storage
from .typer_engine import TyperEngine


# ─── Theme palettes ──────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg":            "#101018",
        "surface":       "#18182a",
        "card":          "#1c1c34",
        "card_alt":      "#20203a",
        "selected":      "#30305a",
        "selected_text": "#ffffff",
        "demo_active":   "#143024",
        "demo_border":   "#22c55e",
        "text":          "#eaeaf0",
        "text2":         "#a0a0b8",
        "text3":         "#60607a",
        "muted":         "#44445a",
        "border":        "#28284a",
        "input_bg":      "#14141e",
        "accent":        "#7c5cfc",
        "accent_hover":  "#9b7eff",
        "accent_muted":  "#3b2d7a",
        "success":       "#22c55e",
        "success_hover": "#1aad50",
        "danger":        "#f43f5e",
        "danger_hover":  "#e11d48",
        "warn":          "#f59e0b",
        "badge_bg":      "#7c5cfc",
        "badge_active":  "#22c55e",
        "separator":     "#28284a",
        "topbar_accent": "#7c5cfc",
    },
    "light": {
        "bg":            "#f2f3f8",
        "surface":       "#ffffff",
        "card":          "#ffffff",
        "card_alt":      "#f8f8fc",
        "selected":      "#7c5cfc",
        "selected_text": "#ffffff",
        "demo_active":   "#e8f8ee",
        "demo_border":   "#22c55e",
        "text":          "#1a1a2e",
        "text2":         "#555570",
        "text3":         "#8888a0",
        "muted":         "#c0c0d0",
        "border":        "#e0e0ec",
        "input_bg":      "#f5f5fa",
        "accent":        "#7c5cfc",
        "accent_hover":  "#6344e0",
        "accent_muted":  "#ebe5ff",
        "success":       "#16a34a",
        "success_hover": "#15803d",
        "danger":        "#e11d48",
        "danger_hover":  "#be123c",
        "warn":          "#d97706",
        "badge_bg":      "#7c5cfc",
        "badge_active":  "#16a34a",
        "separator":     "#e8e8f0",
        "topbar_accent": "#7c5cfc",
    },
}


class DemoScripterApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("DemoScripter")
        self.geometry("1200x820")
        self.minsize(960, 640)

        # Window icon
        self._set_window_icon()

        # ── Theme ─────────────────────────────────────────────────────
        self._mode = "dark"
        self.t = THEMES["dark"]
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # ── State ─────────────────────────────────────────────────────
        self.storage = Storage()
        self.scripts: list[Script] = self.storage.load()
        self.selected_script: Script | None = None
        self.selected_step_idx: int | None = None
        self.typer = TyperEngine()
        self.demo_running: bool = False
        self.demo_step_idx: int = 0
        self._hotkey_key = kb.Key.f2
        self._hotkey_label = "F2"
        self._listener: kb.Listener | None = None
        self._always_on_top = False
        self._step_cards: list[dict] = []
        self._tray_icon: pystray.Icon | None = None

        # Cached fonts to avoid CTkFont leak
        self._font_step_normal = ctk.CTkFont(size=12, weight="normal")
        self._font_step_bold = ctk.CTkFont(size=12, weight="bold")

        # ── Build ─────────────────────────────────────────────────────
        self._build_ui()
        self._apply_theme()
        self._refresh_script_list()
        self._update_runner_state()
        self.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)
        self.bind("<Unmap>", self._on_minimize)
        self._start_tray_icon()

    # ══════════════════════════════════════════════════════════════════
    #  WINDOW ICON
    # ══════════════════════════════════════════════════════════════════

    def _set_window_icon(self):
        """Set window icon from bundled .ico or generate one dynamically."""
        import tempfile
        try:
            # Try the bundled assets/app.ico first
            if getattr(sys, "frozen", False):
                base = sys._MEIPASS
            else:
                base = os.path.dirname(os.path.dirname(__file__))
            ico_path = os.path.join(base, "assets", "app.ico")
            if os.path.exists(ico_path):
                self.after(50, lambda: self.iconbitmap(ico_path))
                return
        except Exception:
            pass
        # Fallback: generate a temp .ico from the tray image
        try:
            img = _create_tray_image()
            tmp = os.path.join(tempfile.gettempdir(), "demoscripter_icon.ico")
            img.save(tmp, format="ICO", sizes=[(64, 64)])
            self.after(50, lambda: self.iconbitmap(tmp))
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════
    #  THEME
    # ══════════════════════════════════════════════════════════════════

    def _toggle_theme(self):
        self._mode = "light" if self._mode == "dark" else "dark"
        self.t = THEMES[self._mode]
        ctk.set_appearance_mode(self._mode)
        self._theme_btn.configure(text="☀" if self._mode == "dark" else "🌙")
        self._apply_theme()
        self._destroy_step_cards()
        self._refresh_script_list()
        self._refresh_step_list()

    def _apply_theme(self):
        t = self.t
        self.configure(fg_color=t["bg"])
        # Top bar
        self._topbar.configure(fg_color=t["surface"], border_color=t["separator"])
        self._topbar_line.configure(fg_color=t["topbar_accent"])
        self._logo_label.configure(text_color=t["text"])
        self._subtitle_label.configure(text_color=t["text3"])
        self._pin_btn.configure(hover_color=t["card_alt"])
        self._theme_btn.configure(hover_color=t["card_alt"])
        # Sidebar
        self._sidebar.configure(fg_color=t["surface"])
        self._sidebar_sep.configure(fg_color=t["separator"])
        self._script_list_frame.configure(fg_color="transparent")
        # Cards
        for panel in (self._info_card, self._steps_panel, self._editor_panel, self._runner_card):
            panel.configure(fg_color=t["card"], border_color=t["border"])
        self._step_list_frame.configure(fg_color="transparent")
        # Input fields
        for entry in (self._name_entry, self._desc_entry, self._delay_entry):
            entry.configure(
                fg_color=t["input_bg"], border_color=t["border"],
                text_color=t["text"],
            )
        self._step_textbox.configure(
            fg_color=t["input_bg"], border_color=t["border"],
            text_color=t["text"],
        )
        # Option menus
        self._hotkey_menu.configure(fg_color=t["input_bg"], button_color=t["accent"], text_color=t["text"])
        self._speed_menu.configure(fg_color=t["input_bg"], button_color=t["accent"], text_color=t["text"])
        # Runner
        self._status_dot.configure(fg_color=t["text3"])
        self._status_label.configure(text_color=t["text3"])
        self._next_label.configure(text_color=t["text2"])
        self._progress.configure(progress_color=t["accent"], fg_color=t["border"])

    # ══════════════════════════════════════════════════════════════════
    #  UI CONSTRUCTION
    # ══════════════════════════════════════════════════════════════════

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_topbar()
        self._build_sidebar()
        self._build_content()

    # ── Top bar ──────────────────────────────────────────────────────
    def _build_topbar(self):
        t = self.t
        wrapper = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        wrapper.grid(row=0, column=0, columnspan=2, sticky="ew")
        wrapper.grid_columnconfigure(0, weight=1)

        self._topbar = ctk.CTkFrame(
            wrapper, height=52, corner_radius=0,
            fg_color=t["surface"], border_width=0, border_color=t["separator"],
        )
        self._topbar.grid(row=0, column=0, sticky="ew")
        self._topbar.grid_columnconfigure(2, weight=1)

        # Accent line under the top bar
        self._topbar_line = ctk.CTkFrame(wrapper, height=2, corner_radius=0, fg_color=t["topbar_accent"])
        self._topbar_line.grid(row=1, column=0, sticky="ew")

        # Logo
        self._logo_icon = ctk.CTkLabel(
            self._topbar, text="⚡",
            font=ctk.CTkFont(size=22),
        )
        self._logo_icon.grid(row=0, column=0, padx=(18, 2), pady=12)
        self._logo_label = ctk.CTkLabel(
            self._topbar, text="DemoScripter",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=t["text"],
        )
        self._logo_label.grid(row=0, column=1, padx=(0, 6), pady=12)
        self._subtitle_label = ctk.CTkLabel(
            self._topbar, text="Presales Demo Assistant",
            font=ctk.CTkFont(size=11), text_color=t["text3"],
        )
        self._subtitle_label.grid(row=0, column=2, sticky="w", padx=4, pady=12)

        # Right controls
        right = ctk.CTkFrame(self._topbar, fg_color="transparent")
        right.grid(row=0, column=3, padx=(0, 12), pady=10)

        self._pin_btn = ctk.CTkButton(
            right, text="📌", width=34, height=34,
            corner_radius=8, fg_color="transparent",
            hover_color=t["card_alt"],
            font=ctk.CTkFont(size=14),
            command=self._toggle_pin,
        )
        self._pin_btn.grid(row=0, column=0, padx=2)

        self._theme_btn = ctk.CTkButton(
            right, text="☀", width=34, height=34,
            corner_radius=8, fg_color="transparent",
            hover_color=t["card_alt"],
            font=ctk.CTkFont(size=14),
            command=self._toggle_theme,
        )
        self._theme_btn.grid(row=0, column=1, padx=2)

    # ── Sidebar ──────────────────────────────────────────────────────
    def _build_sidebar(self):
        t = self.t
        container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        container.grid(row=1, column=0, sticky="ns")
        container.grid_rowconfigure(0, weight=1)

        self._sidebar = ctk.CTkFrame(container, width=270, corner_radius=0, fg_color=t["surface"])
        self._sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar.grid_columnconfigure(0, weight=1)
        self._sidebar.grid_rowconfigure(2, weight=1)
        self._sidebar.grid_propagate(False)

        # Vertical separator line
        self._sidebar_sep = ctk.CTkFrame(container, width=1, fg_color=t["separator"], corner_radius=0)
        self._sidebar_sep.grid(row=0, column=1, sticky="ns")

        # Header
        hdr = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=14, pady=(16, 2))
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            hdr, text="SCRIPTS",
            font=ctk.CTkFont(size=10, weight="bold"), text_color=t["text3"],
        ).grid(row=0, column=0, sticky="w")

        # Action buttons row
        actions = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=12, pady=(6, 8))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            actions, text="+ New", height=30, corner_radius=8,
            fg_color=t["accent"], hover_color=t["accent_hover"],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._new_script,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 3))

        ctk.CTkButton(
            actions, text="Import", height=30, corner_radius=8,
            fg_color=t["accent_muted"] if self._mode == "dark" else t["accent_muted"],
            hover_color=t["accent_hover"],
            text_color=t["accent"] if self._mode == "light" else t["text"],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._import_script,
        ).grid(row=0, column=1, sticky="ew", padx=(3, 0))

        # Scripts list
        self._script_list_frame = ctk.CTkScrollableFrame(self._sidebar, fg_color="transparent")
        self._script_list_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=2)
        self._script_list_frame.grid_columnconfigure(0, weight=1)

        # Bottom
        bot = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        bot.grid(row=3, column=0, sticky="ew", padx=12, pady=(6, 14))
        bot.grid_columnconfigure(0, weight=1)
        bot.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            bot, text="Export", height=30, corner_radius=8,
            fg_color="transparent", border_width=1, border_color=t["border"],
            hover_color=t["card_alt"], text_color=t["text2"],
            font=ctk.CTkFont(size=12),
            command=self._export_script,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        ctk.CTkButton(
            bot, text="Delete", height=30, corner_radius=8,
            fg_color="transparent", border_width=1, border_color=t["danger"],
            hover_color=t["danger"], text_color=t["danger"],
            font=ctk.CTkFont(size=12),
            command=self._delete_script,
        ).grid(row=0, column=1, sticky="ew", padx=(3, 0))

    # ── Content ──────────────────────────────────────────────────────
    def _build_content(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=(10, 16))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)

        self._build_info_card(content)
        self._build_steps_area(content)
        self._build_runner(content)

    def _build_info_card(self, parent):
        t = self.t
        self._info_card = ctk.CTkFrame(
            parent, fg_color=t["card"], corner_radius=14,
            border_width=1, border_color=t["border"],
        )
        self._info_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._info_card.grid_columnconfigure(1, weight=1)
        self._info_card.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(self._info_card, text="Name", font=ctk.CTkFont(size=11, weight="bold"),
                      text_color=t["text3"]).grid(row=0, column=0, padx=(16, 8), pady=12, sticky="w")
        self._name_entry = ctk.CTkEntry(
            self._info_card, placeholder_text="Script name…",
            corner_radius=8, height=34, border_width=1,
            border_color=t["border"], fg_color=t["input_bg"],
        )
        self._name_entry.grid(row=0, column=1, padx=(0, 20), pady=12, sticky="ew")
        self._name_entry.bind("<KeyRelease>", self._on_name_change)

        ctk.CTkLabel(self._info_card, text="Description", font=ctk.CTkFont(size=11, weight="bold"),
                      text_color=t["text3"]).grid(row=0, column=2, padx=(0, 8), pady=12, sticky="w")
        self._desc_entry = ctk.CTkEntry(
            self._info_card, placeholder_text="What's this demo about?",
            corner_radius=8, height=34, border_width=1,
            border_color=t["border"], fg_color=t["input_bg"],
            text_color=t["text"],
        )
        self._desc_entry.grid(row=0, column=3, padx=(0, 16), pady=12, sticky="ew")
        self._desc_entry.bind("<KeyRelease>", self._on_desc_change)

    def _build_steps_area(self, parent):
        t = self.t
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=1, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=3)
        frame.grid_columnconfigure(1, weight=2)
        frame.grid_rowconfigure(0, weight=1)

        # ── Left: step list ──────────────────────────────────────────
        self._steps_panel = ctk.CTkFrame(
            frame, fg_color=t["card"], corner_radius=14,
            border_width=1, border_color=t["border"],
        )
        self._steps_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self._steps_panel.grid_columnconfigure(0, weight=1)
        self._steps_panel.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(self._steps_panel, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))
        hdr.grid_columnconfigure(0, weight=1)

        lbl_row = ctk.CTkFrame(hdr, fg_color="transparent")
        lbl_row.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(lbl_row, text="Steps", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, sticky="w")
        self._step_count_label = ctk.CTkLabel(
            lbl_row, text="", font=ctk.CTkFont(size=10),
            text_color=t["text3"],
        )
        self._step_count_label.grid(row=0, column=1, padx=(8, 0))

        btn_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_frame.grid(row=0, column=1)
        btn_defs = [
            ("＋", self._add_step, t["accent"], t["accent_hover"]),
            ("▲", self._move_step_up, t["muted"], t["text3"]),
            ("▼", self._move_step_down, t["muted"], t["text3"]),
            ("⟳", self._duplicate_step, t["muted"], t["text3"]),
            ("✕", self._delete_step, t["danger"], t["danger_hover"]),
        ]
        for i, (txt, cmd, fg, hv) in enumerate(btn_defs):
            ctk.CTkButton(
                btn_frame, text=txt, width=30, height=26, corner_radius=6,
                fg_color=fg, hover_color=hv,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="white",
                command=cmd,
            ).grid(row=0, column=i, padx=2)

        self._step_list_frame = ctk.CTkScrollableFrame(self._steps_panel, fg_color="transparent")
        self._step_list_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 10))
        self._step_list_frame.grid_columnconfigure(0, weight=1)

        # ── Right: step editor ───────────────────────────────────────
        self._editor_panel = ctk.CTkFrame(
            frame, fg_color=t["card"], corner_radius=14,
            border_width=1, border_color=t["border"],
        )
        self._editor_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self._editor_panel.grid_columnconfigure(0, weight=1)
        self._editor_panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self._editor_panel, text="Edit Step",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=14, pady=(14, 6), sticky="w")

        self._step_textbox = ctk.CTkTextbox(
            self._editor_panel, wrap="word",
            font=ctk.CTkFont(family="Consolas", size=13),
            corner_radius=10, border_width=1, border_color=t["border"],
            fg_color=t["input_bg"], text_color=t["text"],
        )
        self._step_textbox.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 6))
        self._step_textbox.bind("<KeyRelease>", self._on_step_text_change)

        opts = ctk.CTkFrame(self._editor_panel, fg_color="transparent")
        opts.grid(row=2, column=0, sticky="ew", padx=14, pady=(4, 14))
        opts.grid_columnconfigure(3, weight=1)

        self._enter_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            opts, text="Press Enter", variable=self._enter_var,
            command=self._on_enter_toggle, corner_radius=4,
            font=ctk.CTkFont(size=11),
            checkbox_width=18, checkbox_height=18,
        ).grid(row=0, column=0, padx=(0, 14))

        ctk.CTkLabel(opts, text="Delay", font=ctk.CTkFont(size=11),
                      text_color=t["text3"]).grid(row=0, column=1, padx=(0, 4))
        self._delay_entry = ctk.CTkEntry(
            opts, width=50, placeholder_text="0.3",
            corner_radius=6, height=28, border_width=1,
            border_color=t["border"], fg_color=t["input_bg"],
            text_color=t["text"],
            font=ctk.CTkFont(size=11),
        )
        self._delay_entry.grid(row=0, column=2, sticky="w")
        self._delay_entry.bind("<KeyRelease>", self._on_delay_change)

        ctk.CTkLabel(opts, text="sec", font=ctk.CTkFont(size=10),
                      text_color=t["text3"]).grid(row=0, column=3, sticky="w", padx=(4, 0))

    # ── Runner ───────────────────────────────────────────────────────
    def _build_runner(self, parent):
        t = self.t
        self._runner_card = ctk.CTkFrame(
            parent, fg_color=t["card"], corner_radius=14, height=110,
            border_width=1, border_color=t["border"],
        )
        self._runner_card.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self._runner_card.grid_columnconfigure(0, weight=1)

        # Top row: title + controls
        top = ctk.CTkFrame(self._runner_card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        top.grid_columnconfigure(6, weight=1)

        self._start_btn = ctk.CTkButton(
            top, text="▶  Start Demo",
            fg_color=t["success"], hover_color=t["success_hover"],
            width=140, height=36, corner_radius=10,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._toggle_demo,
        )
        self._start_btn.grid(row=0, column=0, padx=(0, 16))

        # Separator dot
        ctk.CTkLabel(top, text="·", text_color=t["muted"], font=ctk.CTkFont(size=18)).grid(row=0, column=1, padx=4)

        ctk.CTkLabel(top, text="Hotkey", font=ctk.CTkFont(size=10), text_color=t["text3"]).grid(row=0, column=2, padx=(0, 4))
        self._hotkey_menu = ctk.CTkOptionMenu(
            top, values=["F1","F2","F3","F4","F5","F6","F7","F8","F9","F10"],
            width=62, height=30, corner_radius=8,
            fg_color=t["input_bg"], button_color=t["accent"],
            font=ctk.CTkFont(size=11),
            command=self._on_hotkey_change,
        )
        self._hotkey_menu.set("F2")
        self._hotkey_menu.grid(row=0, column=3, padx=(0, 12))

        ctk.CTkLabel(top, text="Speed", font=ctk.CTkFont(size=10), text_color=t["text3"]).grid(row=0, column=4, padx=(0, 4))
        self._speed_menu = ctk.CTkOptionMenu(
            top, values=list(TyperEngine.SPEED_PRESETS.keys()),
            width=90, height=30, corner_radius=8,
            fg_color=t["input_bg"], button_color=t["accent"],
            font=ctk.CTkFont(size=11),
            command=self._on_speed_change,
        )
        self._speed_menu.set("Fast")
        self._speed_menu.grid(row=0, column=5)

        # Bottom row: status + progress
        bottom = ctk.CTkFrame(self._runner_card, fg_color="transparent")
        bottom.grid(row=1, column=0, sticky="ew", padx=16, pady=(8, 0))
        bottom.grid_columnconfigure(2, weight=1)

        self._status_dot = ctk.CTkLabel(
            bottom, text="●", font=ctk.CTkFont(size=10), text_color=t["text3"], width=14,
        )
        self._status_dot.grid(row=0, column=0, padx=(0, 4))

        self._status_label = ctk.CTkLabel(
            bottom, text="Idle", font=ctk.CTkFont(size=11, weight="bold"), text_color=t["text3"],
        )
        self._status_label.grid(row=0, column=1, sticky="w")

        self._next_label = ctk.CTkLabel(
            bottom, text="", font=ctk.CTkFont(size=11), text_color=t["text2"],
            wraplength=550, justify="left",
        )
        self._next_label.grid(row=0, column=2, sticky="w", padx=(12, 0))

        self._progress = ctk.CTkProgressBar(
            self._runner_card, height=4, corner_radius=2,
            progress_color=t["accent"], fg_color=t["border"],
        )
        self._progress.grid(row=2, column=0, sticky="ew", padx=16, pady=(8, 14))
        self._progress.set(0)

    # ══════════════════════════════════════════════════════════════════
    #  ALWAYS ON TOP
    # ══════════════════════════════════════════════════════════════════

    def _toggle_pin(self):
        self._always_on_top = not self._always_on_top
        self.attributes("-topmost", self._always_on_top)
        self._pin_btn.configure(
            fg_color=self.t["accent"] if self._always_on_top else "transparent",
        )

    # ══════════════════════════════════════════════════════════════════
    #  IMPORT / EXPORT
    # ══════════════════════════════════════════════════════════════════

    def _export_script(self):
        if not self.selected_script:
            messagebox.showinfo("Export", "Select a script first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"{self.selected_script.name}.json",
        )
        if not path:
            return
        data = Storage._script_to_dict(self.selected_script)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Exported", f"Script saved to:\n{path}")

    def _import_script(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            script = Storage._dict_to_script(data)
            # Give it a new ID to avoid collisions
            import uuid
            script.id = str(uuid.uuid4())
            self.scripts.append(script)
            self._select_script(script)
            self._save()
            messagebox.showinfo("Imported", f"Script '{script.name}' imported.")
        except Exception as e:
            messagebox.showerror("Import Error", f"Could not import:\n{e}")

    # ══════════════════════════════════════════════════════════════════
    #  SCRIPT LIST
    # ══════════════════════════════════════════════════════════════════

    def _refresh_script_list(self):
        t = self.t
        for w in self._script_list_frame.winfo_children():
            w.destroy()
        for script in self.scripts:
            is_sel = self.selected_script and script.id == self.selected_script.id
            bg = t["selected"] if is_sel else "transparent"
            txt_color = t["selected_text"] if is_sel else t["text"]
            step_count = len(script.steps)
            label = f"  {script.name}"
            btn = ctk.CTkButton(
                self._script_list_frame,
                text=label,
                anchor="w",
                fg_color=bg,
                hover_color=t["accent_hover"] if is_sel else t["card_alt"],
                text_color=txt_color,
                text_color_disabled=txt_color,
                height=40,
                corner_radius=10,
                font=ctk.CTkFont(size=12, weight="bold" if is_sel else "normal"),
                command=lambda s=script: self._select_script(s),
            )
            btn.grid(sticky="ew", pady=2)

            # Step count badge (overlaid on right side is complex, so use a subtitle approach)
            if step_count > 0:
                sub = ctk.CTkLabel(
                    self._script_list_frame,
                    text=f"     {step_count} step{'s' if step_count != 1 else ''}",
                    font=ctk.CTkFont(size=9),
                    text_color=t["selected_text"] if is_sel else t["text3"],
                    anchor="w",
                )
                sub.grid(sticky="ew", pady=(0, 2))
                sub.bind("<Button-1>", lambda e, s=script: self._select_script(s))

    def _select_script(self, script: Script):
        self._save_current()
        self.selected_script = script
        self.selected_step_idx = None

        self._name_entry.delete(0, "end")
        self._name_entry.insert(0, script.name)
        self._desc_entry.delete(0, "end")
        self._desc_entry.insert(0, script.description)

        self._refresh_script_list()
        self._destroy_step_cards()
        self._refresh_step_list()
        self._clear_step_editor()

    def _new_script(self):
        script = Script(name=f"Demo Script {len(self.scripts) + 1}")
        self.scripts.append(script)
        self._select_script(script)
        self._save()

    def _delete_script(self):
        if not self.selected_script:
            return
        if not messagebox.askyesno("Delete Script", f"Delete '{self.selected_script.name}'?"):
            return
        self.scripts = [s for s in self.scripts if s.id != self.selected_script.id]
        self.selected_script = None
        self.selected_step_idx = None
        self._name_entry.delete(0, "end")
        self._desc_entry.delete(0, "end")
        self._refresh_script_list()
        self._destroy_step_cards()
        self._refresh_step_list()
        self._clear_step_editor()
        self._save()

    # ══════════════════════════════════════════════════════════════════
    #  STEP LIST  (flicker-free)
    # ══════════════════════════════════════════════════════════════════

    def _refresh_step_list(self):
        if not self.selected_script:
            self._destroy_step_cards()
            self._step_count_label.configure(text="")
            return

        steps = self.selected_script.steps
        num_steps = len(steps)
        num_cards = len(self._step_cards)

        # Update step counter
        self._step_count_label.configure(
            text=f"({num_steps})" if num_steps > 0 else "",
        )

        while num_cards > num_steps:
            self._step_cards.pop()["frame"].destroy()
            num_cards -= 1
        while num_cards < num_steps:
            self._step_cards.append(self._create_step_card_widget(num_cards))
            num_cards += 1

        for idx in range(num_steps):
            is_sel = self.selected_step_idx == idx
            is_demo = self.demo_running and self.demo_step_idx == idx
            self._update_step_card(idx, steps[idx], is_sel, is_demo)

    def _create_step_card_widget(self, idx: int) -> dict:
        t = self.t
        card = ctk.CTkFrame(self._step_list_frame, fg_color="transparent", corner_radius=10, height=42)
        card.grid(sticky="ew", pady=2)
        card.grid_columnconfigure(1, weight=1)

        badge = ctk.CTkLabel(
            card, text="", width=26, height=26,
            font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=6, text_color="white",
        )
        badge.grid(row=0, column=0, padx=(8, 8), pady=8)

        label = ctk.CTkLabel(
            card, text="", font=self._font_step_normal,
            anchor="w", justify="left",
        )
        label.grid(row=0, column=1, sticky="w", padx=(0, 8), pady=8)

        # Store a mutable index ref so we can update it without rebinding
        card_data = {"frame": card, "badge": badge, "label": label, "idx": idx}

        def on_click(e, cd=card_data):
            self._on_step_click(cd["idx"])

        for w in (card, badge, label):
            w.bind("<Button-1>", on_click)

        return card_data

    def _update_step_card(self, idx: int, step: Step, selected: bool, demo_active: bool):
        t = self.t
        cd = self._step_cards[idx]
        card, badge, label = cd["frame"], cd["badge"], cd["label"]

        # Update the mutable index so the existing click handler stays correct
        cd["idx"] = idx

        if demo_active:
            bg = t["demo_active"]
        elif selected:
            bg = t["selected"]
        else:
            bg = "transparent"
        card.configure(fg_color=bg)

        badge.configure(
            text=f"{idx + 1}",
            fg_color=t["badge_active"] if demo_active else t["badge_bg"],
        )

        preview = step.preview(48) or "(empty)"
        text = f"▶  {preview}" if demo_active else preview

        if demo_active:
            txt_color = t["success"]
        elif selected:
            txt_color = t["selected_text"]
        else:
            txt_color = t["text"]

        label.configure(
            text=text,
            font=self._font_step_bold if (demo_active or selected) else self._font_step_normal,
            text_color=txt_color,
        )

    def _destroy_step_cards(self):
        for cd in self._step_cards:
            cd["frame"].destroy()
        self._step_cards.clear()

    def _on_step_click(self, idx: int):
        self._select_step(idx)
        if self.demo_running:
            self.demo_step_idx = idx
            self._update_runner_state()

    def _select_step(self, idx: int):
        if not self.selected_script or idx < 0 or idx >= len(self.selected_script.steps):
            return
        self.selected_step_idx = idx
        step = self.selected_script.steps[idx]

        self._step_textbox.delete("1.0", "end")
        self._step_textbox.insert("1.0", step.text)
        self._enter_var.set(step.press_enter)
        self._delay_entry.delete(0, "end")
        self._delay_entry.insert(0, str(step.delay_before))
        self._refresh_step_list()

    def _add_step(self):
        if not self.selected_script:
            messagebox.showinfo("No Script", "Create or select a script first.")
            return
        step = Step()
        self.selected_script.steps.append(step)
        self.selected_script.touch()
        self._select_step(len(self.selected_script.steps) - 1)
        self._save()

    def _duplicate_step(self):
        """Duplicate the currently selected step."""
        if not self.selected_script or self.selected_step_idx is None:
            return
        src = self.selected_script.steps[self.selected_step_idx]
        new = Step(text=src.text, press_enter=src.press_enter, delay_before=src.delay_before)
        insert_at = self.selected_step_idx + 1
        self.selected_script.steps.insert(insert_at, new)
        self.selected_script.touch()
        self._destroy_step_cards()
        self._select_step(insert_at)
        self._save()

    def _delete_step(self):
        if not self.selected_script or self.selected_step_idx is None:
            return
        del self.selected_script.steps[self.selected_step_idx]
        self.selected_script.touch()
        self.selected_step_idx = None
        self._destroy_step_cards()
        self._refresh_step_list()
        self._clear_step_editor()
        self._save()

    def _move_step_up(self):
        if not self.selected_script or self.selected_step_idx is None or self.selected_step_idx == 0:
            return
        i = self.selected_step_idx
        steps = self.selected_script.steps
        steps[i - 1], steps[i] = steps[i], steps[i - 1]
        self.selected_step_idx = i - 1
        self.selected_script.touch()
        self._refresh_step_list()
        self._save()

    def _move_step_down(self):
        if not self.selected_script or self.selected_step_idx is None:
            return
        i = self.selected_step_idx
        steps = self.selected_script.steps
        if i >= len(steps) - 1:
            return
        steps[i], steps[i + 1] = steps[i + 1], steps[i]
        self.selected_step_idx = i + 1
        self.selected_script.touch()
        self._refresh_step_list()
        self._save()

    def _clear_step_editor(self):
        self._step_textbox.delete("1.0", "end")
        self._enter_var.set(True)
        self._delay_entry.delete(0, "end")
        self._delay_entry.insert(0, "0.3")

    # ── Step editor callbacks ────────────────────────────────────────

    def _current_step(self) -> Step | None:
        if self.selected_script and self.selected_step_idx is not None:
            if 0 <= self.selected_step_idx < len(self.selected_script.steps):
                return self.selected_script.steps[self.selected_step_idx]
        return None

    def _on_step_text_change(self, event=None):
        step = self._current_step()
        if step:
            step.text = self._step_textbox.get("1.0", "end-1c")
            self.selected_script.touch()
            self._refresh_step_list()
            self._save()

    def _on_enter_toggle(self):
        step = self._current_step()
        if step:
            step.press_enter = self._enter_var.get()
            self._save()

    def _on_delay_change(self, event=None):
        step = self._current_step()
        if step:
            try:
                step.delay_before = float(self._delay_entry.get())
            except ValueError:
                pass
            self._save()

    def _on_name_change(self, event=None):
        if self.selected_script:
            self.selected_script.name = self._name_entry.get()
            self.selected_script.touch()
            self._refresh_script_list()
            self._save()

    def _on_desc_change(self, event=None):
        if self.selected_script:
            self.selected_script.description = self._desc_entry.get()
            self.selected_script.touch()
            self._save()

    # ══════════════════════════════════════════════════════════════════
    #  DEMO RUNNER
    # ══════════════════════════════════════════════════════════════════

    def _on_hotkey_change(self, value: str):
        self._hotkey_label = value
        key_map = {
            "F1": kb.Key.f1, "F2": kb.Key.f2, "F3": kb.Key.f3,
            "F4": kb.Key.f4, "F5": kb.Key.f5, "F6": kb.Key.f6,
            "F7": kb.Key.f7, "F8": kb.Key.f8, "F9": kb.Key.f9,
            "F10": kb.Key.f10,
        }
        self._hotkey_key = key_map.get(value, kb.Key.f2)
        if self.demo_running:
            self._stop_listener()
            self._start_listener()

    def _on_speed_change(self, value: str):
        self.typer.set_speed(value)

    def _toggle_demo(self):
        if self.demo_running:
            self._stop_demo()
        else:
            self._start_demo()

    def _start_demo(self):
        t = self.t
        if not self.selected_script or not self.selected_script.steps:
            messagebox.showinfo("No Steps", "Add steps to your script before starting.")
            return
        self.demo_running = True
        self.demo_step_idx = 0
        self._start_btn.configure(text="⏹  Stop Demo", fg_color=t["danger"], hover_color=t["danger_hover"])
        self._start_listener()
        self._update_runner_state()

    def _stop_demo(self):
        t = self.t
        self.demo_running = False
        self.typer.stop()
        self._stop_listener()
        self.demo_step_idx = 0
        self._start_btn.configure(text="▶  Start Demo", fg_color=t["success"], hover_color=t["success_hover"])
        self._update_runner_state()

    def _update_runner_state(self):
        t = self.t
        if not self.demo_running:
            self._status_dot.configure(text_color=t["text3"])
            self._status_label.configure(text="Idle", text_color=t["text3"])
            self._next_label.configure(text="")
            self._progress.set(0)
            self._refresh_step_list()
            return

        script = self.selected_script
        total = len(script.steps) if script else 0
        idx = self.demo_step_idx

        if idx >= total:
            self._status_dot.configure(text_color=t["success"])
            self._status_label.configure(text="Demo Complete", text_color=t["success"])
            self._next_label.configure(text="All steps typed — press Stop to reset.")
            self._progress.set(1.0)
            self._refresh_step_list()
            return

        step = script.steps[idx]
        self._status_dot.configure(text_color=t["accent"])
        self._status_label.configure(
            text=f"Step {idx + 1} of {total}",
            text_color=t["accent"],
        )
        preview = step.preview(70) or "(empty)"
        self._next_label.configure(text=f"Press {self._hotkey_label}  →  {preview}")
        self._progress.set(idx / total if total > 0 else 0)
        self._refresh_step_list()

    # ── Global hotkey ────────────────────────────────────────────────

    def _start_listener(self):
        self._stop_listener()
        self._listener = kb.Listener(on_press=self._on_global_key)
        self._listener.daemon = True
        self._listener.start()

    def _stop_listener(self):
        if self._listener:
            self._listener.stop()
            self._listener = None

    def _on_global_key(self, key):
        if key == self._hotkey_key and self.demo_running and not self.typer.is_typing:
            self.after(10, self._type_next_step)

    def _type_next_step(self):
        if not self.selected_script or not self.demo_running:
            return
        steps = self.selected_script.steps
        if self.demo_step_idx >= len(steps):
            return
        step = steps[self.demo_step_idx]
        self.demo_step_idx += 1
        self._update_runner_state()
        self.typer.type_text(
            text=step.text,
            press_enter=step.press_enter,
            delay_before=step.delay_before,
            on_done=lambda: self.after(0, self._on_step_typed),
        )

    def _on_step_typed(self):
        self._update_runner_state()

    # ══════════════════════════════════════════════════════════════════
    #  PERSISTENCE
    # ══════════════════════════════════════════════════════════════════

    def _save_current(self):
        pass

    def _save(self):
        self.storage.save(self.scripts)

    # ── System tray ─────────────────────────────────────────────────
    def _start_tray_icon(self):
        menu = pystray.Menu(
            pystray.MenuItem("Show DemoScripter", self._tray_show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._tray_quit),
        )
        self._tray_icon = pystray.Icon(
            "DemoScripter", _create_tray_image(), "DemoScripter", menu,
        )
        threading.Thread(target=self._tray_icon.run, daemon=True).start()

    def _tray_show(self, icon=None, item=None):
        """Restore window from tray."""
        self.after(0, self._restore_window)

    def _restore_window(self):
        self.deiconify()
        self.state("normal")
        self.lift()
        self.focus_force()

    def _tray_quit(self, icon=None, item=None):
        """Quit from tray menu."""
        self.after(0, self._full_quit)

    def _full_quit(self):
        self._stop_demo()
        self._save()
        if self._tray_icon:
            self._tray_icon.stop()
        self.destroy()

    def _minimize_to_tray(self):
        """Hide window to system tray (X button or minimize)."""
        self.withdraw()

    def _on_minimize(self, event=None):
        """Intercept minimize to send to tray instead."""
        if self.state() == "iconic":
            self.after(10, self._minimize_to_tray)

    def _on_close(self):
        self._stop_demo()
        self._save()
        if self._tray_icon:
            self._tray_icon.stop()
        self.destroy()
