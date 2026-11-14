# Desktop application

English | [한국어](ko/usage.md)

Start with `radixscope-gui`, `python -m radixscope.gui`, or the Windows EXE.
The top tabs and shortcuts select four workspaces:

| Shortcut | Workspace | Main task |
| --- | --- | --- |
| Ctrl+1 | Conversion | Radix conversion and optional conversion steps |
| Ctrl+2 | Calculation | Exact expressions and fixed-width operations |
| Ctrl+3 | Number Inspector | Numeric representations and specialized analysis |
| Ctrl+4 | Batch Conversion | Line-by-line conversion |
| Ctrl+H | Recent | Search, restore and export history |

## Results and execution

Results groups related fields into Group, Item and Value columns; Text report retains
the complete report. Select rows
and use Copy selected, Ctrl+C or double-click to copy underlying values. Copy all copies
the text report. Long table previews are shortened without truncating copied/exported data.
Detailed fields reveals additional float boundaries and internal fields; the filter
can also find hidden detail fields and their original data paths.

Reuse / export reveals value/raw-pattern transfer and text/JSON/CSV export.
Numeric transfer uses the exact finite value. Raw transfer preserves the pattern and
width. Select a row in format comparison or batch results before transferring it;
numeric comparison has a Number to reuse selector.

Run starts a worker process. Cancel stops it; input changes cancel pending work and clear
old results. Responses are accepted only for the matching input snapshot. Invalid input
disables result copying and reuse. Closing the app terminates its workers. Responses
are limited to 8 MiB.

The input area fits visible controls automatically. Resize the input/results divider as
needed; manual sizes are preserved and adjusted on window resize. An intentionally
compressed form scrolls. Double-click the divider to restore the adaptive default.
The minimum window is 640 × 480; smaller
layouts scroll their input controls while keeping Run and results accessible. Divider,
detail-panel and bit-group preferences are saved separately from numeric input.

## Conversion

Number uses the explicit source base. Auto recognizes supported input syntax; the hint
and Use automatic input button make that choice explicit. Fractions and recurring
groups preserve their exact rational value. Exact output displays up to 1000 fractional
digits and marks incomplete expansions. Rounded output selects fractional digits and
one of five rounding modes.

Enable **Compare rounding** to compare Truncate, Half-up, Half-even, Floor and
Ceiling in the **Rounding comparison** result tab. Select **Base** and fractional
**Digits** above the comparison table; these are target-base digits, shared with the
normal rounded-output precision. The comparison always uses the
original exact input, including when the normal output is rounded. For `2.5`, base 10
and 0 digits, the five results are `2`, `3`, `2`, `2`, `3`. Copy comparison copies all
five rows, or select rows to copy just those. The comparison is optional and does not
change ordinary conversion, CLI or batch behavior.

Choose a preset for common bases or a decimal/binary/Hex pair. Manual base edits select
Custom. Quick swap chooses one target and exchanges it with the source. The input is
rewritten from the exact value, using a fraction if needed; a rounded preview is never
treated as the new source value.

Show conversion steps enables a detailed tab. Choose its base and fractional step limit.
It lists integer divisions and fractional multiplications, highlighting recurring digits.
A step-limited partial trace is explicitly marked and does not imply termination.

## Calculation

Exact expression uses mixed-base literals and rational arithmetic. Select target bases
and display rounding independently. Bitwise operators require integers; `//` and `%`
also accept fractions. Expressions support Python-style operator precedence.

Fixed-width integer exposes width, signedness, numeric/raw input, operation and operand.
Arithmetic separates the mathematical result from overflow and the wrapped result.
Enable **Compare 8/16/32/64-bit results** to see each width's value, overflow,
and representation. Each width is independent, so a failure at the selected width still
leaves the other widths available. For unsigned `300 + 1` with 8 bits selected, the 8-bit
row reports a range error while 16/32/64 bits return `301`. Invalid numeric syntax or
an unsupported operation fails the whole request. Mathematical-result and overflow
columns apply to arithmetic operations; width comparisons use the full, unextracted result.
Signed `shr` extends the sign; `lshr` inserts zero bits. Shift counts are decimal.
Extract bit range selects an LSB-based offset and width from the result; extracted
bits use the selected signedness. Editing result bits selects Inspect.

Integer reports show minimum signed/unsigned widths, standard 8/16/32/64-bit fits and
selected bounds. Negative integers have no unsigned width. GUI integer widths are 1–4096.

## Number Inspector

Select Number or Expression input, a data type, width, signedness and byte order.
Numeric input converts a mathematical value; Raw bits reinterprets the entered pattern.
An integer outside the selected range still shows its exact value and required widths,
with a range error and no fabricated bit pattern. The byte row supports direct copying.

Edit bits and explore neighbors reveals the Hex editor and bit controls. Groups of four
bits correspond to Hex digits; groups of eight correspond to numeric bytes. Positions
count from LSB 0, and sign/exponent/fraction regions have distinct styling. A page contains
at most 32 interactive bits. Editing a bit or Hex pattern updates the other representations.
Byte order changes serialization without changing the mathematical value.

The Analysis selector exposes specialized tools:

- **Number representation:** integer interpretation or floating encoding/decoding, exact
  error, relative error and ULP. Float types are binary16, bfloat16, binary32 and binary64.
  Special value options exposes negative zero and quiet/signaling NaN payload controls.
  Raw decoding preserves every input bit. Neighbor and boundary controls operate on the
  displayed float pattern.
- **Format comparison:** a table of the same exact input encoded directly in all four
  formats, with error, effective precision and intermediate-rounding differences.
- **Numeric comparison:** two inputs under shared base/type/width options. Reports exact
  mathematical ordering, difference, absolute difference and radix outputs. Representable
  patterns additionally show XOR, differing positions and signed/unsigned differences.
  Expand bit controls for highlighted differences. Fractions can be compared mathematically
  even when an integer representation is unavailable. NaN ordering is undefined.
- **Floating-point arithmetic:** enter two exact expressions or two raw patterns, select
  a format and add/subtract/multiply/divide. Reports preserve each encoded operand and
  distinguish rounding operands first from rounding the exact original calculation once.
  Input-conversion flags, operation flags and errors against the original calculation are
  separate. **IEEE rounding** selects nearest-even (default), toward zero, toward
  positive infinity or toward negative infinity. Tiny inexact results can set underflow;
  nonfinite results have no finite rational error.

## Batch, preferences and history

Batch accepts Number, Expression or Auto input, one value per nonempty line. Original line
numbers and individual errors are retained. Choose targets, rounding, exact output and a
row limit. The summary identifies errors, limits and unprocessed input. Exports preserve
per-row data; one invalid row does not discard successful rows.

Settings → Preferences selects English/Korean and System/Light/Dark themes. Language
changes preserve input and result data. Export keys and numeric strings remain canonical.

Recent is initially hidden. Search by input/result/work type and filter by category.
Restore cached results directly; larger reports restore inputs and options for recalculation.
History defaults to 20 entries and allows 1–100. Each cached report is limited to 256 KiB.
Disabling history stops new records while preserving current workspace settings.

Settings retain schema 1 and a 32 MiB limit. Supported historical tasks migrate to the new
workspaces; retired buffer/layout tasks are omitted. Atomic writes preserve the last valid
file after save failures. The CLI does not modify desktop settings.
