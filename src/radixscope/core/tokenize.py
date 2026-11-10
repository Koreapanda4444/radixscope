from dataclasses import dataclass
from enum import StrEnum

from radixscope.core.errors import InvalidExpressionError
from radixscope.core.limits import check_input

_DIGITS = "0123456789"
_NUMERAL_DIGITS = _DIGITS + "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


class TokenKind(StrEnum):
    LITERAL = "literal"
    PLUS = "+"
    MINUS = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    POWER = "**"
    LEFT_PAREN = "("
    RIGHT_PAREN = ")"
    END = "end"


@dataclass(frozen=True, slots=True)
class ExpressionToken:
    kind: TokenKind
    text: str
    position: int
    end: int


def _read_literal(expression: str, start: int) -> tuple[ExpressionToken, int]:
    position = start
    while position < len(expression) and expression[position] in _DIGITS:
        position += 1
    if position < len(expression) and expression[position] == "#":
        position += 1
    elif expression[start : start + 2].lower() in {"0b", "0o", "0x"}:
        position = start + 2
    else:
        position = start
    numeral_start = position
    while position < len(expression) and expression[position] in _NUMERAL_DIGITS:
        position += 1
    if position == numeral_start:
        raise InvalidExpressionError(f"literal at position {start} has no digits")
    if position < len(expression) and expression[position] == ".":
        position += 1
        fractional_start = position
        while position < len(expression) and expression[position] in _NUMERAL_DIGITS:
            position += 1
        if position < len(expression) and expression[position] == "(":
            position += 1
            recurring_start = position
            while position < len(expression) and expression[position] in _NUMERAL_DIGITS:
                position += 1
            if (
                position == recurring_start
                or position >= len(expression)
                or expression[position] != ")"
            ):
                raise InvalidExpressionError(
                    f"invalid recurring group in literal at position {start}"
                )
            position += 1
        elif position == fractional_start:
            raise InvalidExpressionError(f"missing fractional digits at position {position}")
    return ExpressionToken(TokenKind.LITERAL, expression[start:position], start, position), position


def tokenize_expression(expression: str) -> tuple[ExpressionToken, ...]:
    if not isinstance(expression, str):
        raise InvalidExpressionError("expression must be text")
    check_input(expression)
    tokens: list[ExpressionToken] = []
    position = 0
    while position < len(expression):
        character = expression[position]
        if character.isspace():
            position += 1
        elif character in _DIGITS:
            token, position = _read_literal(expression, position)
            tokens.append(token)
        elif expression.startswith("**", position):
            tokens.append(ExpressionToken(TokenKind.POWER, "**", position, position + 2))
            position += 2
        elif character in "+-*/()":
            tokens.append(ExpressionToken(TokenKind(character), character, position, position + 1))
            position += 1
        else:
            raise InvalidExpressionError(
                f"unexpected character {character!r} at position {position}"
            )
    tokens.append(ExpressionToken(TokenKind.END, "", len(expression), len(expression)))
    return tuple(tokens)
