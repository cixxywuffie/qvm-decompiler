"""Text renderers for decoded QVM instructions."""

from __future__ import annotations

from .qvm import QvmFile

_BRANCH_OPCODES = frozenset(range(11, 27))
_BRANCH_OPERATORS = {
    11: "==", 12: "!=", 13: "<", 14: "<=", 15: ">", 16: ">=",
    17: "<", 18: "<=", 19: ">", 20: ">=",
    21: "==", 22: "!=", 23: "<", 24: "<=", 25: ">", 26: ">=",
}
_BINARY_OPERATORS = {
    "add": "+", "sub": "-", "divi": "/", "divu": "/",
    "modi": "%", "modu": "%", "muli": "*", "mulu": "*",
    "band": "&", "bor": "|", "bxor": "^", "lsh": "<<",
    "rshi": ">>", "rshu": ">>", "addf": "+", "subf": "-",
    "divf": "/", "mulf": "*",
}


def _hex(value: int) -> str:
    return f"0x{value & 0xFFFFFFFF:x}"


def disassemble(qvm: QvmFile) -> str:
    header = qvm.header
    lines = [
        f"; source: {qvm.source}",
        f"; QVM version: {header.version}",
        f"; instructions: {header.instruction_count}",
        f"; code: offset={_hex(header.code_offset)} length={_hex(header.code_length)}",
        f"; data: offset={_hex(header.data_offset)} length={_hex(header.data_length)}",
        f"; literals: length={_hex(header.lit_length)}",
        f"; bss: length={_hex(header.bss_length)}",
        "",
    ]
    if qvm.trailing_code_bytes:
        lines[7] = f"; trailing code bytes not covered by instruction count: {qvm.trailing_code_bytes}"
    for instruction in qvm.instructions:
        operand = "" if instruction.operand is None else f" {_hex(instruction.operand)}"
        lines.append(f"{instruction.address:08x}  {instruction.name:<10}{operand}")
    return "\n".join(lines) + "\n"


def pseudocode(qvm: QvmFile) -> str:
    """Render a deliberately partial, stack-based C-like view."""
    lines = [
        "/* Experimental QVM pseudocode; control flow and types are approximate. */",
        "",
    ]
    stack: list[str] = []
    function_index = -1
    function_open = False

    def pop() -> str:
        return stack.pop() if stack else "unknown_value"

    def emit(line: str) -> None:
        lines.append(f"    {line}")

    for instruction in qvm.instructions:
        op = instruction.name
        value = instruction.operand
        if op == "enter":
            if function_open:
                lines.append("}")
                lines.append("")
            function_index += 1
            function_open = True
            stack.clear()
            name = "vmMain" if function_index == 0 else f"qvm_func_{instruction.address:04x}"
            lines.append(f"/* bytecode address 0x{instruction.address:x} */")
            lines.append(f"void {name}(void) {{")
            emit(f"/* frame size: {_hex(value or 0)} */")
        elif not function_open:
            lines.append(f"/* bytecode before first function at 0x{instruction.address:x} */")
            function_open = True
            lines.append(f"void qvm_func_{instruction.address:04x}(void) {{")

        if op == "enter":
            continue
        if op == "leave":
            emit("return;")
            lines.append("}")
            lines.append("")
            function_open = False
            stack.clear()
        elif op == "const":
            stack.append(str(value))
        elif op == "local":
            stack.append(f"&local_{_hex(value or 0)}")
        elif op in ("load1", "load2", "load4"):
            value_type = {"load1": "uint8_t", "load2": "uint16_t", "load4": "int32_t"}[op]
            stack.append(f"*(({value_type}*)({pop()}))")
        elif op in ("store1", "store2", "store4"):
            stored = pop()
            target = pop()
            value_type = {"store1": "uint8_t", "store2": "uint16_t", "store4": "int32_t"}[op]
            emit(f"*(({value_type}*)({target})) = {stored};")
        elif op == "arg":
            emit(f"arg[{_hex(value or 0)}] = {pop()};")
        elif op in _BINARY_OPERATORS:
            right, left = pop(), pop()
            stack.append(f"({left} {_BINARY_OPERATORS[op]} {right})")
        elif op in ("negi", "negf", "bcom", "sex8", "sex16", "cvif", "cvfi"):
            operand = pop()
            prefix = {"negi": "-", "negf": "-", "bcom": "~"}.get(op)
            stack.append(f"({prefix}{operand})" if prefix else f"{op}({operand})")
        elif instruction.opcode in _BRANCH_OPCODES:
            right, left = pop(), pop()
            emit(
                f"if ({left} {_BRANCH_OPERATORS[instruction.opcode]} {right}) "
                f"goto loc_{_hex(value or 0)};"
            )
        elif op == "jump":
            emit(f"goto qvm_target({pop()});")
        elif op == "call":
            target = pop()
            emit(f"/* call target: {target}; arguments/calling convention unresolved */")
            stack.append("call_result")
        elif op == "push":
            stack.append("0")
        elif op == "pop":
            pop()
        elif op in ("ignore", "break"):
            emit(f"/* {op} */")
        else:
            stack.clear()
            emit(f"/* {instruction.address:08x}: {op} (expression tracking reset) */")

    if function_open:
        lines.append("}")
    return "\n".join(lines).rstrip() + "\n"


def render(qvm: QvmFile, mode: str) -> str:
    if mode == "disasm":
        return disassemble(qvm)
    if mode == "pseudocode":
        return pseudocode(qvm)
    raise ValueError(f"unsupported output mode: {mode}")
