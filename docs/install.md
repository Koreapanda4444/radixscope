# Installation

English | [한국어](ko/install.md)

## Windows desktop ZIP

Open a successful [Quality run](https://github.com/Koreapanda4444/radixscope/actions/workflows/quality.yml)
and download the `RadixScope-windows-x64` artifact. Extract that ZIP and the enclosed
`RadixScope-2.1.0-windows-x64.zip`. Launch `RadixScope/RadixScope.exe` from the extracted folder.
The application includes its own Python and Qt; no pip installation is needed.
Keep `_internal` beside the executable, and extract a newer package into a new folder when updating.
Preferences stay in the same per-user application data directory used by the Python installation.

## From a checkout

```sh
git clone https://github.com/Koreapanda4444/radixscope.git
cd radixscope
python -m venv .venv
```

Activate the environment with `.venv\Scripts\activate` in Windows Command Prompt,
or `source .venv/bin/activate` on Linux. Then:

```sh
python -m pip install --upgrade pip
python -m pip install ".[gui]"
python -m radixscope.gui
```

Use `python -m pip install .` for the dependency-free core and command line only.
Installing the `gui` extra adds PySide6 and Qt. The desktop entry point explains the
missing extra when PySide6 is absent.

## From a release package

Open a successful Quality run in GitHub Actions, download its package artifact and extract
the ZIP. Then run from the directory containing the wheel:

```sh
python -m pip install "radixscope-2.1.0-py3-none-any.whl[gui]"
radixscope-gui
```

Omit `[gui]` when only the command line is needed. These are Python distributions;
they require Python. The standalone desktop ZIP is a separate artifact described above.

## Linux desktop libraries

Qt needs the system graphics libraries even when imported by a headless test.
On Ubuntu/Debian, install the libraries used by CI:

```sh
sudo apt-get update
sudo apt-get install -y libegl1 libopengl0
```

For a desktop session using Qt's XCB platform, the distribution may also need
`libxcb-cursor0` and its normal X11 runtime libraries. Use `QT_QPA_PLATFORM=offscreen`
for tests without a display; that setting does not open a desktop window.

## Updating an existing checkout

```sh
git pull --ff-only origin main
python -m pip install --upgrade ".[gui]"
python -m radixscope.gui
```

The 2.0.0 rewrite replaces the old Base-Converter modules. It does not import old
configuration or history files. New preferences and recent inputs live in Qt's
per-user application data directory under `Koreapanda4444/RadixScope/state.json`.

## Building the desktop ZIP

On Windows x64, use Python 3.12 and run:

```sh
python -m pip install -e ".[desktop-build]"
python scripts/build_desktop.py
python scripts/verify_desktop.py
```

The ZIP appears in `dist/`. Verification extracts it into a temporary path containing spaces
and Unicode, then checks the actual GUI, calculation processes, bit editors and cancellation.
The development smoke switch is `RadixScope.exe --smoke-test OUTPUT.json`.
