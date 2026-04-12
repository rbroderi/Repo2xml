from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_submodules

data = collect_data_files("magika")
hiddenimports = collect_submodules("markitdown")


a = Analysis(
    ["src/repo2xml/__main__.py"],
    pathex=["src"],
    binaries=[],
    data=data,
    hiddenimports=hiddenimports,
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
    a.data,
    [],
    exclude_binaries=False,
    name="repo2xml",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
