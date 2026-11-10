from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeAlias

from radixscope.core.errors import InvalidExpressionError, RadixScopeError
from radixscope.core.limits import MAX_COMPUTED_BITS, ComputationLimitError
from radixscope.core.literals import parse_literal
from radixscope.core.tokenize import ExpressionToken, TokenKind, tokenize_expression
from radixscope.core.value import ExactValue


@dataclass(frozen=True, slots=True)
class LiteralExpression:
    value: ExactValue
    text: str
    position: int
    end: int


@dataclass(frozen=True, slots=True)
class UnaryExpression:
    operator: TokenKind
    operand: ExpressionNode
    position: int


@dataclass(frozen=True, slots=True)
class BinaryExpression:
    operator: TokenKind
    left: ExpressionNode
    right: ExpressionNode
    position: int


ExpressionNode: TypeAlias = LiteralExpression | UnaryExpression | BinaryExpression


class _ExpressionParser:
    def __init__(self, expression: str) -> None:
        self.tokens = tokenize_expression(expression)
        self.position = 0

    @property
    def current(self) -> ExpressionToken:
        return self.tokens[self.position]

    def advance(self) -> ExpressionToken:
        token = self.current
        self.position += 1
        return token

    def parse(self) -> ExpressionNode:
        if self.current.kind is TokenKind.END:
            raise InvalidExpressionError("expression cannot be empty")
        node = self.parse_or()
        remaining = self.tokens[self.position]
        if remaining.kind is not TokenKind.END:
            raise InvalidExpressionError(
                f"unexpected token {remaining.text!r} at position {remaining.position}"
            )
        return node

    def parse_left(
        self, operand: Callable[[], ExpressionNode], operators: set[TokenKind],
    ) -> ExpressionNode:
        node = operand()
        while self.current.kind in operators:
            operator = self.advance()
            node = BinaryExpression(operator.kind, node, operand(), operator.position)
        return node

    def parse_or(self) -> ExpressionNode:
        return self.parse_left(self.parse_xor, {TokenKind.BIT_OR})

    def parse_xor(self) -> ExpressionNode:
        return self.parse_left(self.parse_and, {TokenKind.BIT_XOR})

    def parse_and(self) -> ExpressionNode:
        return self.parse_left(self.parse_shift, {TokenKind.BIT_AND})

    def parse_shift(self) -> ExpressionNode:
        return self.parse_left(self.parse_sum, {TokenKind.LEFT_SHIFT, TokenKind.RIGHT_SHIFT})

    def parse_sum(self) -> ExpressionNode:
        node = self.parse_product()
        while self.current.kind in {TokenKind.PLUS, TokenKind.MINUS}:
            operator = self.advance()
            node = BinaryExpression(operator.kind, node, self.parse_product(), operator.position)
        return node

    def parse_product(self) -> ExpressionNode:
        node = self.parse_unary()
        while self.current.kind in {
            TokenKind.MULTIPLY, TokenKind.DIVIDE, TokenKind.FLOOR_DIVIDE, TokenKind.MODULO,
        }:
            operator = self.advance()
            node = BinaryExpression(operator.kind, node, self.parse_unary(), operator.position)
        return node

    def parse_unary(self) -> ExpressionNode:
        if self.current.kind in {TokenKind.PLUS, TokenKind.MINUS, TokenKind.INVERT}:
            operator = self.advance()
            return UnaryExpression(operator.kind, self.parse_unary(), operator.position)
        return self.parse_power()

    def parse_power(self) -> ExpressionNode:
        node = self.parse_primary()
        if self.current.kind is TokenKind.POWER:
            operator = self.advance()
            return BinaryExpression(operator.kind, node, self.parse_unary(), operator.position)
        return node

    def parse_primary(self) -> ExpressionNode:
        token = self.current
        if token.kind is TokenKind.LITERAL:
            self.advance()
            try:
                value = parse_literal(token.text)
            except RadixScopeError as error:
                raise InvalidExpressionError(
                    f"invalid literal {token.text!r} at position {token.position}: {error}"
                ) from error
            return LiteralExpression(value, token.text, token.position, token.end)
        if token.kind is TokenKind.LEFT_PAREN:
            self.advance()
            node = self.parse_or()
            if self.current.kind is not TokenKind.RIGHT_PAREN:
                raise InvalidExpressionError(
                    f"missing closing parenthesis at position {token.position}"
                )
            self.advance()
            return node
        raise InvalidExpressionError(
            f"expected a literal or parenthesis at position {token.position}"
        )


def parse_expression(expression: str) -> ExpressionNode:
    try:
        return _ExpressionParser(expression).parse()
    except RecursionError as error:
        raise InvalidExpressionError("expression nesting is too deep") from error


def _evaluate_node(node: ExpressionNode) -> ExactValue:
    if isinstance(node, LiteralExpression):
        return node.value
    if isinstance(node, UnaryExpression):
        value = _evaluate_node(node.operand)
        if node.operator is TokenKind.PLUS:
            return value
        if node.operator is TokenKind.MINUS:
            return -value
        if node.operator is TokenKind.INVERT:
            if not value.is_integer:
                raise InvalidExpressionError(
                    f"bitwise operators require integers at position {node.position}"
                )
            return ExactValue(~value.numerator)
        raise InvalidExpressionError(f"unsupported unary operator: {node.operator}")
    if not isinstance(node, BinaryExpression):
        raise TypeError("node must be an ExpressionNode")
    left = _evaluate_node(node.left)
    right = _evaluate_node(node.right)
    if node.operator is not TokenKind.POWER:
        sizes = [abs(value.numerator).bit_length() + value.denominator.bit_length()
                 for value in (left, right)]
        if sum(sizes) > MAX_COMPUTED_BITS:
            raise ComputationLimitError(
                f"operation exceeds the computation budget at position {node.position}"
            )
    if node.operator is TokenKind.PLUS:
        return left + right
    if node.operator is TokenKind.MINUS:
        return left - right
    if node.operator is TokenKind.MULTIPLY:
        return left * right
    if node.operator in (TokenKind.DIVIDE, TokenKind.FLOOR_DIVIDE, TokenKind.MODULO):
        if right.numerator == 0:
            raise InvalidExpressionError(f"division by zero at position {node.position}")
        if node.operator is TokenKind.DIVIDE:
            return left / right
        if node.operator is TokenKind.FLOOR_DIVIDE:
            return ExactValue(left.fraction // right.fraction)
        return ExactValue.from_fraction(left.fraction % right.fraction)
    if node.operator in {
        TokenKind.BIT_AND, TokenKind.BIT_OR, TokenKind.BIT_XOR,
        TokenKind.LEFT_SHIFT, TokenKind.RIGHT_SHIFT,
    }:
        if not left.is_integer or not right.is_integer:
            raise InvalidExpressionError(
                f"bitwise operators and shifts require integers at position {node.position}"
            )
        a, b = left.numerator, right.numerator
        if node.operator is TokenKind.BIT_AND:
            return ExactValue(a & b)
        if node.operator is TokenKind.BIT_OR:
            return ExactValue(a | b)
        if node.operator is TokenKind.BIT_XOR:
            return ExactValue(a ^ b)
        if b < 0:
            raise InvalidExpressionError(
                f"shift count cannot be negative at position {node.position}"
            )
        if node.operator is TokenKind.RIGHT_SHIFT:
            return ExactValue((-1 if a < 0 else 0) if b > abs(a).bit_length() else a >> b)
        if a == 0:
            return ExactValue(0)
        if abs(a).bit_length() + b > MAX_COMPUTED_BITS:
            raise ComputationLimitError(
                f"shift exceeds the computation budget at position {node.position}"
            )
        return ExactValue(a << b)
    if node.operator is TokenKind.POWER:
        if not right.is_integer:
            raise InvalidExpressionError(f"exponent must be an integer at position {node.position}")
        if left.numerator == 0 and right.numerator < 0:
            raise InvalidExpressionError(
                f"zero cannot have a negative exponent at position {node.position}"
            )
        exponent = right.numerator
        if left.numerator == 0:
            return ExactValue(int(exponent == 0))
        if left.denominator == 1 and abs(left.numerator) == 1:
            return ExactValue(-1 if left.numerator < 0 and exponent % 2 else 1)
        size = max(abs(left.numerator).bit_length(), left.denominator.bit_length())
        if size * abs(exponent) > MAX_COMPUTED_BITS:
            raise ComputationLimitError(
                f"power exceeds the computation budget at position {node.position}"
            )
        return left ** exponent
    raise InvalidExpressionError(f"unsupported binary operator: {node.operator}")


def evaluate_parsed_expression(node: ExpressionNode) -> ExactValue:
    try:
        return _evaluate_node(node)
    except RecursionError as error:
        raise InvalidExpressionError("expression nesting is too deep") from error


def evaluate_expression(expression: str) -> ExactValue:
    return evaluate_parsed_expression(parse_expression(expression))
