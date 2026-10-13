#!/usr/bin/env python3
"""Validate the explicit LCD fixture and stage readmemh-only simulation data.

No Quartus project, BDF, or synthesizable HDL is modified. Files called *.mif
under sim/build are deliberately simulation shadows containing readmemh hex;
the genuine Intel MIF source files remain in lcd/.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re

LCD_DIR = Path(__file__).resolve().parent.parent
CONTROL = bytes([0, 0, 0, 0, 0, 0x30, 0x30, 0x30, 0x38,
                 0x08, 0x01, 0x06, 0x0C, 0, 0, 0x80])
NAMES = ("ADD", "SUB", "MUL", "DIV", "MOD", "AND", "OR", "XOR", "JMP")
OPERATIONS = b"".join(name.ljust(16).encode("ascii")
                       for name in (*NAMES, *("" for _ in range(7))))


def parse_mif(path: Path, depth: int) -> bytes:
    text = re.sub(r"--[^\n]*", "", path.read_text(encoding="ascii"))
    text = re.sub(r"%.*?%", "", text, flags=re.S)
    header, separator, body = text.partition("CONTENT BEGIN")
    if not separator:
        raise ValueError(f"{path}: missing CONTENT BEGIN")
    assignments = dict(re.findall(r"([A-Z_]+)\s*=\s*([A-Z0-9]+)\s*;", header))
    expected = {"WIDTH": "8", "DEPTH": str(depth),
                "ADDRESS_RADIX": "HEX", "DATA_RADIX": "HEX"}
    if assignments != expected:
        raise ValueError(f"{path}: header {assignments!r}, expected {expected!r}")
    body = re.sub(r"END\s*;\s*$", "", body)
    values: dict[int, int] = {}
    for statement in body.split(";"):
        if not statement.strip():
            continue
        match = re.fullmatch(r"\s*([0-9A-Fa-f]+)\s*:\s*([0-9A-Fa-f]+)\s*", statement)
        if not match:
            raise ValueError(f"{path}: unsupported or malformed entry {statement!r}")
        address, value = (int(item, 16) for item in match.groups())
        if not 0 <= address < depth or not 0 <= value <= 255 or address in values:
            raise ValueError(f"{path}: duplicate/out-of-range address or value")
        values[address] = value
    if set(values) != set(range(depth)):
        raise ValueError(f"{path}: exactly {depth} explicit addresses are required")
    return bytes(values[address] for address in range(depth))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, help="stage simulator data in this directory")
    args = parser.parse_args()
    if args.stage and args.stage.resolve() == LCD_DIR.resolve():
        raise SystemExit("Refusing to overwrite genuine MIF files with simulation shadows.")
    images = {"control.mif": CONTROL, "operations.mif": OPERATIONS}
    for filename, expected in images.items():
        actual = parse_mif(LCD_DIR / filename, len(expected))
        if actual != expected:
            mismatch = next(i for i, (a, b) in enumerate(zip(actual, expected)) if a != b)
            raise SystemExit(f"FAIL {filename}: address {mismatch:02X}: "
                             f"{actual[mismatch]:02X}, expected {expected[mismatch]:02X}")
        print(f"PASS {filename}: {len(actual)} addresses, WIDTH=8, HEX, exact fixture")
        if args.stage:
            args.stage.mkdir(parents=True, exist_ok=True)
            # lpm_rom's readmemh loader resolves its relative lpm_file in vvp's cwd.
            # Also provide .hex for exports explicitly configured with that suffix.
            image = "".join(f"{byte:02X}\n" for byte in actual)
            for suffix in (".mif", ".hex"):
                destination = args.stage / Path(filename).with_suffix(suffix).name
                if destination.resolve() in {(LCD_DIR / item).resolve() for item in images}:
                    raise SystemExit("Refusing a simulation shadow that resolves to a source MIF.")
                destination.write_text(image, encoding="ascii")
    print("Map is a test fixture only; the real CPU opcode map remains unconfirmed.")


if __name__ == "__main__":
    main()
