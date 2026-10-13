#!/usr/bin/env bash
set -euo pipefail
SIM_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
LCD_DIR=$(cd -- "$SIM_DIR/.." && pwd)
mkdir -p "$SIM_DIR/build"
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror -O2 \
  "$LCD_DIR/../teste/txt_to_mif.c" -o "$SIM_DIR/build/txt_to_mif"
"$SIM_DIR/build/txt_to_mif" "$LCD_DIR/operations_fixture.txt" "$LCD_DIR/operations.mif"
python3 "$SIM_DIR/verify_mifs.py"
