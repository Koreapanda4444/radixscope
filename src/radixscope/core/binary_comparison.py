from dataclasses import dataclass

from radixscope.core.bitfields import BitField, inspect_bitfields, validate_fields
from radixscope.core.byte_inspection import ByteInterpretation
from radixscope.core.representations import ByteOrder


@dataclass(frozen=True, slots=True)
class BinaryDifference:
    left: bytes
    right: bytes
    byteorder: ByteOrder = ByteOrder.BIG
    length_policy: str = "equal"
    fields: tuple[BitField, ...] = ()

    def __post_init__(self) -> None:
        ByteInterpretation(self.left)
        ByteInterpretation(self.right)
        object.__setattr__(self, "byteorder", ByteOrder(self.byteorder))
        if self.length_policy not in ("equal", "zero-extend"):
            raise ValueError("length policy must be equal or zero-extend")
        if self.length_policy == "equal" and len(self.left) != len(self.right):
            raise ValueError("patterns have different lengths; choose explicit zero extension")
        validate_fields(self.fields, self.width)

    @property
    def width(self) -> int:
        return max(len(self.left), len(self.right)) * 8

    @property
    def aligned(self) -> tuple[bytes, bytes]:
        size = self.width // 8
        if self.byteorder is ByteOrder.BIG:
            return self.left.rjust(size, b"\0"), self.right.rjust(size, b"\0")
        return self.left.ljust(size, b"\0"), self.right.ljust(size, b"\0")

    @property
    def xor(self) -> bytes:
        left, right = self.aligned
        return bytes(a ^ b for a, b in zip(left, right, strict=True))

    @property
    def changed_byte_offsets(self) -> tuple[int, ...]:
        return tuple(offset for offset, byte in enumerate(self.xor) if byte)

    @property
    def changed_bits(self) -> int:
        return sum(byte.bit_count() for byte in self.xor)

    @property
    def changed_bit_positions(self) -> tuple[int, ...]:
        positions: list[int] = []
        for offset, byte in enumerate(self.xor):
            byte_index = self.width // 8 - 1 - offset if self.byteorder is ByteOrder.BIG else offset
            positions.extend(byte_index * 8 + bit for bit in range(8) if byte & (1 << bit))
        return tuple(sorted(positions))

    @property
    def field_differences(self) -> tuple[dict[str, object], ...]:
        left = inspect_bitfields(
            int.from_bytes(self.left, self.byteorder.value), self.width, self.fields
        )
        right = inspect_bitfields(
            int.from_bytes(self.right, self.byteorder.value), self.width, self.fields
        )
        return tuple(
            {
                "name": a.field.name,
                "offset": a.field.offset,
                "width": a.field.width,
                "signed": a.field.signed,
                "left": str(a.integer.exact),
                "right": str(b.integer.exact),
                "xor_bits": format(
                    a.integer.bit_pattern ^ b.integer.bit_pattern, f"0{a.field.width}b"
                ),
                "changed": a.integer.bit_pattern != b.integer.bit_pattern,
            }
            for a, b in zip(left, right, strict=True)
        )


def compare_binary(
    left: bytes,
    right: bytes,
    *,
    byteorder: str = "big",
    length_policy: str = "equal",
    fields: tuple[BitField, ...] = (),
) -> BinaryDifference:
    return BinaryDifference(left, right, ByteOrder(byteorder), length_policy, fields)
