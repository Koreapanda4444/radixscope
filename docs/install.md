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

The BAT reuses compatible build dependencies, installing missing ones when needed,
and creates `RadixScope.exe` in the project root. Keep `_internal/` beside it.
No installer or ZIP is generated. Existing build dependencies can be reused offline.

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

## Windows icon resources

`build/windows/` contains the ICO, seven rendered PNG sizes and product metadata.
The two SVG sources in `src/radixscope/assets/` supply the same icon family to Qt and
the EXE; a stable Windows application identity groups its running windows.
Explorer may cache an older icon after a folder replacement. Inspect the freshly built
EXE resources before treating a cached shell image as a rendering failure.

The executable is written beside `build_windows.bat`, with its runtime in `_internal/`.
PyInstaller first builds into `build/windows/stage/` so it cannot overwrite source files.
The publisher copies only generated outputs, protects unrelated files, and preserves
unrecognized existing files.
