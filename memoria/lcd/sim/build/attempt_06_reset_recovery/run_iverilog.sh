#!/usr/bin/env bash
# Run only the real Quartus-exported DUT. No substitute implementation is used.
set -euo pipefail
SIM_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
LCD_DIR=$(cd -- "$SIM_DIR/.." && pwd)
BUILD_DIR="$SIM_DIR/build"
SCENARIO=${SIM_SCENARIO:-full}
case "$SCENARIO" in
  full) PASS_MARKER='^PASS: actual DUT checked;' ;;
  reset_recovery) PASS_MARKER='^PASS: actual DUT recovery checked;' ;;
  *) echo "Unsupported SIM_SCENARIO: $SCENARIO" >&2; exit 2 ;;
esac

if (( $# == 0 )); then
  echo "Usage: QUARTUS_ROOTDIR=/path/to/quartus bash $0 real_export.v [other_real_sources.v ...]" >&2
  echo "Optional: QUARTUS_SIM_LIB=/path/to/eda/sim_lib, DUMP_VCD=1" >&2
  exit 2
fi
for tool in iverilog vvp python3; do
  command -v "$tool" >/dev/null || { echo "Required tool is absent: $tool" >&2; exit 127; }
done

SIM_LIB=${QUARTUS_SIM_LIB:-}
if [[ -z "$SIM_LIB" ]]; then
  for root in "${QUARTUS_ROOTDIR:-}" /home/agent/altera_lite/25.1std/quartus; do
    [[ -n "$root" ]] || continue
    for candidate in "$root/eda/sim_lib" "$root/quartus/eda/sim_lib"; do
      if [[ -f "$candidate/220model.v" ]]; then SIM_LIB=$candidate; break 2; fi
    done
  done
fi
[[ -f "$SIM_LIB/220model.v" ]] || {
  echo "220model.v not found. Set QUARTUS_ROOTDIR or QUARTUS_SIM_LIB to the real installation." >&2
  exit 2
}
SIM_LIB=$(cd -- "$SIM_LIB" && pwd)
SOURCES=()
for source in "$@"; do
  [[ -f "$source" ]] || { echo "Missing exported source: $source" >&2; exit 2; }
  SOURCES+=("$(cd -- "$(dirname -- "$source")" && pwd)/$(basename -- "$source")")
done

# The Intel LPM_ROM behavioral library commonly reads lpm_file with readmemh.
# Check the installed model instead of assuming it can parse Intel MIF text.
# No netlist is edited: relative ROM names resolve to simulation-only hex data
# in the build working directory. Absolute or subdirectory paths are rejected.
python3 - "$SIM_LIB/220model.v" "${SOURCES[@]}" <<'PY'
from pathlib import Path
import re
import sys

model = Path(sys.argv[1]).read_text(errors="replace")
module = re.search(r"\bmodule\s+lpm_rom\b(.*?)\bendmodule\b", model, re.I | re.S)
if not module or "$readmemh" not in module.group(1):
    raise SystemExit("Installed lpm_rom is not the expected readmemh loader. "
                     "Inspect the installed simulation model before adapting the runner.")
source = "\n".join(Path(path).read_text(errors="replace") for path in sys.argv[2:])
if not re.search(r"\bmodule\s+lcd_operation_display\b", source):
    raise SystemExit("The supplied files do not declare the real lcd_operation_display DUT.")
files = re.findall(r'lpm_file\s*(?:=|\()\s*"([^"]+)"', source, re.I)
allowed = {"control.mif", "operations.mif", "control.hex", "operations.hex"}
for name in files:
    if name not in allowed:
        raise SystemExit(f"Unsupported lpm_file {name!r}: use relative control.mif and "
                         "operations.mif in the BDF, then export again. Do not edit the DUT here.")
if not any(name.startswith("control.") for name in files) or not any(
        name.startswith("operations.") for name in files):
    raise SystemExit("Both control and operations LPM_ROM file parameters must be present "
                     "in the actual exported source(s). Add any exported submodule sources.")
print("PASS simulation input preflight: top module, relative ROM names and readmemh library")
PY

python3 "$SIM_DIR/verify_mifs.py" --stage "$BUILD_DIR"
python3 "$SIM_DIR/prepare_quartus_sources.py" "$SIM_LIB/220model.v" "$BUILD_DIR" "${SOURCES[@]}"
mapfile -t SIM_SOURCES < "$BUILD_DIR/sim_sources.txt"
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
  printf 'Simulation scenario: %s\n' "$SCENARIO"
  sha256sum "$LCD_DIR/lcd_operation_display.bdf" "${SOURCES[@]}" \
    "$LCD_DIR/control.mif" "$LCD_DIR/operations.mif" \
    "$SIM_DIR/tb_lcd_operation_display.sv" "$SIM_LIB/220model.v" \
    "$BUILD_DIR/export_compatibility.json" "${SIM_SOURCES[@]}"
} > "$BUILD_DIR/input_manifest.txt"

cd -- "$BUILD_DIR"
printf 'Compiling the supplied real exported DUT with Intel simulation libraries...\n'
iverilog -g2012 -Wall -s tb_lcd_operation_display \
  -I "$SIM_LIB" -o "$BUILD_DIR/lcd_operation_display.vvp" \
  "$SIM_DIR/tb_lcd_operation_display.sv" "${SIM_SOURCES[@]}" "${LIBRARIES[@]}" \
  2>&1 | tee compile.log

OPTIONS=()
[[ ${DUMP_VCD:-0} != 1 ]] || OPTIONS+=(+VCD)
[[ "$SCENARIO" != reset_recovery ]] || OPTIONS+=(+RECOVERY_ONLY)
vvp -i "$BUILD_DIR/lcd_operation_display.vvp" "${OPTIONS[@]}" 2>&1 | tee simulation.log
if ! grep -q "$PASS_MARKER" simulation.log; then
  echo "Simulation ended without the complete checker PASS marker." >&2
  exit 1
fi
echo "Logs, input hashes and LCD byte trace: $BUILD_DIR"
