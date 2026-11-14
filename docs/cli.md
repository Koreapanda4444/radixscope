# Command line

English | [한국어](ko/cli.md)

Install with `python -m pip install .`, then use `radixscope` or
`python -m radixscope`. Every command supports `--help` and `--json`.

## Numbers and expressions

```sh
radixscope convert FF --from 16 --to 2 8 10 16
radixscope convert "0.(3)" --to 2 10 --precision 8 --rounding half-even
radixscope convert "1.25e-3" --auto --to 10 16
radixscope expression "(0xFF & 0x0F) << 2" --to 2 10 16
radixscope expression "(7/3) // (2/3) + (-7 % 3)"
radixscope trace "1/7" --from 10 --to 2 --max-steps 12 --json
```

Conversion defaults to source base 10 and output bases 2, 8, 10 and 16.
Without `--precision`, complete expansions use parentheses for repeating digits.
Work limits still apply; use precision or a limited trace for long periods.
Rounding modes are `truncate`, `half-up`, `half-even`, `floor` and `ceiling`.

`--auto` overrides `--from` and recognizes prefixed literals, scientific notation,
expressions and unambiguous bare Hex digits. Use an explicit base when intent could
be ambiguous. In base 16, `1E3` remains hexadecimal; in decimal it is scientific notation.
Incomplete decimal exponents such as `1e` are errors. `trace` reports `complete=false`
when its selected step limit is reached; this does not imply a terminating expansion.

Expression precedence follows Python for `| ^ & << >> + - * / // % +x -x ~x **`.
Bitwise operators require integers; floor division and remainder also accept exact
fractions. There are no variables, calls or implicit multiplication.

## Integers and unified inspection

```sh
radixscope inspect FF --base 16 --width 8 --signed --pattern
radixscope inspect "0.1" --type binary16 --byteorder little
radixscope inspect 3F80 --base 16 --type bfloat16 --pattern
radixscope integer 127 --width 8 --signed --op add --operand 1 --json
radixscope integer -128 --width 8 --signed --op shr --operand 1
radixscope integer FF --base 16 --width 8 --signed --pattern
```

Input is a mathematical value unless `--pattern` requests raw reinterpretation.
Mathematical integer input must fit its range. Arithmetic reports the exact result,
overflow and explicitly wrapped result separately. Bitwise operands share base, width
and signedness; shift counts are decimal. `shr` is arithmetic for signed values,
while `lshr` always fills with zero. Byte order affects byte sequences, not numeric value.

## Floating-point analysis

```sh
radixscope ieee encode "1/10" --format bfloat16 --json
radixscope ieee decode 3C00 --format binary16
radixscope ieee encode nan --format binary32 --payload 123 --signaling
radixscope ieee encode 0 --negative-zero --width 32
radixscope ieee compare "1/10" --json
```

`--format` selects binary16, bfloat16, binary32 or binary64 and overrides the legacy
`--width` option (16, 32 or 64). Encode accepts exact expressions, `nan`, `inf`
and `infinity` with a sign. Decode reads raw digits in base 16 by default;
`--base` changes that base. Raw decoding preserves signed zero and NaN payloads.

Reports include exact representation, rational absolute/relative error and ULP error
when defined, adjacent values and boundaries. Compare encodes the same exact source
directly in all four formats and indicates differences caused by intermediate rounding.
NaN payload/signaling options apply only to single-format NaN encoding.

## Required widths and numeric comparison

```sh
radixscope integer 256 --width 8 --requirements --json
radixscope integer FF --base 16 --width 8 --extract 4 4
radixscope compare-numbers 255 127 --width 8 --json
radixscope compare-numbers "1/3" "2/3"
radixscope compare-numbers "0xFF" "0b11111111" --expressions --width 8
radixscope compare-numbers "0.1" "0.1000000001" --type binary16
```

`--requirements` analyzes the mathematical integer even when it cannot fit the selected
width. It reports minimum signed/unsigned widths, selected bounds and standard-width
fits; it is used without operations or raw-pattern input. `--extract OFFSET WIDTH`
extracts a checked result range from LSB 0 and applies the selected signedness.

`compare-numbers` uses shared base/type/width/signedness options. Mathematical ordering
and differences use exact input values; float patterns are rounded separately. Fractions
or out-of-range integers can still be compared without a bit pattern. For compatible
patterns, reports include XOR, signed/unsigned interpretations and differing positions.
NaN gives `unordered`; finite differences are undefined for infinite operands.
Position lists are capped at 4096, with `positions_complete` distinguishing partial lists.

## Floating-point arithmetic experiments

```sh
radixscope float-op add 0.1 0.2 --format binary16 --json
radixscope float-op subtract "1 + 1/1000" 1 --format bfloat16
radixscope float-op divide 1 0 --format binary32
radixscope float-op add 7C01 3C00 --patterns --format binary16
```

`float-op` accepts add, subtract, multiply and divide. Numeric operands are exact
expressions; `--patterns` decodes both operands in the selected format and raw base
(default 16). All four formats use nearest, ties to even.

`rounded_operands` first encodes both inputs and then rounds their operation result.
`exact_then_round` calculates from the original values and rounds once. Reports retain
original exact inputs, encoded operands, input-conversion flags, operation flags,
operation-rounding errors and errors against the original mathematics. Overflow,
underflow, invalid operation, divide-by-zero and inexact are distinct flags.
Special values and NaN propagation follow the documented [numeric rules](specification.md#floating-point-arithmetic).

## Batch conversion and exports

```sh
radixscope batch --file numbers.txt --mode auto --to 2 10 16 --csv
radixscope batch --file numbers.txt --mode expression --exact --json
radixscope batch - --mode number --from 16 --limit 100 --csv
```

The file is UTF-8 (a BOM is accepted). Omit `--file` and use `-` to read stdin,
or pass a multiline value directly. Nonempty lines retain original line numbers.
Modes are number, expression and auto. Default output has 16 fractional digits;
`--exact` requests complete expansions within work limits.

Each invalid line has an error and does not discard other rows. Global invalid options
or oversized input are command errors. Inspect `errors`, `limited` and per-row errors
even when the batch command succeeds. At most 1000 rows and 2 MiB of formatted
batch content are processed.

JSON preserves existing report keys. Ordinary numeric fields remain JSON numbers;
integers exceeding Python's active decimal-string conversion threshold are emitted as
exact decimal strings. Exact rational values remain strings. GUI text/JSON/CSV exports
use the same source report data, independently of UI language.

## Exit codes and negative arguments

Successful commands return 0. Invalid arguments or numbers return 2 and write an error
to stderr; Ctrl+C returns 130 during computation. For negative values resembling
options, put command options first and the value after `--`:

```sh
radixscope ieee encode --width 32 -- -inf
radixscope integer --base 16 --width 8 --signed -- -7F
```
