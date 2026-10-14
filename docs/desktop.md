# Desktop application

English | [한국어](ko/desktop.md)

Start with `radixscope-gui` or `python -m radixscope.gui`. Use Ctrl+1 through Ctrl+4
to switch workspaces. Enter in the main input field runs the calculation. Results can be
selected or copied with **Copy result**. Invalid input clears the previous result
and displays the error above the output.
The input area scrolls vertically and horizontally when the window is too small for its controls.

## Running and cancelling calculations

Each workspace runs its calculation in a separate process. The window remains responsive
while the status reads Calculating. Cancel terminates that process and clears pending output.
Changing an input or option also cancels its active calculation and invalidates the old result.
Only successful, current results enter recent history. Closing the application terminates active
calculations. Desktop result transfer is limited to 8 MiB; reduce input or trace steps if reached.
The command line retains its synchronous behavior.

## Conversion

Choose Number for digits in a selected source base, or Expression for exact mixed-base
arithmetic. List target bases separated by commas. Exact output uses parentheses around
recurring digits; long expansions end with an ellipsis and list the bases that reached
the 1000-digit display limit. The rational value remains exact.

Turn off exact output to choose fractional digits and a rounding mode. This produces
a fixed-precision result in each target base.

## Trace

The output lists integer division and fractional multiplication steps, the resulting
digits and the start of a repeating cycle. Set the maximum fractional steps to bound
the display. `complete: False` means the limit was reached before the expansion ended
or its cycle was established; it does not mean the number terminates.

## Programmer

Select a base, bit width, signedness and whether the input is a mathematical integer
or a raw bit pattern. The GUI supports widths 1 through 4096; the Python model accepts
any positive width. Pattern input is unsigned digits before interpretation, so `FF`
at eight signed bits means -1. Mathematical input must fit the selected range.

Operations include add, subtract, multiply, AND, OR, XOR, NOT and shifts. Shift operands
are decimal counts. `shr` is arithmetic for signed values, while `lshr` always fills
with zero. Arithmetic results show both the exact result and overflow flag alongside
the explicitly wrapped value. The byte preview preserves width and selected endian order.

Result bits are editable by clicking a button or focusing it and pressing Space.
Positions run from most significant to least significant, with at most 32 bits per page.
Editing a result changes the input to its raw pattern in the current base and selects Inspect,
so the previous arithmetic operation is not applied again. The numeric and byte report updates
immediately. Changing other input controls invalidates the editor; Run loads the new result.

## IEEE 754

Encode accepts exact expressions, NaN and infinity. Decode interprets raw digits in
the selected pattern base. Choose binary32 or binary64. Results include the exact
rational value when finite, classification, separated bit fields, hex and endian bytes.

Signed-zero controls apply to encoding zero. NaN controls become available for `nan`
or `-nan`; unchecking Quiet NaN requires a nonzero payload. Disabled encoding controls
are ignored during raw decoding. Changing modes keeps the input text for editing.

The bit editor labels and colors sign, exponent and fraction fields. Binary64 uses two pages.
Editing switches to Decode and replaces the input with the edited raw pattern in the selected
base. Classification, exact value, hex, endian bytes and NaN metadata update together.
Raw edits preserve every bit, including signed zero and signaling NaN payloads.

## Preferences and recent history

Settings → Preferences selects System, Light or Dark theme and enables or disables
recent history with a limit of 1 through 100 entries. The default limit is 20.
Current input and workspace options, active tab and window size are restored on startup.

The Recent panel stores input, options, timestamp and a short result summary, excluding
full trace output. Identical inputs and options move to the front instead of duplicating.
Double-click an entry or use Restore selected input; Run computes the restored input.
Clear history removes saved recent entries. Turning history off stops new entries;
current workspace options and input are still saved independently.

Preferences are saved on successful calculations, explicit preference changes and window
close. Writes replace the settings file atomically. Unreadable or malformed settings use
defaults and display a status message. A write failure keeps the previous file and does
not prevent calculations. The CLI does not read or modify desktop preferences.
Reading and saving share a 32 MiB settings-file limit, enough for 100 entries containing long inputs.
An oversized save reports an error and preserves the previous settings file.
