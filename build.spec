# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

# Find snap7 DLL for Windows
snap7_binaries = []
if sys.platform == 'win32':
    try:
        import snap7
        snap7_dir = os.path.dirname(snap7.__file__)
        # Search for snap7.dll
        for root, dirs, files in os.walk(snap7_dir):
            for f in files:
                if f.lower() == 'snap7.dll':
                    dll_path = os.path.join(root, f)
                    snap7_binaries.append((dll_path, '.'))
                    print(f"Found snap7.dll: {dll_path}")
                    break
    except ImportError:
        print("WARNING: snap7 not installed, DLL will not be bundled")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=snap7_binaries,
    datas=[],
    hiddenimports=[
        'snap7',
        'snap7.client',
        'snap7.util',
        'snap7.type',
        'configparser',
        'struct',
        'threading',
        'csv',
        'datetime',
        'shutil',
        'logging',
        'signal',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='TDK2-Traceability',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Console application - show output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
