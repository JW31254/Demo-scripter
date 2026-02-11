# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\jackwicks\\OneDrive - Microsoft\\Desktop\\Work\\Projects\\DemoScripter\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\jackwicks\\OneDrive - Microsoft\\Desktop\\Work\\Projects\\DemoScripter\\src', 'src'), ('C:\\Users\\jackwicks\\OneDrive - Microsoft\\Desktop\\Work\\Projects\\DemoScripter\\assets', 'assets')],
    hiddenimports=['pynput.keyboard._win32', 'pynput.mouse._win32', 'pystray._win32'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DemoScripter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\jackwicks\\OneDrive - Microsoft\\Desktop\\Work\\Projects\\DemoScripter\\assets\\app.ico'],
)
