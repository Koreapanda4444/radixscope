# RadixScope

English | [한국어](README.ko.md)

<img src="src/radixscope/assets/radixscope.svg" width="80" alt="RadixScope RS icon">

RadixScope is a desktop tool for radix conversion, exact calculation and analysis of
numeric representations. Python integers and rational arithmetic preserve the
mathematical value while fixed-width and floating-point views explain its encoding.
The Core is also available through a command line and Python API.

## Features

| Workspace | What you can do |
| --- | --- |
| Conversion | Convert bases 2–36; enter fractions, recurring digits or scientific notation; choose rounding; inspect conversion steps; use presets and swap bases. |
| Calculation | Evaluate mixed-base expressions or fixed-width integer operations; distinguish exact results, overflow and wrapping; extract bit ranges and inspect required widths. |
| Number Inspector | Explore numeric, signed/unsigned, bit and endian byte representations; edit bits/Hex; analyze four floating formats; compare numbers and experiment with rounded arithmetic. |
| Batch Conversion | Convert values or expressions by line, retain individual errors and export results. |

Floating-point tools support binary16, bfloat16, binary32 and binary64, with exact
representation errors, ULPs, adjacent values, signed zero and NaN payloads. Arithmetic
experiments compare rounding operands first against rounding the exact result once.

The GUI supports English/Korean, light/dark/system themes, searchable history,
individual result copying and text/JSON/CSV export. Computations run in cancellable
worker processes; changing input clears obsolete results.

## Run from source

Use Python 3.11 or newer. From the repository folder:

```sh
python -m pip install ".[gui]"
python -m radixscope.gui
```

For the dependency-free Core and CLI, install with `python -m pip install .`.
Installed commands are `radixscope` and `radixscope-gui`.

In the GUI, start with Conversion and enter `1/3`. Select **Show conversion steps**
for the detailed divisions and multiplications. In Number Inspector, enter `255`
with an 8-bit integer type, or select `binary16` and inspect `0.1`. The **Analysis**
selector opens format comparison, numeric comparison or floating-point arithmetic.

## Command line

```sh
python -m radixscope convert FF --from 16 --to 2 8 10 16
python -m radixscope expression "(0xFF & 0x0F) << 2"
python -m radixscope integer 256 --width 8 --requirements
python -m radixscope inspect FF --base 16 --width 8 --signed --pattern
python -m radixscope compare-numbers 255 127 --width 8 --json
python -m radixscope float-op add 0.1 0.2 --format binary16 --json
```

Use `--help` on any command. [CLI documentation](docs/cli.md) explains input syntax
and options; [numeric models and API](docs/specification.md) covers the Python API.

## Windows application

On Windows, use 64-bit Python 3.11 or newer available as `python` and run:

```powershell
.\build_windows.bat
```

The command installs build dependencies into the current Python environment and
creates `dist/RadixScope/RadixScope.exe`. Keep the whole generated folder, including
`_internal/` and `licenses/`. Python and Qt are included in that folder.

## Documentation

- [Installation and execution](docs/install.md)
- [Desktop usage](docs/usage.md)
- [Command line](docs/cli.md)
- [Numeric models and Python API](docs/specification.md)

For development verification, run `python scripts/check_numeric.py`; add `--desktop`
for Qt checks or `--exhaustive` to check all binary16 and bfloat16 encodings.
The Windows validation workflow invokes the same BAT and checks the resulting EXE.
