# Bundled components

The desktop package includes Python, PySide6 / Qt, and the PyInstaller bootloader.
The shared libraries remain in `_internal` alongside the application.

- Python: [PSF license](https://docs.python.org/3/license.html).
- PySide6 / Qt for Python: [licensing information](https://doc.qt.io/qtforpython-6/licenses.html).
- Qt: [open source licensing](https://www.qt.io/licensing/open-source-lgpl-obligations).
- PyInstaller bootloader: [GPL with distribution exception](https://pyinstaller.org/en/stable/license.html).

Included dependency license files are copied into `licenses` when available in the
installed distributions. Qt for Python source and installation packages are available
through its official project; matching component versions are listed in `build-info.json`.
