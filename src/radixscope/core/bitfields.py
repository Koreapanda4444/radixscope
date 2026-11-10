import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from radixscope.core.fixed_width import FixedWidthInteger, validate_width


@dataclass(frozen=True, slots=True)
class BitField:
    name: str
    offset: int
    width: int
    signed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 80:
            raise ValueError("field names require 1 through 80 characters")
        if isinstance(self.offset, bool) or not isinstance(self.offset, int) or self.offset < 0:
            raise ValueError("field offset must be a nonnegative integer (LSB is bit zero)")
        validate_width(self.width)
        if not isinstance(self.signed, bool):
            raise ValueError("field signedness must be boolean")


def validate_fields(fields: Sequence[BitField], width: int) -> None:
    validate_width(width)
    if len(fields) > 256:
        raise ValueError("a layout supports at most 256 fields")
    if any(not isinstance(field, BitField) for field in fields):
        raise TypeError("layout entries must be BitField values")
    names: set[str] = set()
    end = 0
    for field in sorted(fields, key=lambda item: item.offset):
        if field.name in names:
            raise ValueError(f"duplicate field name: {field.name}")
        names.add(field.name)
        if field.offset < end:
            raise ValueError(f"field overlaps another field: {field.name}")
        end = field.offset + field.width
        if end > width:
            raise ValueError(f"field exceeds the {width}-bit selection: {field.name}")


@dataclass(frozen=True, slots=True)
class BitFieldValue:
    field: BitField
    integer: FixedWidthInteger


def inspect_bitfields(
    pattern: int, width: int, fields: Sequence[BitField]
) -> tuple[BitFieldValue, ...]:
    validate_fields(fields, width)
    FixedWidthInteger.from_bit_pattern(pattern, width)
    return tuple(
        BitFieldValue(
            field,
            FixedWidthInteger.from_bit_pattern(
                (pattern >> field.offset) & ((1 << field.width) - 1),
                field.width,
                field.signed,
            ),
        )
        for field in fields
    )


@dataclass(frozen=True, slots=True)
class BitfieldLayout:
    width: int
    fields: tuple[BitField, ...]

    def __post_init__(self) -> None:
        validate_fields(self.fields, self.width)

    def to_json(self) -> str:
        return json.dumps(
            {
                "schema": 1,
                "bit_numbering": "lsb0",
                "width": self.width,
                "fields": [asdict(field) for field in self.fields],
            },
            indent=2,
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, text: str) -> "BitfieldLayout":
        if not isinstance(text, str) or len(text) > 1024 * 1024:
            raise ValueError("layout must be text no larger than 1 MiB")
        data = json.loads(text)
        if (
            not isinstance(data, dict)
            or type(data.get("schema")) is not int
            or data.get("schema") != 1
            or data.get("bit_numbering") != "lsb0"
        ):
            raise ValueError("unsupported bitfield layout")
        entries = data.get("fields")
        if not isinstance(entries, list) or len(entries) > 256:
            raise ValueError("layout fields must be a list of at most 256 entries")
        fields: list[BitField] = []
        for entry in entries:
            if not isinstance(entry, dict) or not {"name", "offset", "width"} <= entry.keys():
                raise ValueError("invalid bitfield entry")
            if entry.keys() - {"name", "offset", "width", "signed"}:
                raise ValueError("unknown bitfield property")
            fields.append(
                BitField(entry["name"], entry["offset"], entry["width"], entry.get("signed", False))
            )
        return cls(validate_width(data.get("width")), tuple(fields))
