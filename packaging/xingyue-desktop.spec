# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
SRC = ROOT / "src"
RESOURCES = ROOT / "resources"
CONFIG = ROOT / "config"

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=[(str(RESOURCES), "resources")],
    hiddenimports=[],
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
    name="XingYueDesktop",
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
    version=str(CONFIG / "version_info.txt"),
    icon=[str(RESOURCES / "icons" / "icon.ico")],
)
