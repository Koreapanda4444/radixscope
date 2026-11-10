from __future__ import annotations

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
        node = self.parse_sum()
        remaining = self.tokens[self.position]
        if remaining.kind is not TokenKind.END:
            raise InvalidExpressionError(
                f"unexpected token {remaining.text!r} at position {remaining.position}"
            )
        return node

    def parse_sum(self) -> ExpressionNode:
        node = self.parse_product()
        while self.current.kind in {TokenKind.PLUS, TokenKind.MINUS}:
            operator = self.advance()
            node = BinaryExpression(operator.kind, node, self.parse_product(), operator.position)
        return node

    def parse_product(self) -> ExpressionNode:
        node = self.parse_unary()
        while self.current.kind in {TokenKind.MULTIPLY, TokenKind.DIVIDE}:
            operator = self.advance()
            node = BinaryExpression(operator.kind, node, self.parse_unary(), operator.position)
        return node

    def parse_unary(self) -> ExpressionNode:
        if self.current.kind in {TokenKind.PLUS, TokenKind.MINUS}:
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
            node = self.parse_sum()
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
    if node.operator is TokenKind.DIVIDE:
        if right.numerator == 0:
            raise InvalidExpressionError(f"division by zero at position {node.position}")
        return left / right
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
