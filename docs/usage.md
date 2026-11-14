# Desktop application

English | [한국어](ko/usage.md)

Start with `radixscope-gui`, `python -m radixscope.gui`, or the Windows desktop EXE.
The sidebar groups inspection, calculation and comparison tools. Workspace shortcuts
retain the following order:

| Shortcut | Workspace | Main task |
| --- | --- | --- |
| Ctrl+1 | Conversion | Exact conversion or expressions |
| Ctrl+2 | Trace | Division and remainder steps |
| Ctrl+3 | Integer operations / Programmer | Fixed-width integer operations |
| Ctrl+4 | IEEE 754 | Float precision and four-format comparison |
| Ctrl+5 | Number Inspector | Synchronized numeric, raw-bit and byte views |
| Ctrl+6 | Byte Inspector | Byte selections and bitfields |
| Ctrl+7 | Binary Comparison | XOR and field differences |
| Ctrl+8 | Batch Conversion | One value or expression per line |
| Ctrl+H | Recent panel | Search and restore history |

## Shared controls

Results open in a structured table with a field filter; Text report displays the
complete text. Select rows and use Copy selected (or Ctrl+C) to copy their underlying
values. Copy all copies the current text report. Long values remain accessible through
copy and export even when table previews are shortened.

Reuse / export reveals workspace transfer and text/JSON/CSV export. Numeric value
transfer uses the exact value where available. Raw bits transfer preserves the
pattern and width. The destination's data type determines its interpretation.
A transfer to Binary Comparison fills the left side and waits for a right side.
Float comparison and batch workspaces transfer the selected result row.

Each calculation runs in a separate process. Cancel terminates the process; changing
input also cancels it and clears the previous result. A result is accepted only if
its input snapshot still matches. Invalid input shows an error and invalidates copy,
export and reuse. Closing the window terminates active calculations.
Desktop worker responses are limited to 8 MiB.

The input/results divider is resizable. Optional tools stay hidden until selected;
tables and input panels scroll when needed. The minimum window size is 640 × 480.
Divider positions and optional panel visibility are restored separately from inputs.

## Conversion and Trace

Conversion supports Number (explicit base), Expression and Auto modes. The hint
suggests recognized syntax; switching to Auto explicitly adopts automatic parsing.
Exact conversion shows at most 1000 fractional digits, marking partial expansions
and affected bases. The rational source stays exact. Disable exact output to select
fractional digits and a rounding mode.

Trace shows integer divisions and fractional multiplications, including recurrence.
Set the maximum fractional steps. A partial trace has `complete=False`; this is
different from proving that the expansion terminates.

## Number Inspector and integer operations

Number Inspector combines base 2/8/10/16 output, signed and unsigned interpretations,
editable raw bits/Hex, fixed width and endian bytes. Choose integer or one of four
floating formats. The raw-pattern option reinterprets digits as a bit pattern;
otherwise input represents a mathematical value. Integer values must fit the selected
width. Signedness changes the interpretation of a fixed-width pattern.

Editing bits or Hex changes the input to the raw-pattern path and refreshes the
other representations. Changing byte order changes serialization. It does not
numerically swap the source value. Bit controls display at most 32 positions per page;
click a bit or focus it and press Space.

Integer operations retains the Programmer workspace for arithmetic, shifts and bitwise
operations. Arithmetic separates the exact result, overflow flag and wrapped value.
Editing result bits selects Inspect so the previous arithmetic operation is not repeated.
The GUI supports integer widths 1–4096; Core also applies its documented work budget.

## IEEE 754

Encode accepts exact expressions, NaN and infinity. Decode interprets raw digits in
the chosen base. Select binary16, bfloat16, binary32 or binary64. Results separate
sign, exponent and fraction; preserve signed zero, quiet/signaling NaNs and payloads;
and expose exact rational values, errors and ULP spacing when defined.

Signed-zero options apply to zero encoding. NaN controls apply to NaN encoding;
a signaling NaN needs a nonzero payload. Disabled encoding controls are ignored
during raw decoding. Editing bits switches to Decode and keeps all pattern bits.

Previous/next controls navigate representable neighbors. Boundary controls jump to
zero, the smallest subnormal, minimum normal, maximum finite and infinity patterns.
Compare formats creates a table for the same source across all four formats,
including effective significand bits and intermediate-rounding differences.
Select a comparison row before copying or transferring it.

## Bytes and bitfields

Byte Inspector accepts Hex, Binary, Base64 and UTF-8. Use Offset/Length or table
selection to choose bytes. Whole-buffer mode interprets from offset through the end.
The byte table shows offset, Hex and ASCII, paged in groups of 256 bytes.
Select an interpretation and endian order; float selection length must match its format.
Copy selected bytes or convert the buffer to another input format without changing bytes.

Show bitfield editor exposes name, LSB-based offset, width and signedness.
Apply fields checks duplicate names, overlap and range, then shows values and
colored regions. Edit bits to update the actual byte buffer. Save/load layout uses JSON;
layout width must match the selection. Interactive editing is limited to 512 selected
bytes; Core byte interpretation supports up to 64 KiB.

## Binary comparison and batch

Binary Comparison accepts two buffers in the same selected input format.
Lengths must match unless Zero extend is explicitly chosen. Results include XOR,
changed bit/byte counts, paged byte differences and optional layout field differences.
Show bit differences enables colored bit views for patterns up to 4096 bits.
Larger inputs retain byte/text views and complete counts; position lists indicate truncation.

Batch Conversion skips empty lines but retains original line numbers. Choose Number,
Expression or Auto, target bases, precision and a row limit. Default output uses
16 fractional digits; Exact output requests expansions within work limits.
An invalid row does not discard successful rows. Check the summary for errors
and unprocessed inputs. Exports preserve per-row values and errors.

## Language, themes and history

Settings → Preferences selects English/Korean and System/Light/Dark themes.
The initial language follows the system locale. Switching language preserves inputs,
options, active calculations, result data and history. JSON/CSV keys remain canonical;
UI language does not change exported numeric values.

Recent history is hidden until Ctrl+H. Search by input, result or work type, or filter
by category. Restore a saved result directly when cached; larger records restore
inputs/options and require Run. Repeating the same input/options moves the entry
to the front. Clear history removes entries. Disabling history prevents new entries
but still saves the current workspace state.

History defaults to 20 entries and supports 1–100. Individual cached reports are
limited to 256 KiB. Settings keep their compatible schema, use atomic replacement
and have a 32 MiB file limit. Read/write failures display a status message;
a failed save preserves the previous file. The CLI does not modify GUI settings.
