import re
from dataclasses import dataclass

from radixscope.core.errors import (
    InvalidBaseError,
    InvalidDigitError,
    InvalidExpressionError,
    InvalidNumberError,
)
from radixscope.core.expression import evaluate_expression
from radixscope.core.literals import parse_literal
from radixscope.core.parse import parse_number
from radixscope.core.tokenize import TokenKind, tokenize_expression
from radixscope.core.value import ExactValue


@dataclass(frozen=True, slots=True)
class InputSyntax:
    kind: str
    base: int | None
    description: str


def _bare_hex(text: str) -> bool:
    unsigned = text.lstrip("+-")
    return bool(re.fullmatch(r"[0-9a-fA-F]+", unsigned)) and (
        any(digit in unsigned.upper() for digit in "ABCDF") or unsigned[:1].upper() == "E"
    )


def detect_input_syntax(text: str) -> InputSyntax:
    normalized = text.strip()
    if not normalized:
        return InputSyntax("invalid", None, "Enter a number or expression")
    if len(normalized) > 2000:
        return InputSyntax("large", None, "Large input · choose Number, Expression or Auto")
    if _bare_hex(normalized):
        return InputSyntax("hex", 16, "Hexadecimal digits · Auto uses base 16")
    try:
        tokens = [
            token for token in tokenize_expression(normalized) if token.kind is not TokenKind.END
        ]
    except InvalidExpressionError as error:
        return InputSyntax("invalid", None, str(error))
    literals = [token for token in tokens if token.kind is TokenKind.LITERAL]
    if (
        len(literals) != 1
        or len(tokens) > 2
        or (len(tokens) == 2 and tokens[0].kind not in (TokenKind.PLUS, TokenKind.MINUS))
    ):
        return InputSyntax("expression", None, "Exact expression · Auto evaluates operators")
    literal = literals[0].text
    base = 10
    for prefix, candidate in (("0b", 2), ("0o", 8), ("0x", 16)):
        if literal.lower().startswith(prefix):
            base = candidate
            break
    if "#" in literal:
        digits = literal.split("#", 1)[0].lstrip("0") or "0"
        base = int(digits) if len(digits) <= 2 else 0
    kind = "scientific" if base == 10 and "e" in literal.lower() else "number"
    return InputSyntax(kind, base, f"{kind.capitalize()} input · detected base {base}")


def parse_numeric_input(text: str, base: int | None = None) -> ExactValue:
    if not isinstance(text, str):
        raise InvalidNumberError("number must be text")
    if base is not None:
        return parse_number(text, base)
    try:
        return parse_literal(text)
    except (InvalidNumberError, InvalidDigitError, InvalidBaseError):
        if _bare_hex(text.strip()):
            return parse_number(text, 16)
    return evaluate_expression(text)
