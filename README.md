# QVM Decompiler

A small Python project for inspecting Quake III VM (`.qvm`) files. The first
prototype validates QVM v1/v2 headers, decodes bytecode, and offers an
experimental expression-level pseudocode view.

This cannot recover the original C source. The pseudocode is intentionally
approximate: control flow, types, function names, and data structures may need
manual analysis.

## Run

Requires Python 3.10 or later; there are no third-party dependencies.

From a terminal, install the project in editable mode once:

```powershell
py -m pip install -e .
qvm-decompiler C:\path\to\cgame.qvm
qvm-decompiler C:\path\to\qagame.qvm --mode pseudocode --output qagame.pseudo.c
```

In PyCharm, open this folder, mark `src` as a Sources Root, and create a run
configuration for `qvm_decompiler` (module name `qvm_decompiler`) with the QVM
path and options as program arguments.

## Current limitations

- The disassembler supports the standard 60 QVM opcodes.
- Pseudocode translates only local stack expressions and straightforward
  operations. Branches are emitted as `goto` statements; it does not reconstruct
  structured `if`/`switch` blocks.
- Function names and source types are not present in the QVM and are not
  recovered.

## Development

Run the unit tests with:

```powershell
py -m unittest discover -s tests -v
```

The reusable QVM analysis skill is in `.github\skills\qvm-analysis\SKILL.md`.
It describes how to inspect a mod's PK3 with this decompiler and report
evidence and limitations.
