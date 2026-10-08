# -*- mode: python ; coding: utf-8 -*-
"""Portable Qt build with an isolated Windows DLL search path."""
import os
from pathlib import Path
import sys
import PySide6
import shiboken6

source = Path(SPECPATH)
qt_dir = Path(PySide6.__file__).parent
shiboken_dir = Path(shiboken6.__file__).parent
windows = Path(os.environ.get('SystemRoot', 'C:/Windows'))

# Do not collect DLLs from unrelated applications on the build host's PATH.
os.environ['PATH'] = os.pathsep.join(str(p) for p in (
    Path(sys.base_prefix), qt_dir, shiboken_dir, windows / 'System32', windows
))
runtime_names = ('VCRUNTIME140.dll', 'VCRUNTIME140_1.dll', 'MSVCP140.dll',
                 'MSVCP140_1.dll', 'MSVCP140_2.dll')
runtimes = [(str(qt_dir / name), '.') for name in runtime_names
            if (qt_dir / name).exists()]

a = Analysis(
    [str(source / 'app.py')],
    pathex=[str(source)],
    binaries=runtimes,
    datas=[(str(source / 'assets'), 'assets')],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['numpy', 'matplotlib', 'pandas', 'scipy', 'IPython', 'tkinter', 'PIL'],
    noarchive=False, optimize=0,
)
# UCRT is supplied by Windows. A private copy from another OS build can fail
# during DLL import even when the Python source runs correctly on this machine.
a.binaries = [entry for entry in a.binaries
              if Path(entry[0]).name.lower() != 'ucrtbase.dll']
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name=os.environ.get('DUST_EXE_NAME', 'GenshinDustCalculator'),
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    runtime_tmpdir=None, console=False, disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None, codesign_identity=None,
    entitlements_file=None, icon=[str(source / 'assets' / 'icon.ico')],
)
