#!/usr/bin/env python3
"""Independently recheck completed checker CSV/VCD; never infer PASS from a partial run."""
from pathlib import Path
import argparse
import csv
import hashlib
import json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, nargs="?", default=Path(__file__).parent / "build")
    args = parser.parse_args()
    root = args.directory
    log = (root / "simulation.log").read_text()
    assert "PASS: actual DUT checked; 16 opcodes, 18 complete prints, 2 complete init sequences," in log, \
        "No complete checker PASS; do not summarize an unfinished or failed run as success"
    rows = list(csv.DictReader((root / "lcd_trace.csv").open()))
    assert len(rows) == 328, f"Expected 328 completed transfers, got {len(rows)}"
    init = {}
    prints = []
    for row in rows:
        row["time_ns"] = int(row["time_ns"])
        row["index"] = int(row["index"])
        row["rs"] = int(row["rs"])
        row["data_hex"] = int(row["data_hex"], 16)
        if row["kind"] == "init":
            init.setdefault(int(row["reset_epoch"]), []).append(row)
        elif row["kind"] == "print":
            if row["index"] == 0:
                prints.append([])
            assert prints, "Character occurred before a print command"
            prints[-1].append(row)
        else:
            raise AssertionError("Unknown trace row kind")
    commands = [0x30, 0x30, 0x30, 0x38, 0x08, 0x01, 0x06, 0x0C]
    assert sorted(init) == [1, 2, 3]
    assert [len(init[k]) for k in [1, 2, 3]] == [2, 8, 8]
    for group in init.values():
        assert [row["data_hex"] for row in group] == commands[:len(group)]
        assert all(row["rs"] == 0 for row in group)
    names = ["ADD", "SUB", "MUL", "DIV", "MOD", "AND", "OR", "XOR", "JMP"] + [""] * 7
    expected_order = list(range(16)) + [8, 3, 8]
    assert len(prints) == 19
    complete = []
    for i, (group, opcode) in enumerate(zip(prints, expected_order)):
        expected_length = 4 if i == 17 else 17
        assert len(group) == expected_length, (i, len(group))
        assert [row["index"] for row in group] == list(range(expected_length))
        assert all(int(row["opcode"], 16) == opcode for row in group)
        expected_bytes = [0x80] + list(names[opcode].ljust(16).encode("ascii"))
        assert [row["data_hex"] for row in group] == expected_bytes[:expected_length]
        assert [row["rs"] for row in group] == [0] + [1] * (expected_length - 1)
        if expected_length == 17:
            complete.append({"opcode": f"{opcode:X}", "text": names[opcode].ljust(16),
                             "first_fall_ns": group[0]["time_ns"], "last_fall_ns": group[-1]["time_ns"]})
    intervals = []
    for group in [*init.values(), *prints]:
        intervals.extend(b["time_ns"] - a["time_ns"] for a, b in zip(group, group[1:]))
    assert intervals and set(intervals) == {10000000}, "Cadence differs from exactly 10 ms"

    vcd_path = root / "lcd_trace.vcd"
    assert vcd_path.is_file(), "VCD is required for the independent pulse recheck; run with DUMP_VCD=1"
    ids, state, updates = {}, {}, {}
    time_ps = 0
    rise_ps = None
    pulses = []

    def flush():
        nonlocal rise_ps
        before = state.get("LCD_EN", "x")
        state.update(updates)
        after = state.get("LCD_EN", "x")
        if before != "1" and after == "1":
            assert state.get("RESET_N") == "1", "EN rise in reset"
            assert rise_ps is None
            rise_ps = time_ps
        if before == "1" and after != "1":
            assert after == "0" and rise_ps is not None
            pulses.append({"rise_ps": rise_ps, "fall_ps": time_ps,
                           "width_ps": time_ps - rise_ps, "reset_truncated": state.get("RESET_N") == "0"})
            rise_ps = None
        updates.clear()

    with vcd_path.open() as stream:
        for raw in stream:
            line = raw.strip()
            if line.startswith("$var "):
                parts = line.split()
                ids[parts[3]] = parts[4]
            elif line.startswith("#"):
                flush()
                time_ps = int(line[1:])
            elif line and line[0] in "01xz" and line[1:] in ids:
                updates[ids[line[1:]]] = line[0]
            elif line.startswith("b"):
                value, identifier = line[1:].split()
                if identifier in ids:
                    updates[ids[identifier]] = value
        flush()
    assert rise_ps is None
    valid = [pulse for pulse in pulses if not pulse["reset_truncated"]]
    truncated = [pulse for pulse in pulses if pulse["reset_truncated"]]
    assert len(valid) == 328 and all(pulse["width_ps"] == 1000000 for pulse in valid)
    assert len(truncated) == 2 and all(pulse["width_ps"] == 200000 for pulse in truncated)
    assert [pulse["fall_ps"] // 1000 for pulse in valid] == [row["time_ns"] for row in rows]
    summary = {
        "verdict": "PASS_TRACE_RECHECK", "fixture_not_confirmed_isa": True,
        "completed_initializations": 2, "completed_prints": 18,
        "all_opcodes_checked": [f"{n:X}" for n in range(16)],
        "valid_lcd_transfers": len(valid), "reset_truncated_en_pulses": len(truncated),
        "en_width_ns": 1000, "truncated_en_width_ns": 200, "byte_cadence_ns": 10000000,
        "complete_prints": complete,
        "sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                   for name in ["simulation.log", "lcd_trace.csv", "lcd_trace.vcd"]},
    }
    (root / "trace_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("PASS_TRACE_RECHECK: 328 transfers, 18 complete prints, all 16 opcodes, "
          "2 complete initializations, 1 us pulses and 10 ms cadence; 2 reset-truncated pulses")


if __name__ == "__main__":
    main()
