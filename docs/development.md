# Development, verification and builds

English | [한국어](ko/development.md)

## Source layout

| Location | Responsibility |
| --- | --- |
| `src/radixscope/core/` | Dependency-free exact numeric models and public API |
| `cli.py`, `reports.py`, `exports.py` | CLI commands, shared reports and serialization |
| `calculations.py`, `worker.py` | Calculation requests and cancellable process execution |
| `src/radixscope/gui/` | PySide6 workspaces, localization and presentation |
| `settings.py` | Compatible GUI settings and history storage |
| `src/radixscope/assets/` | Packaged application icon, control SVGs and Korean translations |
| `scripts/`, `packaging/` | Verification/build entry points and desktop launch/installer inputs |

The public Core API and CLI remain independent of Qt. Shared reports keep exports
consistent across the CLI and GUI; GUI modules do not belong in Core.
`gui/verification.py` is also used by the packaged EXE's `--self-check` path, so it
remains in the package. Build-time checks stay under `scripts/`.

## Source verification

```sh
python -m pip install -e ".[dev]"
python -m ruff check src scripts packaging
python -m mypy src scripts packaging
python scripts/verify_numeric.py
python -m radixscope.gui.verification
python -m build
python scripts/verify_repository.py --packages
```

`verify_numeric.py --exhaustive` additionally checks every 16-bit float pattern.
GUI verification uses temporary settings, checks both languages, all workspaces,
transfers, cancellation, exports and state restoration. Repository verification
checks local document links, Python/CLI examples and built package resources.
Set `QT_QPA_PLATFORM=offscreen` when running GUI checks without a desktop.

## CI and generated files

`.github/workflows/quality.yml` runs Quality on Ubuntu and Windows with Python
3.11–3.13. Its dependent Windows desktop job uses Python 3.12 x64. The integrated
workflow is kept because the desktop build depends on the complete quality matrix.
Checks use temporary data; build output, verification receipts, caches and local
environments are ignored by Git. Icons and translation resources remain packaged
assets. Existing product version and Windows metadata come from their current sources.

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
