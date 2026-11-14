# RadixScope

English | [한국어](README.ko.md)

RadixScope is a desktop and command-line tool for exact number conversion and
bit-level analysis. It brings integer, floating-point and byte representations
together without losing the original exact value.

## Features

- Exact base 2–36 conversion, fractions, recurring decimals and expression evaluation.
- Fixed-width integer arithmetic, overflow analysis and editable bit representations.
- binary16, bfloat16, binary32 and binary64 inspection, precision errors and neighboring values.
- Byte inspection, saved bitfield layouts and binary comparison.
- Batch conversion, searchable history and text/JSON/CSV export.
- GUI, CLI and Python API, with English/Korean UI and light/dark/system themes.

## Getting Started

Use Python 3.11 or newer from the repository folder:

```sh
python -m pip install ".[gui]"
python -m radixscope.gui
```

For the CLI only, install with `python -m pip install .`:

```sh
python -m radixscope convert FF --from 16 --to 2 8 10 16
python -m radixscope ieee encode "1/10" --format binary32
```

Installed commands are `radixscope` and `radixscope-gui`.
On Windows, `build_windows.bat` creates `dist/RadixScope/RadixScope.exe`.
Keep the whole program folder, including `_internal/`, together.
See the installation guide for prerequisites, settings and updates.

## Documentation

- [Installation and execution](docs/install.md)
- [Desktop usage](docs/usage.md)
- [Command-line usage](docs/cli.md)
- [Number rules and Python API](docs/specification.md)

Use text or `ExactValue` for exact decimal input. Raw reinterpretation preserves
bits; numeric conversion follows the destination format. Work limits are reported
without silently changing the stored rational value.
