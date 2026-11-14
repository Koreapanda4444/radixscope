# RadixScope

English | [한국어](README.ko.md)

## Overview

RadixScope is a Python and PySide6 application for exact number conversion and
analysis of numeric representations. It connects fractions, fixed-width integers,
floating-point formats and raw bytes in one desktop interface, with the same
operations available through a CLI and Python API. Use it to understand both a
number's mathematical value and the bits used to represent it.

## Features

### Exact numbers and expressions

Convert between bases 2–36 using integers, fractions, recurring decimals and
scientific notation. Evaluate mixed-base expressions and follow conversion steps
in Trace. Exact calculations retain rational values; precision and rounding choices
control how results are displayed.

### Number Inspector and integer operations

Inspect one value as binary, octal, decimal, hexadecimal, signed/unsigned integers
and endian byte sequences. Edit raw bits or Hex patterns to see their interpretation
change. Fixed-width arithmetic separates the exact result, overflow status and
wrapped result, alongside bitwise operations and shifts.

### Floating-point analysis

Encode and decode binary16, bfloat16, binary32 and binary64, or compare their
representations of the same input. Inspect sign, exponent, significand, signed zero
and NaN payloads, then explore absolute/relative error, ULP spacing, neighboring
values and normal/subnormal boundaries.

### Batch work, history and exports

Convert multiple values or expressions together while retaining per-line results
and errors. Search previous calculations, restore inputs and reuse results across
workspaces, then export text, JSON or CSV. The desktop supports English/Korean and
light, dark and system themes.

## Usage

### Explore a value in the GUI

### Use the command line

After installation, the same operations can be run from a terminal:

```sh
python -m radixscope convert FF --from 16 --to 2 8 10 16
python -m radixscope expression "(0xFF & 0x0F) << 2" --to 2 10 16
python -m radixscope inspect FF --base 16 --width 8 --signed --pattern
python -m radixscope ieee compare "1/10" --json
```

These examples convert hexadecimal `FF` to four bases, evaluate a bitwise expression,
reinterpret an eight-bit pattern as a signed integer, and compare floating-point
formats for an exact fraction. Use `--help` on any command for its options. The Python
API exposes the same numeric models and operations; examples are in the numeric
specification.

## Getting Started

### Run from source

Use Python 3.11 or newer. From the repository folder:

```sh
python -m pip install ".[gui]"
python -m radixscope.gui
```

For the dependency-free Core and CLI only, use `python -m pip install .`.
Installed commands are `radixscope` and `radixscope-gui`. Platform requirements and
settings locations are described in the installation guide.

### Build the Windows application

On Windows, use 64-bit Python 3.11 or newer available as `python`, and run:

```powershell
.\build_windows.bat
```

The BAT installs build dependencies into the current Python environment and creates
`dist/RadixScope/RadixScope.exe`. Run that EXE from the generated folder and keep
`_internal/` and `licenses/` with it. The built application includes Python and Qt;
it is created locally from this repository's source code.

## Documentation

- [Installation and execution](docs/install.md) — environment setup, settings and updates.
- [Desktop usage](docs/usage.md) — workspace controls, result reuse, history and exports.
- [Command-line usage](docs/cli.md) — commands, input forms and output options.
- [Numeric rules and Python API](docs/specification.md) — exact values, bit representations, floating-point rules and API examples.
