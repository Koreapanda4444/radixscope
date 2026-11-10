# RadixScope

English | [한국어](README.ko.md)

RadixScope is a desktop and command-line workbench for exact numbers, fixed-width
integers, floating-point precision, bytes and bitfields. The Python core is shared
by the CLI and PySide6 interface.

## Install and run

On Windows x64, download the `RadixScope-windows-x64` artifact from a successful
[Quality run](https://github.com/Koreapanda4444/radixscope/actions/workflows/quality.yml).
Extract the artifact and choose the setup executable or the enclosed portable ZIP.
The installer adds an application shortcut and an uninstaller. For the portable
package, extract its ZIP and run `RadixScope/RadixScope.exe`; keep the entire folder,
including `_internal`, together. Both packages include Python and Qt.

From a checkout, with Python 3.11 or newer:

```sh
python -m pip install ".[gui]"
python -m radixscope.gui
```

Use `python -m pip install .` for the dependency-free core and CLI.
Installed entry points are `radixscope` and `radixscope-gui`.
See [installation](docs/install.md) for virtual environments, Linux libraries,
updating, wheel packages and local desktop builds.

## What it does

- Exact conversion between bases 2–36, ratios, recurring fractions and decimal scientific notation.
- Exact expressions with arithmetic, floor division, remainder, bitwise operators and shifts.
- Number Inspector with synchronized numeric, signed, bit and endian byte representations.
- Fixed-width integer operations with separate exact, overflow and wrapped results.
- binary16, bfloat16, binary32 and binary64 encoding, raw decoding and format comparison.
- Rational error analysis, ULP spacing, neighboring floats, subnormal boundaries and NaN payloads.
- Byte selection, Hex/Binary/Base64/UTF-8 input, ASCII previews and saved bitfield layouts.
- Binary comparison with XOR, changed bits/bytes and field-level differences.
- Batch conversion, searchable history, result reuse and text/JSON/CSV export.
- English/Korean desktop UI, light/dark themes, editable bits and cancellable worker processes.

Raw reinterpretation preserves bits. Numeric conversion preserves the mathematical
value subject to the destination format. IEEE encoding rounds exact rational inputs
directly to the destination using nearest, ties to even. A Python `float` already
contains a rounded binary value; use `ExactValue` or text for exact decimal input.

## CLI examples

```sh
radixscope convert FF --from 16 --to 2 8 10 16
radixscope convert "1.25e-3" --auto --to 10 16
radixscope expression "(0xFF & 0x0F) << 2" --to 2 10 16
radixscope trace "1/7" --to 2 --max-steps 12 --json
radixscope inspect FF --base 16 --width 8 --signed --pattern
radixscope integer 127 --width 8 --signed --op add --operand 1
radixscope ieee encode "1/10" --format bfloat16 --json
radixscope ieee compare "1/10"
radixscope bytes "3F 80 00 00" --byteorder big
radixscope compare "FF 00" "FE 80" --json
radixscope batch --file numbers.txt --mode auto --to 2 10 16 --csv
```

Every command has `--help` and `--json`. Batch CSV includes per-line errors.
See the [CLI guide](docs/cli.md).

## Python API

```python
from radixscope.core import (
    ExactValue, convert_bases, encode_ieee754, evaluate_expression, inspect_number,
)

value = evaluate_expression("0x10 + 2#11 / 10#2")
assert value == ExactValue(35, 2)
print(convert_bases(value, [2, 10, 16]))
print(encode_ieee754(ExactValue(1, 10), "binary16").hexadecimal)
assert inspect_number("FF", base=16, width=8, signed=True, raw=True).exact == ExactValue(-1)
```

## Documentation and development

- [Installation and packaging](docs/install.md)
- [Command line](docs/cli.md)
- [Desktop workspaces and history](docs/desktop.md)
- [Numeric models, API and work limits](docs/specification.md)

```sh
python -m pip install -e ".[dev]"
python -m ruff check src scripts packaging
python -m mypy src scripts packaging
python scripts/verify_numeric.py
python -m radixscope.gui.verification
python -m build
python scripts/verify_repository.py --packages
```

Quality checks Ubuntu and Windows on Python 3.11–3.13, builds wheel/source packages,
and validates extracted and installed Windows desktop applications, including uninstall.
Artifacts remain attached to Actions runs.

Exact arithmetic does not imply unlimited work. Expansions, powers, traces, byte
buffers and batches have explicit resource limits. The GUI marks partial expansions;
limits do not silently alter the stored rational value. See the numeric specification.
