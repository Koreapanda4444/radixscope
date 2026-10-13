# RadixScope v2 specification

English | [한국어](ko/specification.md)

## Core rules

- Supported bases are 2 through 36.
- Input digits are case-insensitive. Formatted output uses uppercase letters.
- Core arithmetic is exact and does not use binary floating-point values.
- Leading and trailing whitespace is ignored. Internal whitespace is invalid.
- Every digit must be valid for the selected base.
- Zero is always normalized to a positive sign.

## Digit alphabet

Digit values use the following alphabet:

```text
0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ
```

`A` represents 10 and `Z` represents 35.

## Input forms

`parse_number` takes the base separately. `parse_literal` reads the base from the numeric text.

```text
sign      = "+" | "-"
integer   = sign? digit+
finite    = sign? digit+ "." digit+
ratio     = integer "/" integer
recurring = sign? digit+ "." digit* "(" digit+ ")"
number    = ratio | recurring | finite | integer
```

Examples:

| Input | Base | Exact value |
| --- | ---: | ---: |
| `-101` | 2 | `-5` |
| `A.F` | 16 | `175/16` |
| `1/3` | 10 | `1/3` |
| `A/10` | 16 | `5/8` |
| `0.(3)` | 10 | `1/3` |
| `0.1(6)` | 10 | `1/6` |
| `0.(01)` | 2 | `1/3` |

Both sides of a ratio use the selected base. A zero denominator is invalid.

## Exact value model

Every accepted number is normalized to a rational value:

- numerator and denominator are reduced by their greatest common divisor;
- the denominator is always positive;
- integer values use denominator `1`;
- equivalent inputs produce the same exact value.

## Conversion behavior

- Integer conversion uses the complete exact value.
- Fractional conversion tracks remainders so recurring sections can be detected.
- A terminating result contains no recurring section.
- A recurring result uses parentheses, such as `0.(3)`.
- Precision limits and rounding affect only formatted output, never the stored exact value.
- Converting a complete recurring representation back to a value must reproduce the original rational value.

## Mixed-base literals

Unprefixed literals use base 10. Prefixes `0b`, `0o` and `0x` select bases 2, 8 and 16;
prefixes and digits are case-insensitive. `base#digits` selects any base from 2 through 36,
with the base label always written in decimal. Finite and recurring fractions use the same
syntax as `parse_number`: `0xA.F`, `2#0.(01)` and `0.1(6)` are exact values.
An integer part is required; `.5` and `0x.F` are not accepted. Scientific notation is unsupported.

`parse_literal` accepts an optional leading sign and outer whitespace for a single literal.
In expressions, signs are unary operators. The slash is always division between two literals,
each with its own base: `0xA / 10` is `1`, while `0xA / 16#10` is `5/8`.
For a standalone same-base ratio, use `parse_number("A/10", 16)` instead.

```python
from radixscope.core import ExactValue, evaluate_expression, parse_literal

assert parse_literal("0xA.F") == ExactValue(175, 16)
assert evaluate_expression("0xFF + 0b10") == ExactValue(257)
assert evaluate_expression("16#FF + 2#10") == ExactValue(257)
assert evaluate_expression("(0x10 + 2) ** -2") == ExactValue(1, 324)
```

## Expression tokenization

`tokenize_expression` separates numeric literals, operators and grouping parentheses.
Each immutable token carries its kind, original text and zero-based half-open source span.
An end token marks the end of the input. Whitespace between tokens is ignored;
whitespace within a literal is not allowed. Literal digits and base labels use ASCII.
Signs are separate tokens, and recurring parentheses belong to their numeric literal.
The `**` operator is emitted as one power token rather than two multiplication tokens.

## Expression parsing and evaluation

`parse_expression` returns an immutable tree of literal, unary and binary nodes.
`evaluate_parsed_expression` evaluates that tree, and `evaluate_expression` combines both.
All literals and intermediate results remain exact rational values.

```text
expression = product (("+" | "-") product)*
product    = unary (("*" | "/") unary)*
unary      = ("+" | "-") unary | power
power      = primary ("**" unary)?
primary    = literal | "(" expression ")"
```

Addition, subtraction, multiplication and division associate left to right.
Power associates right to left: `10#2**10#3**10#2` is `512`.
Power binds tighter than a leading sign: `-10#2**10#2` is `-4`.
Exponents must evaluate to integers; negative exponents produce exact reciprocals.
Zero to a negative power and division by zero are invalid. Zero to the zeroth power is `1`.
Errors identify the operator or token position; excessive nesting raises a domain error.
Variable names, assignments, function calls and implicit multiplication are not supported.

Desktop conversion displays at most 1000 fractional digits in exact mode and labels partial
expansions with an ellipsis and the affected bases. The trace workspace has an adjustable
step limit. `trace_value(..., max_steps=...)` preserves the original rational value and sets
`complete=False` when that limit is reached before termination or recurrence is established.
The core's default remains unlimited; partial traces never claim to terminate.

## Fixed-width integer model

`FixedWidthInteger(value, width, signed=False)` stores an immutable integer with an explicit
positive bit width. Unsigned bounds are `0` through `2**width - 1`; signed bounds are
`-2**(width - 1)` through `2**(width - 1) - 1`. Construction checks this range.
Widths need not be multiples of eight. Boolean and non-integer values are rejected.

`from_exact` and `from_text` connect the model to the rational core and numeric parser.
Fractional values are rejected instead of truncated. The `exact` property returns the
mathematical value as an `ExactValue`. `resize` preserves that value and signedness,
checking the destination range instead of wrapping or discarding bits.

## Signed and unsigned interpretation

`bit_pattern` and `bits` encode a fixed-width value without a leading minus sign.
`reinterpret(signed=...)` preserves the width and every bit, changing only its interpretation.
`interpret_bit_pattern` reports the unsigned value, signed two's-complement value,
sign bit, padded binary text and uppercase hexadecimal text for the same pattern.

`from_bits` uses the raw binary text length when no width is supplied. A larger explicit
width zero-extends the pattern before signed interpretation; extra textual bits are rejected.
Thus `11111111` is signed `-1` at eight bits, but signed `255` at sixteen bits.
`parse_bit_pattern` reads integer digits in a specified base and then interprets the pattern.
`from_text` instead reads a mathematical value, so signed `-1` and pattern `FF` are
different input paths. Neither path silently wraps out-of-range input.

## Range and overflow analysis

`analyze_range` preserves the mathematical integer and reports its destination bounds.
`overflowed` indicates whether it fits. `checked` raises `IntegerRangeError` on overflow,
while `wrapped` explicitly reduces the result modulo `2**width` and decodes its signedness.
The exact result is never overwritten by the wrapped result.

`analyze_arithmetic` analyzes addition, subtraction and multiplication of two fixed-width
operands with identical width and signedness. Signed and unsigned overflow are detected
against their respective mathematical ranges. For example, signed eight-bit `127 + 1`
has exact result `128`, overflows, and wraps to `-128`; unsigned `255 + 1` wraps to `0`.
Operands with different formats must be explicitly resized or reinterpreted first.

## Fixed-width bitwise operations

Fixed-width values support `&`, `|`, `^`, `~`, `<<` and `>>`. Binary bitwise operands
must have the same width and signedness. Results preserve that format; NOT and left
shift mask their result to the selected width. Operands remain immutable.

For signed values, `>>` is an arithmetic shift that repeats the sign bit. For unsigned
values it fills with zero. `logical_right_shift` always fills with zero, preserving the
result's declared format. Shift counts must be nonnegative integers, excluding booleans.
Counts at least the width discard all shifted bits: left and logical right shifts give
zero, while arithmetic right shift gives `-1` for a negative signed value.
These operations apply to `FixedWidthInteger` values; the rational expression grammar
continues to support only its documented arithmetic operators.

## Endian byte and ASCII representations

`encode_bytes` serializes the fixed-width bit pattern in big or little endian order,
using exactly `ceil(width / 8)` bytes, including leading zero bytes. Byte order changes
the sequence of bytes, not the bits inside each byte. Signed negatives retain their
two's-complement pattern.

Unused high bits in the most-significant partial byte are zero-padded. For example, signed five-bit
`-1` encodes as `1F`, not `FF`. `decode_bytes` defaults to `len(data) * 8` bits;
pass the original width to round-trip non-byte-aligned values. Explicit width must
match the byte count, and nonzero unused high bits are rejected instead of discarded.
Empty data cannot represent a fixed-width integer.

`represent_bytes` returns the ordered bytes, spaced uppercase hexadecimal text and
an ASCII preview. The preview displays printable bytes `20` through `7E` and uses a
dot for every other byte without altering the underlying data. `encode_ascii` and
`decode_ascii` are strict, lossless seven-bit ASCII codecs, including control characters;
they reject non-ASCII text or bytes rather than substituting characters.

## IEEE 754 decoding

`decode_ieee754(pattern, width=64)` interprets an unsigned raw binary32 or binary64
pattern without changing any bits. `IEEEFormat` describes the 23/52 fraction bits,
8/11 exponent bits and 127/1023 exponent bias. Other formats are rejected.
`decode_ieee754_bytes` requires exactly four or eight bytes with explicit byte order.

The immutable `IEEE754Value` exposes sign, exponent and fraction fields, padded binary
and hexadecimal text, and classification as zero, subnormal, normal, infinity or NaN.
Finite `exact` values are rational, including the smallest subnormal. `significand`
includes the implicit leading one only for normal values; `exponent` is unbiased.
For zero and subnormal values it is the format's minimum normal exponent.
Infinity and NaN have no rational value, significand or unbiased exponent.

Signed zero retains its sign in the raw pattern even though its rational value is zero.
NaN retains its sign, quiet bit and payload; `nan_payload` excludes the quiet bit.
`to_bytes` preserves all raw bits and supports either endian order. `to_float` is a
host-float convenience; use the raw pattern to preserve signaling NaNs and payloads.

Format definitions follow the [Oracle numerical computation guide](https://docs.oracle.com/cd/E19422-01/819-3693/ncg_math.html).

## IEEE 754 encoding

`encode_ieee754(value, width=64)` accepts `ExactValue`, integer or host float and returns
an `IEEE754Value`. Rational and integer inputs round directly into the destination format
without first converting to a host float. Host floats contribute their actual binary value;
use `ExactValue` and the numeric parser for exact decimal input.

Rounding is round to nearest, ties to even. It covers significand carries, gradual underflow,
the subnormal-to-normal transition and overflow to signed infinity. Values smaller than
half the minimum subnormal round to signed zero. At the halfway value, zero is the even
choice. The halfway overflow threshold rounds to infinity.

Host `-0.0` retains its sign. Rational zero has no sign, so `negative_zero=True` explicitly
creates negative zero and is rejected for nonzero inputs. Host infinities retain their sign;
host NaNs become canonical quiet NaNs with their sign preserved.

`encode_ieee754_special` explicitly constructs zero, infinity or NaN with a zero-or-one
`sign_bit`. NaN's `payload` excludes its leading quiet bit, and `quiet=False` constructs
a signaling NaN only when the payload is nonzero. Payloads must fit the chosen format;
they are rejected instead of truncated. Non-NaN special values cannot carry a payload.
Raw decoding and byte serialization remain the lossless path for existing NaN patterns.

## Errors

The core rejects:

- bases outside 2 through 36;
- empty input or a sign without digits;
- digits that do not exist in the selected base;
- multiple decimal points, fraction separators, or recurring groups;
- empty recurring groups;
- zero denominators;
- malformed literal prefixes, invalid base labels and unsupported numeric syntax.
