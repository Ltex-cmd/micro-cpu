#!/usr/bin/env python3
"""Verify preserved full-prefix + terminal reset-recovery coverage honestly."""
from pathlib import Path
import argparse
import hashlib
import json
import re

parser = argparse.ArgumentParser()
parser.add_argument('prefix', type=Path)
parser.add_argument('recovery', type=Path)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
p, r = args.prefix, args.recovery
logs = [(folder/'simulation.log').read_text() for folder in (p, r)]
for text in logs:
    assert not re.search(r'\bFAIL\b|\bFATAL\b|Assertion.*failed', text), 'Failure in a coverage log'
opcodes = [[int(x, 16) for x in re.findall(r'^PASS opcode ([0-9a-f]):', text, re.M)] for text in logs]
assert opcodes[0] == [*range(16), 8], opcodes[0]
assert opcodes[1] == [8], opcodes[1]
assert re.findall(r'^PASS init epoch (\d+)', logs[0], re.M) == ['2']
assert re.findall(r'^PASS init epoch (\d+)', logs[1], re.M) == ['2', '3']
assert 'Reset epoch 3 released' in logs[0]
assert 'PASS: actual DUT recovery checked;' in logs[1]
assert (r/'exit_status.txt').read_text().strip() == '0'
assert 'PASS: actual DUT checked;' not in logs[0], 'Prefix unexpectedly already has full terminal marker'
exports = sorted((p/'original_exports').glob('*.v'))
assert [x.name for x in exports] == sorted(x.name for x in (r/'original_exports').glob('*.v'))
source_hashes = {}
for source in exports:
    assert source.read_bytes() == (r/'original_exports'/source.name).read_bytes(), source.name
    source_hashes[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
for filename in ('control.mif', 'operations.mif'):
    assert (p/filename).read_bytes() == (r/filename).read_bytes(), filename
    source_hashes[filename] = hashlib.sha256((p/filename).read_bytes()).hexdigest()
models = []
for folder in (p, r):
    manifest = (folder/'input_manifest.txt').read_text()
    models.append(re.findall(r'^([0-9a-f]{64})\s+\S*/220model\.v$', manifest, re.M))
assert len(models[0]) == 1 and models[0] == models[1]
source_hashes['220model.v'] = models[0][0]
benches = [(folder/'tb_lcd_operation_display.sv').read_text() for folder in (p, r)]
monitor_blocks = [text.split('    initial begin : test_sequence')[0] for text in benches]
assert monitor_blocks[0] == monitor_blocks[1], 'A monitor or task assertion changed'
assert benches[0].split('    initial begin\n        #8000000000ns;')[1] == benches[1].split('    initial begin\n        #8000000000ns;')[1]
report = {
    'result': 'PASS coverage union',
    'single_uninterrupted_full_run': False,
    'full_prefix_log': str((p/'simulation.log').resolve()),
    'recovery_log': str((r/'simulation.log').resolve()),
    'completed_prints': {'prefix': 17, 'recovery': 1, 'total_across_runs': 18},
    'completed_initializations': {'prefix': 1, 'recovery': 2, 'total_across_runs': 3,
                                  'note': 'The recovery segment repeats the initial-reset setup, then completes reset-during-print recovery.'},
    'covered': ['All 16 fixture opcodes; command 80 and 16 exact characters per print',
                'Opcode latch; rejected initialization/busy PRINT edges; held-high PRINT; new idle edge',
                'Reset during initialization and in the middle of a print EN pulse; clean complete reinitialization',
                'Successful 16-character print after recovery, including opcode latch after reset',
                'No idle/reset EN; 1 us EN; 10 ms cadence; initialization deadlines; data/control stability and 20 ns hold'],
    'source_hashes_identical_across_runs': source_hashes,
    'identical_monitor_and_task_block_sha256': hashlib.sha256(monitor_blocks[0].encode()).hexdigest(),
    'limits': ['The prefix was interrupted by the execution environment and has no terminal full-suite PASS.',
               'Recovery is a separately reset simulation of the real DUT, not a resumed simulator checkpoint.',
               'The interrupted prefix CSV/VCD may have an unflushed tail; its completed-check log is preserved.',
               'Functional interface verification only; no physical-board or post-fit verification.'],
}
args.output.write_text(json.dumps(report, indent=2)+'\n')
print('PASS combined coverage: 16 opcodes, 17 prefix prints + 1 post-reset print, both interruptive reset scenarios')
print('Separate executions, same DUT/data/model and identical monitor/task assertions; no full single-run PASS is claimed.')
print('Report:', args.output)
