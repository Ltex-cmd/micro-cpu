#!/usr/bin/env bash
# Simulate the actual board BDF export; never substitute or edit the DUT.
set -euo pipefail
SIM_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
LCD_DIR=$(cd -- "$SIM_DIR/.." && pwd)
BUILD_DIR="$SIM_DIR/build/board"
if (( $# == 0 )); then
  echo "Usage: QUARTUS_SIM_LIB=/path/to/eda/sim_lib bash $0 board_export.v core_export.v other_real_sources.v ..." >&2
  exit 2
fi
for tool in iverilog vvp python3; do
  command -v "$tool" >/dev/null || { echo "Required tool is absent: $tool" >&2; exit 127; }
done
SIM_LIB=${QUARTUS_SIM_LIB:-/workspace/shared/quartus_sim_lib}
[[ -f "$SIM_LIB/220model.v" ]] || { echo "Missing official 220model.v: $SIM_LIB" >&2; exit 2; }
SIM_LIB=$(cd -- "$SIM_LIB" && pwd)
SOURCES=()
for source in "$@"; do
  [[ -f "$source" ]] || { echo "Missing real exported source: $source" >&2; exit 2; }
  SOURCES+=("$(cd -- "$(dirname -- "$source")" && pwd)/$(basename -- "$source")")
done

python3 "$SIM_DIR/verify_mifs.py" --stage "$BUILD_DIR"
python3 "$SIM_DIR/prepare_quartus_sources.py" "$SIM_LIB/220model.v" "$BUILD_DIR" "${SOURCES[@]}"
mapfile -t SIM_SOURCES < "$BUILD_DIR/sim_sources.txt"

# Obtain a read-only hierarchical probe from the real exported top. Also
# verify that both top modules survived compatibility staging byte for byte.
python3 - "$BUILD_DIR" "${SOURCES[@]}" <<'PY'
from pathlib import Path
import hashlib
import json
import re
import sys

build = Path(sys.argv[1])
sources = [Path(arg) for arg in sys.argv[2:]]
module_re = re.compile(r"^module\s+(\w+)\b.*?^endmodule\b[^\n]*", re.M | re.S)
modules = {}
for path in sources:
    for match in module_re.finditer(path.read_text()):
        if "/* synthesis black_box */" not in match[0]:
            modules.setdefault(match[1], []).append((path, match[0]))
for name in ("lcd_de2_115_top", "lcd_operation_display", "debouncer"):
    if len(modules.get(name, [])) != 1:
        raise SystemExit(f"Exactly one real implementation of {name} must be supplied")
board_path, top = modules["lcd_de2_115_top"][0]
for name in ("RESET_N", "SYNC_Q", "BUTTON_CLEAN", "PRINT_PULSE"):
    if not re.search(r"\b" + name + r"\b", top):
        raise SystemExit(f"Missing expected observed board net {name}; inspect the GUI export")
filters = re.findall(r"\bdebouncer\s+(\w+)\s*\(", top)
if len(filters) != 1:
    raise SystemExit("Cannot identify exactly one real debouncer instance in board export")
cores = re.findall(r"\blcd_operation_display\s+(\w+)\s*\(", top)
if len(cores) != 1:
    raise SystemExit("Cannot identify exactly one real LCD core instance in board export")
all_source = "\n".join(path.read_text() for path in sources)
rom_files = set(re.findall(r'lpm_file\s*(?:=|\()\s*"([^"]+)"', all_source, re.I))
if not {"control.mif", "operations.mif"}.issubset(rom_files):
    raise SystemExit("Both relative control.mif and operations.mif parameters must be present")
if rom_files - {"control.mif", "operations.mif"}:
    raise SystemExit(f"Unexpected ROM file names: {rom_files}")
report = {"filter_instance": filters[0], "core_instance": cores[0], "unchanged_modules": {}}
for name in ("lcd_de2_115_top", "lcd_operation_display", "debouncer"):
    path, original = modules[name][0]
    staged_text = (build / "export_compat" / path.name).read_text()
    staged = [m[0] for m in module_re.finditer(staged_text) if m[1] == name]
    if staged != [original]:
        raise SystemExit(f"Refusing simulation because the real {name} module was changed")
    report["unchanged_modules"][name] = hashlib.sha256(original.encode()).hexdigest()
sync_probe = "{dut.KEY_SYNC, dut.SYNC_Q[3:0]}" if re.search(r"\bKEY_SYNC\b", top) else "dut.SYNC_Q"
report["sync_bus_probe"] = sync_probe
(build / "board_probe_paths.svh").write_text(
    f"`define BOARD_FILTER dut.{filters[0]}\n`define BOARD_SYNC_BUS {sync_probe}\n")
(build / "board_preflight.json").write_text(json.dumps(report, indent=2) + "\n")
print("PASS board input preflight: unchanged real board/core/debouncer and relative ROM paths")
PY

if [[ $(cat "$BUILD_DIR/rom_loader.txt") == intel_mif ]]; then
  cp "$LCD_DIR/control.mif" "$LCD_DIR/operations.mif" "$BUILD_DIR/"
fi
LIBRARIES=(-l "$SIM_LIB/220model.v")
for library in altera_primitives.v altera_mf.v sgate.v; do
  [[ ! -f "$SIM_LIB/$library" ]] || LIBRARIES+=(-l "$SIM_LIB/$library")
done
{
  date -u '+UTC %Y-%m-%dT%H:%M:%SZ'
  iverilog -V 2>&1 | head -n 2 || true
  printf 'Quartus simulation library: %s\n' "$SIM_LIB"
  sha256sum "$LCD_DIR/lcd_de2_115_top.bdf" "$LCD_DIR/lcd_operation_display.bdf" \
    "$LCD_DIR/lcd_de2_115_top.qsf" "$LCD_DIR/lcd_de2_115_top.sdc" \
    "${SOURCES[@]}" "$LCD_DIR/control.mif" "$LCD_DIR/operations.mif" \
    "$SIM_DIR/tb_lcd_de2_115_top.sv" "$SIM_DIR/run_board_iverilog.sh" \
    "$SIM_LIB/220model.v" "$BUILD_DIR/export_compatibility.json" \
    "$BUILD_DIR/board_preflight.json" "${SIM_SOURCES[@]}"
} > "$BUILD_DIR/input_manifest.txt"

cd -- "$BUILD_DIR"
iverilog -g2012 -Wall -s tb_lcd_de2_115_top -I "$SIM_LIB" -I "$BUILD_DIR" \
  -o "$BUILD_DIR/lcd_de2_115_top.vvp" "$SIM_DIR/tb_lcd_de2_115_top.sv" \
  "${SIM_SOURCES[@]}" "${LIBRARIES[@]}" 2>&1 | tee compile.log
OPTIONS=()
[[ ${DUMP_VCD:-0} != 1 ]] || OPTIONS+=(+VCD)
vvp -i "$BUILD_DIR/lcd_de2_115_top.vvp" "${OPTIONS[@]}" 2>&1 | tee simulation.log
if ! grep -q '^PASS: actual board DUT checked;' simulation.log; then
  echo "Board simulation ended without the complete checker PASS marker." >&2
  exit 1
fi
echo "Board logs, source hashes and LCD byte trace: $BUILD_DIR"
