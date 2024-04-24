# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['server_build.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['bson.raw_bson', 'bson'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['client', 'matplotlib', 'matplotlib.pyplot', 'prompt_toolkit', 'PySide2', 'PyQt6'],
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
    name='server_build',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
