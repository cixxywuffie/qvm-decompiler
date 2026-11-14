import struct
import unittest

from qvm_decompiler.formatter import disassemble, pseudocode
from qvm_decompiler.qvm import QVM_MAGIC_V1, QVM_MAGIC_V2, QvmFile, QvmFormatError


def make_qvm(code: bytes, instruction_count: int, magic: int = QVM_MAGIC_V1) -> bytes:
    header_size = 36 if magic == QVM_MAGIC_V2 else 32
    header = struct.pack(
        "<8I",
        magic,
        instruction_count,
        header_size,
        len(code),
        header_size + len(code),
        0,
        0,
        0,
    )
    if magic == QVM_MAGIC_V2:
        header += struct.pack("<I", 0)
    return header + code


class QvmParserTests(unittest.TestCase):
    def test_decodes_operands_and_opcodes(self) -> None:
        code = b"\x03" + struct.pack("<i", 16) + b"\x08" + struct.pack("<i", 7) + b"\x04" + struct.pack("<i", 16)
        qvm = QvmFile.from_bytes(make_qvm(code, 3))

        self.assertEqual(qvm.header.version, 1)
        self.assertEqual(
            [(item.address, item.name, item.operand) for item in qvm.instructions],
            [(0, "enter", 16), (5, "const", 7), (10, "leave", 16)],
        )

    def test_reads_version_two_header(self) -> None:
        qvm = QvmFile.from_bytes(make_qvm(b"\x01", 1, QVM_MAGIC_V2))

        self.assertEqual(qvm.header.version, 2)
        self.assertEqual(qvm.header.jump_table_length, 0)

    def test_decodes_block_copy_operand(self) -> None:
        code = b"\x22" + struct.pack("<i", 12)
        qvm = QvmFile.from_bytes(make_qvm(code, 1))

        self.assertEqual(qvm.instructions[0].name, "block_copy")
        self.assertEqual(qvm.instructions[0].operand, 12)

    def test_decodes_last_conditional_branch_operand(self) -> None:
        code = b"\x1a" + struct.pack("<i", 0x1234)
        qvm = QvmFile.from_bytes(make_qvm(code, 1))

        self.assertEqual(qvm.instructions[0].name, "gef")
        self.assertEqual(qvm.instructions[0].operand, 0x1234)

    def test_rejects_bad_magic(self) -> None:
        with self.assertRaisesRegex(QvmFormatError, "unrecognized QVM magic"):
            QvmFile.from_bytes(b"\0" * 32)

    def test_rejects_unknown_opcode(self) -> None:
        with self.assertRaisesRegex(QvmFormatError, "unknown opcode"):
            QvmFile.from_bytes(make_qvm(b"\xff", 1))

    def test_rejects_truncated_operand(self) -> None:
        with self.assertRaisesRegex(QvmFormatError, "truncated operand"):
            QvmFile.from_bytes(make_qvm(b"\x08\x01", 1))

    def test_rejects_instruction_count_mismatch(self) -> None:
        with self.assertRaisesRegex(QvmFormatError, "instruction count mismatch"):
            QvmFile.from_bytes(make_qvm(b"\x01", 2))

    def test_records_bytes_after_instruction_count(self) -> None:
        qvm = QvmFile.from_bytes(make_qvm(b"\x01\xff\xfe", 1))

        self.assertEqual(len(qvm.instructions), 1)
        self.assertEqual(qvm.trailing_code_bytes, 2)

    def test_outputs_disassembly_and_experimental_pseudocode(self) -> None:
        code = b"\x03" + struct.pack("<i", 8) + b"\x08" + struct.pack("<i", 7) + b"\x04" + struct.pack("<i", 8)
        qvm = QvmFile.from_bytes(make_qvm(code, 3))

        self.assertIn("00000000  enter", disassemble(qvm))
        pseudo = pseudocode(qvm)
        self.assertIn("void vmMain(void)", pseudo)
        self.assertIn("return;", pseudo)

    def test_pseudocode_handles_dynamic_jump_target(self) -> None:
        code = b"\x03" + struct.pack("<i", 8) + b"\x08" + struct.pack("<i", 12) + b"\x0a\x04" + struct.pack("<i", 8)
        qvm = QvmFile.from_bytes(make_qvm(code, 4))

        self.assertIn("goto qvm_target(12);", pseudocode(qvm))


if __name__ == "__main__":
    unittest.main()
