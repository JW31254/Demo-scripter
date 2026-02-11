# ⚡ DemoScripter — Presales Demo Script Assistant

A modern desktop application for presales consultants to create and run **live chat demo scripts**. Instead of pasting text, DemoScripter **types each message character-by-character** into any chat window — making it look like someone is genuinely typing in real time.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Script Management** | Create, edit, and organise multiple demo scripts |
| **Step-by-Step Messages** | Each script has ordered steps — one per chat message |
| **Realistic Typing** | Text is typed out keystroke-by-keystroke with natural speed variation |
| **Global Hotkey** | Press a configurable hotkey (F1–F10) to trigger the next step — even while the app is in the background |
| **Role Tagging** | Tag each step as *Agent*, *Customer*, or *System* for clarity |
| **Speed Control** | Choose from *Slow*, *Normal*, *Fast*, or *Very Fast* typing presets |
| **Auto Enter** | Optionally press Enter after typing to send the message automatically |
| **Persistent Storage** | Scripts are saved locally as JSON — they survive restarts |
| **Dark Modern UI** | Built with CustomTkinter for a clean, professional look |

---

## 🚀 Quick Start

## For EXE go to https://github.com/JW31254/Demo-scripter/releases/

### 1. Install dependencies

```bash
cd DemoScripter
pip install -r requirements.txt
```

### 2. Run the app

```bash
python main.py
```

---

## 🎯 How to Use

### Creating a script

1. Click **＋ New** in the sidebar to create a script
2. Give it a name (e.g. "Product Support Demo")
3. Click **＋** above the steps list to add steps
4. For each step:
   - Select a **Role** (Agent / Customer / System)
   - Type the **message text** in the editor
   - Toggle whether **Enter** should be pressed after typing
   - Set a **delay** before typing starts (useful for positioning your cursor)

### Running a demo

1. Select the script you want to run
2. Configure the **Hotkey** (default: F2) and **Speed** (default: Fast)
3. Click **▶ Start Demo**
4. Switch to your target chat window (Teams, browser chat, etc.)
5. Press **F2** — DemoScripter types out the first step character-by-character
6. Continue pressing **F2** for each subsequent step
7. The status bar shows your progress and previews the next step
8. Click **⏹ Stop Demo** when finished

### Tips for great demos

- **Set the speed to "Fast"** — it looks like confident, quick typing
- **Enable "Press Enter after typing"** so messages send automatically
- **Use the delay** setting (0.3–1s) to give yourself time to position the cursor
- **Minimise the DemoScripter window** — the hotkey works globally even when minimised
- **Prepare both sides**: create steps for both Agent and Customer if you're driving both sides of a conversation

---

## 📁 Project Structure

```
DemoScripter/
├── main.py              # Entry point
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── data/
│   └── scripts.json     # Your saved scripts (auto-created)
└── src/
    ├── __init__.py
    ├── app.py           # Main UI application (CustomTkinter)
    ├── models.py        # Script & Step data models
    ├── storage.py       # JSON persistence
    └── typer_engine.py  # Keystroke simulation engine
```

---

## ⚙️ Configuration

| Setting | Options | Default | Where |
|---|---|---|---|
| Hotkey | F1 – F10 | F2 | Runner bar dropdown |
| Typing speed | Slow / Normal / Fast / Very Fast | Fast | Runner bar dropdown |
| Press Enter | On / Off per step | On | Step editor checkbox |
| Delay before typing | 0 – 5 seconds per step | 0.3s | Step editor field |

---

## 🔧 Requirements

- **Python 3.10+**
- **Windows** (tested; macOS/Linux should work with pynput but may need accessibility permissions)
- Dependencies: `customtkinter`, `pynput`

---

## 📄 Licence

Internal tool — use freely within your organisation.

