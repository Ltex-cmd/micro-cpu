#!/usr/bin/env python3
"""Make auditable simulator-only copies of unmodified Quartus GUI exports.

Remove only empty duplicate black-box declarations, adapt uppercase exported
LPM defparam identifiers to the official model's lowercase identifiers, and
represent numeric *_SVALUE/AVALUE/PVALUE parameters as the model's decimal
strings. No wires, ports, connections, register logic, or values are repaired.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

library = Path(sys.argv[1])
build = Path(sys.argv[2])
sources = [Path(arg) for arg in sys.argv[3:]]
model = library.read_text()
module_re = re.compile(r"^module\s+(\w+)\b.*?^endmodule\b[^\n]*", re.M | re.S)
originals = {path: path.read_text() for path in sources}
modules = {}
for path, source in originals.items():
    for match in module_re.finditer(source):
        modules.setdefault(match[1], []).append((path, match[0]))

report = {"sources": [], "removed_stubs": [], "parameter_adaptations": []}
output = build / "export_compat"
output.mkdir(parents=True, exist_ok=True)
output_paths = []
seen_names = set()

def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()

for path, source in originals.items():
    def remove_stub(match):
        name, body = match[1], match[0]
        if "/* synthesis black_box */" not in body:
            return body
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", body, flags=re.S)
        code = re.sub(r"^module\s+\w+\s*\([^;]*\)\s*;", "", code)
        code = re.sub(r"\b(?:input|output|inout)\b[^;]*;", "", code)
        code = re.sub(r"\bendmodule\b", "", code).strip()
        implementations = [(p, b) for p, b in modules[name]
                           if "/* synthesis black_box */" not in b]
        if code or len(implementations) != 1:
            raise SystemExit(f"Cannot safely remove stub {name}: nonempty or no unique real implementation")
        header = re.search(r"module\s+\w+\s*(\([^;]*\))", body)[1]
        real_header = re.search(r"module\s+\w+\s*(\([^;]*\))", implementations[0][1])[1]
        if re.sub(r"\s+", "", header) != re.sub(r"\s+", "", real_header):
            raise SystemExit(f"Stub and implementation port lists differ: {name}")
        report["removed_stubs"].append({"source": str(path), "module": name,
                                        "implementation": str(implementations[0][0])})
        return f"// Simulation only: empty {name} stub removed; real exported wrapper supplied."

    processed = module_re.sub(remove_stub, source)

    def adapt_parameter(match):
        prefix, parameter, value = match.groups()
        lower = parameter.lower()
        if not re.search(r"\bparameter\s+" + re.escape(lower) + r"\b", model):
            raise SystemExit(f"Official library does not declare parameter {lower}")
        adapted = value.strip()
        if lower in {"lpm_svalue", "lpm_avalue", "lpm_pvalue"} and re.fullmatch(r"\d+", adapted):
            adapted = '"' + adapted + '"'
        report["parameter_adaptations"].append({"source": str(path), "parameter": parameter,
                                                "to": lower, "value": value.strip(), "model_value": adapted})
        return prefix + lower + " = " + adapted + ";"

    processed = re.sub(r"(\bdefparam\s+\w+\.)(LPM_[A-Z0-9_]+)\s*=\s*([^;]+);",
                       adapt_parameter, processed)
    original_top = next((m[0] for m in module_re.finditer(source) if m[1] == "lcd_operation_display"), None)
    if original_top is not None:
        processed_top = next(m[0] for m in module_re.finditer(processed) if m[1] == "lcd_operation_display")
        if processed_top != original_top:
            raise SystemExit("Refusing any change to the actual lcd_operation_display module")
        report["top_module_sha256_unchanged"] = digest(original_top)
    if path.name in seen_names:
        raise SystemExit("Duplicate source basenames cannot be staged")
    seen_names.add(path.name)
    destination = output / path.name
    destination.write_text(processed)
    output_paths.append(str(destination.resolve()))
    report["sources"].append({"original": str(path), "simulator_copy": str(destination),
                               "original_sha256": digest(source), "simulator_sha256": digest(processed)})

rom = re.search(r"\bmodule\s+lpm_rom\b(.*?)\bendmodule\b", model, re.S)
if not rom or "$readmemh" not in rom[1]:
    raise SystemExit("Unsupported official lpm_rom simulation loader")
report["rom_loader"] = "intel_mif" if "convert_to_ver_file" in rom[1] else "readmemh"
(build / "export_compatibility.json").write_text(json.dumps(report, indent=2) + "\n")
(build / "sim_sources.txt").write_text("\n".join(output_paths) + "\n")
(build / "rom_loader.txt").write_text(report["rom_loader"] + "\n")
print(f"Simulator copies: {len(report['removed_stubs'])} empty stubs removed, "
      f"{len(report['parameter_adaptations'])} LPM parameters adapted; actual top unchanged")
print(f"Official ROM loader: {report['rom_loader']}")
