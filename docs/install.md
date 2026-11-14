# Installation and execution

English | [한국어](ko/install.md)

## Run from source

Use Python 3.11 or newer. In the repository folder:

```sh
python -m venv .venv
```

Activate with `.venv\Scripts\activate` in Windows Command Prompt, or
`source .venv/bin/activate` on Linux/macOS. Then run:

```sh
python -m pip install ".[gui]"
python -m radixscope.gui
```

For the dependency-free Core and CLI, use `python -m pip install .`.
Installed commands are `radixscope` and `radixscope-gui`.

## Windows executable

On Windows with x64 Python 3.11 or newer available as `python`, run:

```powershell
.\build_windows.bat
```

The BAT installs build dependencies into the current Python environment and creates
`dist/RadixScope/RadixScope.exe`. Run it from that folder; keep `_internal/` and
`licenses/` with it. The built application includes Python and Qt.
No installer or ZIP is generated.

## Settings and updates

Settings remain in Qt's per-user application data directory under
`Koreapanda4444/RadixScope/state.json`, separately from the program folder.
Close the app before replacing a built program folder. Preserve the settings file
if moving to another computer.

For a source checkout update, close the app and run:

```sh
git pull --ff-only origin main
python -m pip install --upgrade ".[gui]"
```

## Linux graphics libraries

Qt needs the system graphics libraries. On Ubuntu/Debian:

```sh
sudo apt-get update
sudo apt-get install -y libegl1 libopengl0 libxkbcommon0
```

A desktop session using XCB may also need `libxcb-cursor0` and the distribution's
usual X11 libraries. Install GUI dependencies using the project's version constraints.

## Verification and icon resources

After installing the source package, `python scripts/check_numeric.py` checks Core and
CLI behavior. Add `--desktop` for Qt and `--exhaustive` for all binary16/bfloat16 patterns.
After building on Windows, run:

```powershell
python scripts/check_numeric.py --desktop --exe dist/RadixScope/RadixScope.exe
```

This checks x64 resources, frozen calculations, native window icons and normal shutdown.
`build/windows/` contains the ICO, seven rendered PNG sizes and product metadata.
The two SVG sources in `src/radixscope/assets/` supply the same icon family to Qt and
the EXE; a stable Windows application identity groups its running windows.
Explorer may cache an older icon after a folder replacement. Inspect the freshly built
EXE resources before treating a cached shell image as a rendering failure.

The desktop validation workflow builds with this same BAT. Its artifacts contain icon
validation resources; application builds remain in the BAT's generated program folder.
