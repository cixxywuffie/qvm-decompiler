"""Parser and instruction decoder for Quake III VM files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct

QVM_MAGIC_V1 = 0x12721444
QVM_MAGIC_V2 = 0x12721445


class QvmFormatError(ValueError):
    """Raised when a QVM header or code segment is malformed."""


@dataclass(frozen=True)
class Header:
    magic: int
    instruction_count: int
    code_offset: int
    code_length: int
    data_offset: int
    data_length: int
    lit_length: int
    bss_length: int
    jump_table_length: int | None = None

    @property
    def version(self) -> int:
        return 1 if self.magic == QVM_MAGIC_V1 else 2


@dataclass(frozen=True)
class Instruction:
    address: int
    opcode: int
    name: str
    operand: int | None = None


# The bytecode opcode values are part of the QVM format.
OPCODE_NAMES = (
    "undef", "ignore", "break", "enter", "leave", "call", "push", "pop",
    "const", "local", "jump", "eq", "ne", "lti", "lei", "gti", "gei",
    "ltu", "leu", "gtu", "geu", "eqf", "nef", "ltf", "lef", "gtf",
    "gef", "load1", "load2", "load4", "store1", "store2", "store4",
    "arg", "block_copy", "sex8", "sex16", "negi", "add", "sub", "divi",
    "divu", "modi", "modu", "muli", "mulu", "band", "bor", "bxor",
    "bcom", "lsh", "rshi", "rshu", "negf", "addf", "subf", "divf",
    "mulf", "cvif", "cvfi",
)

_FOUR_BYTE_OPERAND_OPCODES = frozenset(
    (3, 4, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 34)
)
_ONE_BYTE_OPERAND_OPCODES = frozenset((33,))


def _checked_range(offset: int, length: int, file_size: int, label: str) -> None:
    if offset < 0 or length < 0 or offset > file_size or length > file_size - offset:
        raise QvmFormatError(f"{label} range is outside the file")


def read_qvm(path: str | Path) -> QvmFile:
    """Read and validate the header and instruction stream of a QVM file."""
    file_path = Path(path)
    return QvmFile.from_bytes(file_path.read_bytes(), str(file_path))


@dataclass(frozen=True)
class QvmFile:
    header: Header
    instructions: tuple[Instruction, ...]
    source: str = "<memory>"
    trailing_code_bytes: int = 0

    @classmethod
    def from_bytes(cls, data: bytes, source: str = "<memory>") -> QvmFile:
        if len(data) < 8 * 4:
            raise QvmFormatError("file is too small to contain a QVM header")

        values = struct.unpack_from("<8I", data)
        magic = values[0]
        if magic not in (QVM_MAGIC_V1, QVM_MAGIC_V2):
            raise QvmFormatError(f"unrecognized QVM magic 0x{magic:08x}")

        jump_table_length = None
        header_size = 8 * 4
        if magic == QVM_MAGIC_V2:
            if len(data) < 9 * 4:
                raise QvmFormatError("truncated QVM v2 header")
            jump_table_length = struct.unpack_from("<I", data, 8 * 4)[0]
            header_size += 4

        header = Header(*values, jump_table_length=jump_table_length)
        if header.instruction_count == 0 and header.code_length != 0:
            raise QvmFormatError("code segment is non-empty but instruction count is zero")
        if header.code_offset < header_size:
            raise QvmFormatError("code segment overlaps the QVM header")
        _checked_range(header.code_offset, header.code_length, len(data), "code segment")
        _checked_range(header.data_offset, header.data_length, len(data), "data segment")
        _checked_range(
            header.data_offset + header.data_length,
            header.lit_length,
            len(data),
            "literal segment",
        )

        code = data[header.code_offset:header.code_offset + header.code_length]
        instructions, trailing_code_bytes = _decode_instructions(code, header.instruction_count)
        return cls(
            header=header,
            instructions=instructions,
            source=source,
            trailing_code_bytes=trailing_code_bytes,
        )


def _decode_instructions(code: bytes, expected_count: int) -> tuple[tuple[Instruction, ...], int]:
    result: list[Instruction] = []
    offset = 0

    while len(result) < expected_count:
        if offset >= len(code):
            raise QvmFormatError(
                f"instruction count mismatch: header says {expected_count}, decoded {len(result)}"
            )
        address = offset
        opcode = code[offset]
        offset += 1
        if opcode >= len(OPCODE_NAMES):
            raise QvmFormatError(f"unknown opcode {opcode} at code address 0x{address:x}")

        operand = None
        if opcode in _FOUR_BYTE_OPERAND_OPCODES:
            if len(code) - offset < 4:
                raise QvmFormatError(f"truncated operand at code address 0x{address:x}")
            operand = struct.unpack_from("<i", code, offset)[0]
            offset += 4
        elif opcode in _ONE_BYTE_OPERAND_OPCODES:
            if offset >= len(code):
                raise QvmFormatError(f"truncated operand at code address 0x{address:x}")
            operand = code[offset]
            offset += 1

        result.append(Instruction(address, opcode, OPCODE_NAMES[opcode], operand))

    return tuple(result), len(code) - offset
