import base64
import re
from dataclasses import dataclass

from radixscope.core.ieee754 import IEEE754Value, IEEEFormat, decode_ieee754_bytes
from radixscope.core.representations import ByteOrder

MAX_BYTE_INPUT = 65_536


def parse_byte_input(text: str, input_format: str = "hex") -> bytes:
    if not isinstance(text, str):
        raise TypeError("byte input must be text")
    if len(text) > MAX_BYTE_INPUT * 8:
        raise ValueError("byte input exceeds the 64 KiB work limit")
    if input_format == "hex":
        chunks: list[bytes] = []
        for token in re.finditer(r"[^\s,:]+", text):
            digits = token.group()
            prefix = 2 if digits.lower().startswith("0x") else 0
            digits = digits[prefix:]
            if not digits or len(digits) % 2:
                raise ValueError(f"hex bytes require pairs of digits at position {token.start()}")
            invalid = re.search(r"[^0-9a-fA-F]", digits)
            if invalid is not None:
                position = token.start() + prefix + invalid.start()
                raise ValueError(f"invalid hex byte at position {position}")
            chunks.append(bytes.fromhex(digits))
        data = b"".join(chunks)
    elif input_format == "binary":
        bits = "".join(text.split())
        if bits.startswith("0b"):
            bits = bits[2:]
        if not bits or len(bits) % 8 or any(bit not in "01" for bit in bits):
            raise ValueError("binary bytes require complete groups of eight zero/one bits")
        data = int(bits, 2).to_bytes(len(bits) // 8, "big")
    elif input_format == "base64":
        data = base64.b64decode("".join(text.split()), validate=True)
    elif input_format == "utf8":
        data = text.encode("utf-8")
    else:
        raise ValueError("input format must be hex, binary, base64 or utf8")
    if not data:
        raise ValueError("byte input cannot be empty")
    if len(data) > MAX_BYTE_INPUT:
        raise ValueError("byte input exceeds the 64 KiB work limit")
    return data


@dataclass(frozen=True, slots=True)
class ByteInterpretation:
    data: bytes
    byteorder: ByteOrder = ByteOrder.BIG

    def __post_init__(self) -> None:
        if not isinstance(self.data, bytes) or not 1 <= len(self.data) <= MAX_BYTE_INPUT:
            raise ValueError("interpretation requires 1 through 65536 bytes")
        object.__setattr__(self, "byteorder", ByteOrder(self.byteorder))

    @property
    def unsigned(self) -> int:
        return int.from_bytes(self.data, self.byteorder.value, signed=False)

    @property
    def signed(self) -> int:
        return int.from_bytes(self.data, self.byteorder.value, signed=True)

    @property
    def ascii_preview(self) -> str:
        return "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in self.data)

    @property
    def utf8_preview(self) -> str:
        return self.data.decode("utf-8", errors="replace")

    @property
    def utf8_valid(self) -> bool:
        try:
            self.data.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return False
        return True

    @property
    def floating(self) -> tuple[IEEE754Value, ...]:
        formats = {2: (IEEEFormat.BINARY16, IEEEFormat.BFLOAT16),
                   4: (IEEEFormat.BINARY32,), 8: (IEEEFormat.BINARY64,)}
        return tuple(decode_ieee754_bytes(self.data, format_, self.byteorder)
                     for format_ in formats.get(len(self.data), ()))


def select_bytes(
    data: bytes, offset: int = 0, length: int | None = None, byteorder: str = "big",
) -> ByteInterpretation:
    if not isinstance(data, bytes) or not 1 <= len(data) <= MAX_BYTE_INPUT:
        raise ValueError("buffer requires 1 through 65536 bytes")
    if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset < len(data):
        raise ValueError("offset must address a byte inside the buffer")
    count = len(data) - offset if length is None else length
    if (isinstance(count, bool) or not isinstance(count, int)
            or not 1 <= count <= len(data) - offset):
        raise ValueError("selection length must fit inside the buffer")
    return ByteInterpretation(data[offset:offset + count], ByteOrder(byteorder))
