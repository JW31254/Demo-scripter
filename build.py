"""Build script — run `python build.py` to create DemoScripter.exe"""
import PyInstaller.__main__
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

PyInstaller.__main__.run([
    os.path.join(ROOT, "main.py"),
    "--name", "DemoScripter",
    "--onefile",
    "--windowed",                       # no console window
    "--icon", os.path.join(ROOT, "assets", "app.ico"),
    "--add-data", f"{os.path.join(ROOT, 'src')};src",
    "--add-data", f"{os.path.join(ROOT, 'assets')};assets",
    "--distpath", os.path.join(ROOT, "dist"),
    "--workpath", os.path.join(ROOT, "build"),
    "--specpath", ROOT,
    "--noconfirm",
    "--clean",
    # Hidden imports that PyInstaller may miss
    "--hidden-import", "pynput.keyboard._win32",
    "--hidden-import", "pynput.mouse._win32",
    "--hidden-import", "pystray._win32",
])
