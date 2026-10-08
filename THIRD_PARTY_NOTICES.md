# Third-party materials

The MIT license applies to original project code. It does not replace the
licenses or copyrights of the following components.

| Component | Role | Upstream license / attribution |
|---|---|---|
| Python | Runtime embedded in the Windows executable | PSF License Agreement |
| PySide6 / Shiboken6 / Qt | GUI bindings and dynamically loaded Qt libraries | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only; this project uses the LGPL option |
| PyInstaller | Build tool and executable bootloader | GPLv2-or-later with bootloader distribution exception |
| Pillow | Development-only icon/image preparation | MIT-CMU; excluded from the executable |
| Genshin Impact item artwork | `assets/brand.png` and derived `assets/icon.ico` | Original rights belong to HoYoverse / miHoYo; not covered by MIT |

The original item asset is `UI_ItemIcon_TrainingIteration`, item ID 105006,
mirrored by Yatta. See [asset sources](assets/SOURCES.md). Small control glyphs
were drawn by the project. Microsoft YaHei UI is requested from the user's
system; no font file is distributed.

Qt runtime libraries are supplied as separate DLLs in the PyInstaller bundle.
The complete application source, dependency versions and build instructions are
provided so the application can be rebuilt against compatible Qt libraries.
Relevant upstream license text is included under `licenses/` in the repository
and Windows ZIP release. Do not interpret the project MIT license as permission
to relicense the item artwork or third-party runtimes.

Upstream source and license references:

- [Python license](https://docs.python.org/3/license.html)
- [Qt for Python source](https://code.qt.io/cgit/pyside/pyside-setup.git/)
- [Qt source](https://code.qt.io/cgit/qt/qtbase.git/)
- [Qt licensing](https://doc.qt.io/qt-6/licensing.html)
- [PyInstaller license](https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt)
- [Pillow license](https://github.com/python-pillow/Pillow/blob/main/LICENSE)
