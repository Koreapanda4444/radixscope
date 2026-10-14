# RadixScope

English | [한국어](README.ko.md)

RadixScope 2.1.0 converts exact numbers between bases 2 through 36 and inspects the
bits behind fixed-width integers and IEEE 754 floating-point values. It provides a
command line interface and a PySide6 desktop application.

Version 2.0 rewrote Base-Converter as RadixScope, adding exact arithmetic, bit inspection
and a new desktop app. It does not import the old application's settings or history.

## Install and run

For Windows x64, download the `RadixScope-windows-x64` artifact from a successful
[Quality run](https://github.com/Koreapanda4444/radixscope/actions/workflows/quality.yml).
Extract the artifact ZIP, then extract the enclosed `RadixScope-2.1.0-windows-x64.zip`
and run `RadixScope/RadixScope.exe`. Keep the entire folder together, including `_internal`.
This package includes Python and Qt.

Source and wheel installations require Python 3.11 or newer. From a checkout of this repository:

```sh
python -m pip install ".[gui]"
python -m radixscope.gui
```

For the command line and Python API alone, install with `python -m pip install .`.
The installed commands are `radixscope` and `radixscope-gui`.
On Windows, `py` can replace `python` in these commands.

```sh
radixscope convert FF --from 16 --to 2 8 10 16
radixscope expression "0x10 + 2#11 / 10#2" --to 2 10 16
radixscope trace "1/3" --to 2 --json
radixscope integer 127 --width 8 --signed --op add --operand 1 --json
radixscope ieee encode "1/10" --width 32
radixscope ieee decode 3F800000 --width 32
```

Wheel and source packages are attached as artifacts to successful [Quality workflow runs](https://github.com/Koreapanda4444/radixscope/actions/workflows/quality.yml).
See the [installation guide](docs/install.md) for package installation and Linux desktop dependencies.

## Features

- Exact integers, finite fractions, ratios and recurring digits such as `0.(3)`
- Multiple output bases, explicit precision and five rounding modes
- Mixed-base expressions with `base#digits`, `0b`, `0o`, `0x` and exact arithmetic
- Integer division and fractional multiplication traces, including cycle detection
- Arbitrary-width signed and unsigned integers, two's complement and bitwise operations
- Range and overflow analysis with separate exact and wrapped results
- Big-endian and little-endian bytes, strict ASCII codecs and printable previews
- Binary32 and binary64 encoding and decoding, including subnormals, signed zero and NaNs
- Four desktop workspaces, clipboard output, themes, saved options and bounded recent history
- Isolated desktop calculations with cancellation and input-change protection
- Editable integer and IEEE 754 bits with synchronized numeric and byte representations
- Windows x64 desktop ZIP that runs without a separate Python installation

IEEE encoding rounds exact rational inputs directly using nearest, ties to even.
Raw decoding preserves NaN payloads and signaling bits. A host Python float already contains
a rounded binary value; use exact numeric input when decimal precision matters.

## Python API

```python
from radixscope.core import ExactValue, convert_bases, encode_ieee754, evaluate_expression

value = evaluate_expression("0x10 + 2#11 / 10#2")
print(convert_bases(value, [2, 10, 16]))
print(encode_ieee754(ExactValue(1, 10), 32).hexadecimal)
```

## Documentation

- [Command line](docs/cli.md)
- [Desktop application](docs/desktop.md)
- [Numeric specification](docs/specification.md)

Exact expansions can have long periods. CLI exact output is unlimited; choose `--precision`
for a bounded expansion. Desktop exact conversion displays at most 1000 fractional digits
and marks incomplete output explicitly. The trace workspace offers an adjustable limit.
Expression evaluation and integer operations use arbitrary-size integers; very large powers
or inputs can take substantial time and memory.

## Development

```sh
python -m pip install -e ".[dev]"
python -m ruff check src scripts packaging
python -m mypy src scripts packaging
python -m build
```

Quality runs check lint and types, run the CLI version command, and build wheel and source
packages on Ubuntu and Windows with Python 3.11, 3.12 and 3.13. Packages are retained as
workflow artifacts. No PyPI publishing is configured. The Windows desktop job builds the
standalone ZIP. To reproduce that build on Windows, install
`python -m pip install -e ".[desktop-build]"`, then run `python scripts/build_desktop.py`.
