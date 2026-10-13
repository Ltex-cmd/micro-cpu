import hashlib
import itertools
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'lcd_operation_display.bdf'
DEST = SOURCE.parent / 'evidence/connected_geometry_audit.json'
raw = SOURCE.read_bytes()
text = raw.decode()
segments, junctions, ports, symbols = [], set(), [], []

def expand(label):
    result = []
    for part in label.split(','):
        part = part.strip()
        m = re.fullmatch(r'(\w+)\[(\d+)\.\.(\d+)\]', part)
        if m:
            name, first, last = m.group(1), int(m.group(2)), int(m.group(3))
            result.extend(f'{name}[{i}]' for i in range(first, last + (1 if last >= first else -1), 1 if last >= first else -1))
        elif part:
            result.append(part)
    return result

for block in re.split(r'(?m)(?=^\()', text):
    if block.startswith('(connector'):
        pts = [tuple(map(int, p.split())) for p in re.findall(r'\(pt ([^)]+)\)', block)]
        lab = re.search(r'\(text "([^"]+)"', block)
        segments.append({'a': pts[0], 'b': pts[1], 'bus': '(bus)' in block, 'label': lab.group(1) if lab else ''})
    elif block.startswith('(junction'):
        junctions.add(tuple(map(int, re.search(r'\(pt ([^)]+)\)', block).group(1).split())))
    elif block.startswith('(symbol'):
        typ, name = re.findall(r'^\t\(text "([^"]+)"', block, re.M)[:2]
        x, y, right, bottom = map(int, re.search(r'\(rect ([^)]+)\)', block).group(1).split())
        params = dict(re.findall(r'\(parameter\s+"([^"]+)"\s+"((?:\\.|[^"\\])*)"', block))
        symbols.append({'name': name, 'type': typ, 'rect': [x, y, right, bottom]})
        for part in block.split('\t(port')[1:]:
            dx, dy = map(int, re.search(r'\(pt ([^)]+)\)', part).group(1).split())
            port = re.search(r'\(text "([^"]+)"', part).group(1)
            direction = re.search(r'\((input|output|inout)\)', part).group(1)
            width = 1
            if '[' in port:
                bounds = port.split('[', 1)[1].rstrip(']').split('..')
                nums = []
                for bound in bounds:
                    match = re.fullmatch(r'(LPM_\w+)-1', bound)
                    nums.append(int(params[match.group(1)]) - 1 if match else int(bound))
                width = abs(nums[0] - nums[1]) + 1
            ports.append({'key': name + '.' + port.split('[')[0], 'name': port, 'direction': direction, 'point': (x + dx, y + dy), 'width': width})
    elif block.startswith('(pin'):
        x, y, _, _ = map(int, re.search(r'\(rect ([^)]+)\)', block).group(1).split())
        dx, dy = map(int, re.search(r'\(pt ([^)]+)\)', block).group(1).split())
        direction, name = re.findall(r'^\t\(text "([^"]+)"', block, re.M)[:2]
        ports.append({'key': 'TOP.' + name.split('[')[0], 'name': name, 'direction': direction.lower(), 'point': (x + dx, y + dy), 'width': len(expand(name))})

def on(point, a, b):
    return ((point[0] - a[0]) * (b[1] - a[1]) == (point[1] - a[1]) * (b[0] - a[0])
            and min(a[0], b[0]) <= point[0] <= max(a[0], b[0])
            and min(a[1], b[1]) <= point[1] <= max(a[1], b[1]))

parent = list(range(len(segments)))
def root(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i
def join(i, j):
    parent[root(i)] = root(j)

contacts, crossings = [], []
for i, j in itertools.combinations(range(len(segments)), 2):
    u, v = segments[i], segments[j]
    shared = {p for p in (u['a'], u['b'], v['a'], v['b']) if on(p, u['a'], u['b']) and on(p, v['a'], v['b'])}
    if shared:
        contacts.append((i, j, shared))
        if u['bus'] == v['bus']:
            join(i, j)
        continue
    point = None
    if u['a'][0] == u['b'][0] and v['a'][1] == v['b'][1]:
        point = (u['a'][0], v['a'][1])
    elif u['a'][1] == u['b'][1] and v['a'][0] == v['b'][0]:
        point = (v['a'][0], u['a'][1])
    if point and on(point, u['a'], u['b']) and on(point, v['a'], v['b']):
        crossings.append((i, j, point, point in junctions))
        if point in junctions:
            contacts.append((i, j, {point}))
            if u['bus'] == v['bus']:
                join(i, j)

components = defaultdict(list)
for i in range(len(segments)):
    components[root(i)].append(i)
labels = {r: sorted({segments[i]['label'] for i in inds if segments[i]['label']}) for r, inds in components.items()}
bits = {r: expand(labs[0]) if labs else [] for r, labs in labels.items()}
issues = []
for r, labs in labels.items():
    if len(labs) > 1:
        issues.append({'type': 'conflicting_labels', 'component': r, 'labels': labs})

mixed = set()
for i, j, points in contacts:
    if segments[i]['bus'] == segments[j]['bus']:
        continue
    b, w = (root(i), root(j)) if segments[i]['bus'] else (root(j), root(i))
    for point in points:
        mixed.add((b, w, point))
for b, w, point in mixed:
    if not labels[b] and len(bits[w]) == 1 and bits[w][0] not in bits[b]:
        bits[b].append(bits[w][0])

bit_parent = {}
def bitroot(node):
    bit_parent.setdefault(node, node)
    if bit_parent[node] != node:
        bit_parent[node] = bitroot(bit_parent[node])
    return bit_parent[node]
def bitjoin(a, b):
    bit_parent[bitroot(a)] = bitroot(b)

taps = []
for b, w, point in sorted(mixed):
    selected = bits[w]
    good = len(selected) == 1 and selected[0] in bits[b]
    taps.append({'point': point, 'bus_labels': labels[b], 'wire_labels': labels[w], 'selected_bit': selected, 'valid': good})
    if good:
        bitjoin((b, selected[0]), (w, selected[0]))
    else:
        issues.append({'type': 'invalid_bus_tap', 'point': point, 'bus_labels': labels[b], 'wire_labels': labels[w]})

# Expected endpoint map, reconstructed from the named ports and original named
# connections inspected before the graphical rerouting. Names below are used
# only to check the result; they never join disconnected geometry.
expected = {}
def expect(instance, mapping):
    for port, signal in mapping.items():
        expected[instance + '.' + port] = expand(signal)

T, S, O = 'TIMER_Q[18..0]', 'SLOT_Q[4..0]', 'OPCODE_Q[3..0]'
expect('TOP', dict(CLOCK_50='CLOCK_50', RESET_N='RESET_N', OPCODE='OPCODE[3..0]', PRINT='PRINT', LCD_DATA='LCD_DATA[7..0]', LCD_EN='LCD_EN', LCD_RS='LCD_RS', LCD_RW='LCD_RW', LCD_ON='LCD_ON', BUSY='BUSY', INIT_DONE='INIT_DONE'))
expect('TIMER', dict(sclr='ACCEPT', clock='CLOCK_50', aclr='RESET', q=T))
expect('SLOT', dict(sload='ACCEPT', sset='RETURN_IDLE', data='K15[4..0]', clock='CLOCK_50', aclr='RESET', cnt_en='BYTE_ADVANCE', q=S))
expect('CMP_GE50', dict(dataa=T, datab='FIFTY_CONST[18..0]', ageb='GE50'))
expect('CMP_LT100', dict(dataa=T, datab='K100[18..0]', alb='LT100'))
expect('CMP_FRAME_END', dict(dataa=T, datab='KEND[18..0]', aeb='FRAME_END'))
for name, signal in [('CONST_50','FIFTY_CONST[18..0]'), ('inst2','K100[18..0]'), ('inst3','KEND[18..0]'), ('inst4','K15[4..0]'), ('inst8','FIVE_CONST[4..0]'), ('inst9','K13[4..0]')]:
    expect(name, {'result': signal})
expect('ROM_CONTROL', dict(address='SLOT_Q[3..0]', inclock='CLOCK_50', q='CTRL_DATA[7..0]'))
expect('ROM_OPERATIONS', dict(address=O + ',SLOT_Q[3..0]', inclock='CLOCK_50', q='TEXT_DATA[7..0]'))
expect('CMP_SLOT5', dict(dataa=S, datab='FIVE_CONST[4..0]', ageb='STATE_GE5'))
expect('CMP_IDLE', dict(dataa=S, datab='K13[4..0]', aeb='IDLE', ageb='INIT_DONE'))
expect('inst10', dict(IN1='FRAME_END', IN2='BUSY', OUT='BYTE_ADVANCE'))
expect('inst11', dict(IN1='FRAME_END', IN2='SLOT31', OUT='RETURN_IDLE'))
expect('inst12', dict(IN1='STATE_GE5', IN2='BUSY', OUT='SEND_ACTIVE'))
expect('inst', dict(IN1='SEND_ACTIVE', IN2='GE50', IN3='LT100', OUT='EN_NEXT'))
expect('inst13', dict(IN='IDLE', OUT='BUSY'))
expect('inst14', dict(IN='PRINT_PREV', OUT='PRINT_PREV_N'))
expect('inst15', dict(IN='RST_N', OUT='RESET'))
for name, d, q, clear in [('inst16','EN_NEXT','LCD_EN','RST_N'), ('inst17','PRINT','PRINT_PREV','RST_N'), ('inst18','ONE','RESET_STAGE1','RESET_N'), ('inst19','RESET_STAGE1','RST_N','RESET_N')]:
    expect(name, dict(D=d, Q=q, CLK='CLOCK_50', CLRN=clear))
expect('OPCODE_LATCH', dict(data='OPCODE[3..0]', clock='CLOCK_50', enable='ACCEPT', aclr='RESET', q=O))
expect('ACCEPT_GATE', dict(IN1='PRINT', IN2='PRINT_PREV_N', IN3='IDLE', OUT='ACCEPT'))
expect('inst1', {'1': 'LCD_ON'})
expect('inst5', {'1': 'LCD_RW'})
expect('CONST_ONE', {'1': 'ONE'})
expect('inst6', dict(IN='SLOT_Q[4]', OUT='LCD_RS'))
expect('LAST_SLOT', dict(IN1='SLOT_Q[4]', IN2='SLOT_Q[0]', IN3='ONE', IN4='SLOT_Q[3]', IN5='SLOT_Q[2]', IN6='SLOT_Q[1]', OUT='SLOT31'))
expect('DATA_MUX', dict(data1x='TEXT_DATA[7..0]', data0x='CTRL_DATA[7..0]', sel='SLOT_Q[4]', result='LCD_DATA[7..0]'))

port_checks, signal_nodes = [], defaultdict(list)
for port in ports:
    connected = sorted({root(i) for i, seg in enumerate(segments) if on(port['point'], seg['a'], seg['b'])})
    want = expected.get(port['key'])
    if want is None:
        if connected:
            issues.append({'type': 'unexpected_connected_port', 'port': port, 'components': connected})
        continue
    actual = bits[connected[0]] if len(connected) == 1 else []
    valid = len(connected) == 1 and actual == want and port['width'] == len(want)
    port_checks.append({**port, 'expected_bits': want, 'actual_bits': actual, 'components': connected, 'valid': valid})
    if not valid:
        issues.append({'type': 'port_connection_mismatch', 'port': port['key'], 'point': port['point'], 'expected': want, 'actual': actual, 'components': connected})
    if valid:
        for bit in want:
            node = (connected[0], bit)
            signal_nodes[bit].append((port['key'], node))

signal_checks = []
for signal, endpoint_nodes in sorted(signal_nodes.items()):
    groups = defaultdict(list)
    for port, node in endpoint_nodes:
        groups[str(bitroot(node))].append(port)
    valid = len(groups) == 1
    signal_checks.append({'signal': signal, 'physical_groups': list(groups.values()), 'valid': valid})
    if not valid:
        issues.append({'type': 'disconnected_named_signal', 'signal': signal, 'physical_groups': list(groups.values())})

known = {p['key'] for p in ports}
for missing in set(expected) - known:
    issues.append({'type': 'expected_port_missing', 'port': missing})

visual = []
for a, b in itertools.combinations(symbols, 2):
    x, y = max(a['rect'][0], b['rect'][0]), max(a['rect'][1], b['rect'][1])
    right, bottom = min(a['rect'][2], b['rect'][2]), min(a['rect'][3], b['rect'][3])
    if right > x and bottom > y:
        visual.append({'type': 'overlapping_symbol_bounds', 'symbols': [a['name'], b['name']], 'overlap_rect': [x, y, right, bottom], 'area': (right-x)*(bottom-y)})

report = {
    'status': 'PASS' if not issues else 'FAIL',
    'generated_at_utc': datetime.now(timezone.utc).isoformat(),
    'source': str(SOURCE), 'source_sha256': hashlib.sha256(raw).hexdigest(),
    'source_mtime_ns': SOURCE.stat().st_mtime_ns,
    'method': 'Geometric segments and explicit junctions; separate scalar/bus components; per-bit unions only at physically touching, named bus taps. Equal labels on distant components are never joined. Every expected original endpoint and every optional port is checked.',
    'limitations': ['Read-only BDF geometry audit; compilation and simulation results are separate.', 'Symbol bounding rectangles conservatively approximate visible bodies.'],
    'counts': {'segments': len(segments), 'symbols': len(symbols), 'all_ports': len(ports), 'expected_connected_ports': len(expected), 'checked_connected_ports': len(port_checks), 'checked_signal_bits': len(signal_checks), 'bus_taps': len(taps)},
    'issues': issues, 'port_checks': port_checks, 'signal_checks': signal_checks, 'bus_taps': taps,
    'visual_findings': visual,
    'crossings_without_junction': [{'point': point, 'first_labels': labels[root(i)], 'second_labels': labels[root(j)]} for i, j, point, dot in crossings if not dot and root(i) != root(j)]
}
DEST.parent.mkdir(parents=True, exist_ok=True)
DEST.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': report['status'], 'counts': report['counts'], 'issues': issues, 'visual_findings': visual, 'report': str(DEST), 'source_sha256': report['source_sha256']}, ensure_ascii=False, indent=2))
