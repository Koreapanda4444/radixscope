# RadixScope

RadixScope is a Python and PySide6 desktop and command-line tool for exact numbers,
fixed-width integers, floating-point precision, bytes and bitfields.

English | [한국어](README.ko.md)

## Features

- Exact base 2–36 conversion, ratios, recurring fractions and scientific notation.
- Exact expressions, conversion traces and fixed-width arithmetic with overflow analysis.
- Number Inspector with synchronized values, raw bits and endian byte representations.
- binary16, bfloat16, binary32 and binary64 encoding, decoding and precision comparison.
- Rational error, ULP spacing, neighboring values, subnormal boundaries and NaN payloads.
- Hex/Binary/Base64/UTF-8 byte input, saved bitfield layouts and binary differences.
- Batch conversion, searchable history, result reuse and text/JSON/CSV export.
- English/Korean interface, light/dark/system themes and cancellable calculations.

## Install and run

From a checkout, use Python 3.11 or newer:

```sh
python -m pip install ".[gui]"
python -m radixscope.gui
```

For the dependency-free Core and CLI, install with `python -m pip install .` and run:

```sh
python -m radixscope convert FF --from 16 --to 2 8 10 16
```

Installed commands are `radixscope` and `radixscope-gui`.
Windows x64 packages are available as `RadixScope-windows-x64` from successful
[Quality runs](https://github.com/Koreapanda4444/radixscope/actions/workflows/quality.yml).
See the installation guide for setup and portable execution.

## Documentation

- [Installation, updates and data locations](docs/install.md)
- [Desktop usage](docs/usage.md)
- [Command-line usage](docs/cli.md)
- [Numeric models, Python API and work limits](docs/specification.md)
- [Development, verification and builds](docs/development.md)

Raw reinterpretation preserves bits; numeric conversion follows the destination format.
Use text or `ExactValue` for exact decimal input. Output and work limits are explicit
and do not silently change the stored rational value.

## Development

```sh
python -m pip install -e ".[dev]"
python -m ruff check src scripts packaging
python -m mypy src scripts packaging
python scripts/verify_numeric.py
python -m radixscope.gui.verification
```

Existing verification uses temporary data. Quality checks Ubuntu and Windows on
Python 3.11–3.13, Python distributions and the Windows desktop build, including
installation and uninstall. See the development guide for build commands.
