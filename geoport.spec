# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path
from PyInstaller.utils.hooks import copy_metadata, collect_data_files, collect_dynamic_libs

block_cipher = None
base_dir = Path.cwd()

added_files = [
    ('src/static', 'src/static'),
    ('src/templates', 'src/templates'),
]

# Collect package metadata required by importlib.metadata.version()
for pkg in ['pyimg4', 'pymobiledevice3', 'pykdebugparser', 'developer-disk-image', 'remotezip2', 'fastapi', 'starlette']:
    try:
        added_files.extend(copy_metadata(pkg))
    except Exception as e:
        print(f"Warning: could not copy metadata for {pkg}: {e}")

# Collect data files and native binaries (like wintun.dll for pymobiledevice3/pytun_pmd3)
added_binaries = []
for pkg in ['pymobiledevice3', 'pytun_pmd3']:
    try:
        added_files.extend(collect_data_files(pkg))
    except Exception as e:
        print(f"Warning: could not collect data files for {pkg}: {e}")
    try:
        added_binaries.extend(collect_dynamic_libs(pkg))
    except Exception as e:
        print(f"Warning: could not collect dynamic libs for {pkg}: {e}")

hidden_imports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.lifespans',
    'uvicorn.lifespans.auto',
    'uvicorn.lifespans.on',
    'fastapi',
    'pydantic',
    'pymobiledevice3',
    'httpx',
    'jinja2',
    'pyuac',
    'pycountry',
    'websockets',
    'pyimg4',
    'ipsw_parser',
    'pytun_pmd3',
]

a = Analysis(
    ['src/main.py'],
    pathex=[str(base_dir)],
    binaries=added_binaries,
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'PIL'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GeoPort-v5.0-Windows',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
