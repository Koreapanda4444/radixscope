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
`RadixScope.exe` in the project root. Keep `_internal/` beside it;
required notices are inside `_internal/licenses/`. The built application includes Python and Qt.
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

## Windows icon resources

`build/windows/` contains the ICO, seven rendered PNG sizes and product metadata.
The two SVG sources in `src/radixscope/assets/` supply the same icon family to Qt and
the EXE; a stable Windows application identity groups its running windows.
Explorer may cache an older icon after a folder replacement. Inspect the freshly built
EXE resources before treating a cached shell image as a rendering failure.

The executable is written to the folder containing `build_windows.bat`, with runtime
files in `_internal/` and notices in `_internal/licenses/`. Intermediate collection
uses `build/windows/stage/` because PyInstaller cleans its collection directory;
collecting directly into the repository root would risk deleting source files.
The publisher tracks generated files by hash and refuses to overwrite modified or
unmanaged files. It preserves unrelated files. An identified old `dist` executable
is renamed to `.exe.previous-build` so its former launch path cannot be mistaken
for the current application. Move an unrecognized old output yourself before building.
Open `_internal/licenses/NOTICE.html` to view the bundled license texts, inventory and matching
upstream source locations. LGPL libraries remain replaceable under `_internal/`.
Retain the notices and equivalent access to corresponding sources when redistributing.
