"""Work limits for expansion and computation, independent of integer range checks."""

from radixscope.core.errors import RadixScopeError

MAX_INPUT_CHARS = 100_000
MAX_COMPUTED_BITS = 2_000_000
MAX_EXPANSION_DIGITS = 100_000
MAX_TRACE_STEPS = 10_000
MAX_REMAINDER_BITS = 64 * 1024 * 1024 * 8


class ComputationLimitError(RadixScopeError):
    pass


def check_input(text: str) -> None:
    if len(text) > MAX_INPUT_CHARS:
        raise ComputationLimitError(f"input exceeds {MAX_INPUT_CHARS} characters")


def check_expansion(count: int, denominator: int) -> None:
    if count >= MAX_EXPANSION_DIGITS or count * max(64, denominator.bit_length()) > (
        MAX_REMAINDER_BITS
    ):
        raise ComputationLimitError(
            "exact expansion exceeds the work limit; use rounded output or a limited trace"
        )
