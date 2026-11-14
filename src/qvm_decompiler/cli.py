"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys

from .formatter import render
from .qvm import QvmFormatError, read_qvm


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qvm-decompiler",
        description="Inspect a Quake III VM bytecode file and emit approximate pseudocode.",
    )
    parser.add_argument("qvm", help="path to a .qvm file")
    parser.add_argument(
        "--mode",
        choices=("disasm", "pseudocode"),
        default="disasm",
        help="output format (default: disasm)",
    )
    parser.add_argument("-o", "--output", help="write output to a file instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = render(read_qvm(args.qvm), args.mode)
        if args.output:
            with open(args.output, "w", encoding="utf-8", newline="\n") as output_file:
                output_file.write(result)
        else:
            sys.stdout.write(result)
    except (OSError, QvmFormatError, ValueError) as error:
        print(f"qvm-decompiler: error: {error}", file=sys.stderr)
        return 2
    return 0
