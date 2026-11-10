# Installation and packaging

English | [한국어](ko/install.md)

## Windows x64

Download `RadixScope-windows-x64` from a successful
[Quality run](https://github.com/Koreapanda4444/radixscope/actions/workflows/quality.yml).
Extract the Actions artifact first, then choose:

| Package | Use |
| --- | --- |
| `RadixScope-*-windows-x64-setup.exe` | Install for the current user, with a Start menu shortcut and uninstaller |
| `RadixScope-*-windows-x64.zip` | Extract and run `RadixScope/RadixScope.exe` without installation |

Both contain the Python runtime, Qt, icon, English/Korean resources, documentation
and third-party license notices. Keep all portable files together; moving only the
EXE will break its runtime. Administrator rights are not required for the default
per-user installation. The installer offers an optional desktop shortcut.
Remove it through Windows Installed apps or its `unins000.exe`.

Preferences live separately under Qt's per-user application data directory,
`Koreapanda4444/RadixScope/state.json`. Uninstalling does not erase this user data.
For portable updates, close the app and extract into a fresh folder. For installed
updates, close the app and run setup against the same installation directory.

## Python installation

Python 3.11 or newer is required for source and wheel distributions.

```sh
git clone https://github.com/Koreapanda4444/radixscope.git
cd radixscope
python -m venv .venv
```

Activate with `.venv\Scripts\activate` in Windows Command Prompt, or
`source .venv/bin/activate` on Linux. Then:

```sh
python -m pip install --upgrade pip
python -m pip install ".[gui]"
python -m radixscope.gui
```

Install with `python -m pip install .` for Core/CLI only. A downloaded wheel is
installed by passing its actual filename to pip; append `[gui]` inside the quoted
filename when desktop dependencies are needed. Wheels and source archives are in
the `packages-<os>-py<python>` Actions artifacts. They require Python, unlike the
standalone Windows packages.

```sh
git pull --ff-only origin main
python -m pip install --upgrade ".[gui]"
radixscope-gui
```

GUI dependencies exclude PySide6 6.12.0 because of
[the upstream singleton reference-counting regression](https://qt-project.atlassian.net/browse/PYSIDE-3474).
Use the project's dependency constraints when installing the GUI.

## Linux graphics libraries

Even offscreen Qt requires system graphics libraries. On Ubuntu/Debian:

```sh
sudo apt-get update
sudo apt-get install -y libegl1 libopengl0 libxkbcommon0
```

A desktop session using XCB may also require `libxcb-cursor0` and the distribution's
normal X11 libraries. `QT_QPA_PLATFORM=offscreen` runs integration verification
without opening a visible desktop window.

## Build and verify

On Windows x64, use Python 3.12. Install Inno Setup 6.3 or newer for the installer;
make `ISCC` available on PATH or use its standard Inno Setup 6 installation location.

```sh
python -m pip install -e ".[desktop-build]"
python scripts/build_desktop.py --installer
python scripts/verify_windows.py
```

Omit `--installer` to build only the portable ZIP. Outputs are in `dist/`.
PyInstaller bundles the runtime; the build preserves dependency license files in
`licenses/`.

Verification extracts the actual ZIP into a temporary directory, runs all desktop
workspaces, installs setup into another temporary directory, repeats the checks,
and uninstalls. It checks bilingual UI state, cancellation, settings, runtime
availability and the icon. JSON receipts and installer logs go to
`build/desktop/verification/`; CI publishes them as
`Windows-distribution-verification`. CI also checks Windows EXE product metadata.

For source validation, see the commands in the [README](../README.md).
