import hashlib
import itertools
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'lcd_de2_115_top.bdf'
DEST = SOURCE.parent / 'evidence/wrapper_connected_geometry_audit.json'
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

def keys(*items):
    return set(items)

expected_groups = [
    ('CLOCK_50', 1, keys('TOP.CLOCK_50','inst.CLOCK_50','inst1.CLK','inst2.CLK','inst3.CLK','inst4.CLK','inst5.CLK','SYNC_META.clock','SYNC_STABLE.clock','BUTTON_FILTER.clk')),
    ('ONE',1,keys('inst12.1','inst1.D')),
    ('RESET_META',1,keys('inst1.Q','inst2.D')),
    ('RESET_N',1,keys('inst2.Q','inst.RESET_N','inst3.CLRN','inst4.CLRN','inst5.CLRN','BUTTON_FILTER.rst_n','inst8.IN')),
    ('KEY_META',1,keys('inst3.Q','inst4.D')),
    ('KEY_SYNC',1,keys('inst4.Q','BUTTON_FILTER.inb')),
    ('BUTTON_CLEAN',1,keys('BUTTON_FILTER.outb','inst9.IN')),
    ('RESET_HIGH',1,keys('inst8.OUT','SYNC_META.aclr','SYNC_STABLE.aclr')),
    ('BUTTON_PRESSED',1,keys('inst9.OUT','inst5.D','inst11.IN1')),
    ('BUTTON_PREV',1,keys('inst5.Q','inst10.IN')),
    ('BUTTON_PREV_N',1,keys('inst10.OUT','inst11.IN2')),
    ('PRINT_PULSE',1,keys('inst11.OUT','inst.PRINT')),
    ('SW',4,keys('TOP.SW','SYNC_META.data')),
    ('META_BUS',4,keys('SYNC_META.q','SYNC_STABLE.data')),
    ('SYNC_Q',4,keys('SYNC_STABLE.q','inst.OPCODE')),
    ('KEY_INPUT_BUS',2,keys('TOP.KEY')),
    ('KEY[0]',1,keys('inst1.CLRN','inst2.CLRN')),
    ('KEY[1]',1,keys('inst3.D')),
]
for signal in ['LCD_DATA','LCD_EN','LCD_RS','LCD_RW','LCD_ON','BUSY','INIT_DONE']:
    expected_groups.append((signal,8 if signal == 'LCD_DATA' else 1,keys('inst.'+signal,'TOP.'+signal)))

actual_groups, direct_groups = [], []
attached_to_segment = set()
for component, indices in components.items():
    group = {p['key'] for p in ports if any(on(p['point'],segments[i]['a'],segments[i]['b']) for i in indices)}
    attached_to_segment.update(group)
    actual_groups.append({'component':component,'ports':group,'bus':segments[indices[0]]['bus'],'labels':labels[component]})
points = defaultdict(list)
for port in ports:
    if port['key'] not in attached_to_segment:
        points[port['point']].append(port)
for point, coports in points.items():
    if len(coports) > 1:
        entry = {'component':'direct:'+str(point),'ports':{p['key'] for p in coports},'bus':coports[0]['width']>1,'labels':[], 'point':point}
        actual_groups.append(entry)
        direct_groups.append(entry)

port_by_key = {p['key']:p for p in ports}
expected_ports = set().union(*(g[2] for g in expected_groups))
group_checks = []
for name, width, want in expected_groups:
    matches = [g for g in actual_groups if g['ports'] == want]
    valid = len(matches) == 1 and matches[0]['bus'] == (width > 1) and all(port_by_key[k]['width']==width for k in want)
    group_checks.append({'signal':name,'width':width,'expected_ports':sorted(want),'actual_matches':[m['component'] for m in matches],'valid':valid})
    if not valid:
        issues.append({'type':'endpoint_group_mismatch','signal':name,'expected_ports':sorted(want),'nearby_groups':[{**g,'ports':sorted(g['ports'])} for g in actual_groups if g['ports'] & want]})
for group in actual_groups:
    extra = group['ports'] - expected_ports
    if extra:
        issues.append({'type':'unexpected_connected_ports','ports':sorted(extra),'component':group['component']})
for name, want in [('KEY[0]',keys('inst1.CLRN','inst2.CLRN')),('KEY[1]',keys('inst3.D'))]:
    branch = [g for g in actual_groups if g['ports']==want]
    keybus = [g for g in actual_groups if g['ports']==keys('TOP.KEY')]
    valid = bool(branch and keybus and any(b==keybus[0]['component'] and w==branch[0]['component'] and labels[w]==[name] for b,w,_ in mixed))
    if not valid:
        issues.append({'type':'key_tap_mismatch','bit':name})

export_path = SOURCE.with_suffix('.v')
export_bytes = export_path.read_bytes()
export_text = export_bytes.decode()
compact = re.sub(r'\s+','',export_text)
export_checks = []
def check(name, valid, details=None):
    export_checks.append({'name':name,'valid':bool(valid),'details':details})
    if not valid:
        issues.append({'type':'export_mismatch','check':name,'details':details})

instances = {}
for match in re.finditer(r'(\w+)\s+(b2v_\w+)\s*\((.*?)\);',export_text,re.S):
    instances[match.group(2)] = {'type':match.group(1),'ports':dict(re.findall(r'\.(\w+)\s*\(\s*([^()]*)\s*\)',match.group(3)))}
want_core = dict(CLOCK_50='CLOCK_50',RESET_N='RESET_N',PRINT='PRINT_PULSE',OPCODE='SYNC_Q')
for signal in ['LCD_DATA','LCD_EN','LCD_RS','LCD_RW','LCD_ON','BUSY','INIT_DONE']:
    want_core[signal]=signal
check('core_instance_ports',instances.get('b2v_inst',{}).get('ports')==want_core)
check('button_filter_ports',instances.get('b2v_BUTTON_FILTER',{}).get('ports')==dict(rst_n='RESET_N',inb='KEY_SYNC',clk='CLOCK_50',outb='BUTTON_CLEAN'))
check('debounce_width_19','defparamb2v_BUTTON_FILTER.DELAY_BITS=19;' in compact)
check('scalar_key_sync','regKEY_SYNC;' in compact and 'SYNC_Q[4]' not in compact)
check('external_bus_widths','inputwire[1:0]KEY;' in compact and 'inputwire[3:0]SW;' in compact and 'outputwire[7:0]LCD_DATA;' in compact)
check('constant_one','assignSYNTHESIZED_WIRE_0=1;' in compact)
for name, expr in [('SYNTHESIZED_WIRE_1','~DFF_inst5'),('PRINT_PULSE','BUTTON_PRESSED&SYNTHESIZED_WIRE_1'),('SYNTHESIZED_WIRE_5','~RESET_N'),('BUTTON_PRESSED','~BUTTON_CLEAN')]:
    check('assign_'+name, 'assign'+name+'='+expr+';' in compact)
always_blocks = re.findall(r'always@\((.*?)\)\s*begin(.*?)\nend',export_text,re.S)
for reg, reset, data in [('DFF_inst1','KEY[0]','SYNTHESIZED_WIRE_0'),('RESET_N','KEY[0]','DFF_inst1'),('DFF_inst3','RESET_N','KEY[1]'),('KEY_SYNC','RESET_N','DFF_inst3'),('DFF_inst5','RESET_N','BUTTON_PRESSED')]:
    matching = [(event,body) for event,body in always_blocks if re.search(r'\b'+re.escape(reg)+r'\s*<=',body)]
    valid = len(matching)==1
    if valid:
        event, body = matching[0]
        valid = re.sub(r'\s+','',event)=='posedgeCLOCK_50ornegedge'+reset
        assignments=re.findall(r'\b'+re.escape(reg)+r'\s*<=\s*([^;]+);',body)
        valid = valid and [a.strip() for a in assignments]==['0',data] and 'if(!'+reset+')' in re.sub(r'\s+','',body)
    check('ff_'+reg,valid)
check('opcode_meta_ports',instances.get('b2v_SYNC_META',{}).get('ports')==dict(clock='CLOCK_50',aclr='SYNTHESIZED_WIRE_5',data='SW',q='SYNTHESIZED_WIRE_4'))
check('opcode_stable_ports',instances.get('b2v_SYNC_STABLE',{}).get('ports')==dict(clock='CLOCK_50',aclr='SYNTHESIZED_WIRE_5',data='SYNTHESIZED_WIRE_4',q='SYNC_Q'))
check('both_opcode_register_widths',len(re.findall(r'input\s*\[3:0\]\s*data;',export_text))==2 and len(re.findall(r'output\s*\[3:0\]\s*q;',export_text))==2)

report={
    'status':'PASS' if not issues else 'FAIL',
    'generated_at_utc':datetime.now(timezone.utc).isoformat(),
    'source':str(SOURCE),'source_sha256':hashlib.sha256(raw).hexdigest(),'source_mtime_ns':SOURCE.stat().st_mtime_ns,
    'export':str(export_path),'export_sha256':hashlib.sha256(export_bytes).hexdigest(),
    'method':'Read-only geometric groups compared with complete expected endpoint sets; coincident external/module ports treated as direct connections; scalar/bus types and KEY tap identities checked. Equal labels never join distant groups. Real Quartus-exported HDL checked independently for register clocks, resets, data flow and public ports.',
    'counts':{'symbols':len(symbols),'all_ports':len(ports),'expected_connected_ports':len(expected_ports),'logical_connection_groups':len(expected_groups),'direct_output_connections':len(direct_groups),'key_bus_taps':len(mixed),'export_checks':len(export_checks)},
    'issues':issues,'geometry_checks':group_checks,'bus_taps':taps,
    'direct_output_connections':[{**g,'ports':sorted(g['ports'])} for g in direct_groups],
    'export_checks':export_checks,
    'limitations':['Does not replace Quartus compilation or functional simulation.','The exported lpm_ff_0 and lpm_ff_1 modules are black-box declarations; Icarus requires the matching behavioral simulation models.','Debouncer implementation and its reset behavior are not reverified by this wrapper-only audit.']
}
DEST.parent.mkdir(parents=True,exist_ok=True)
DEST.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':report['status'],'counts':report['counts'],'issues':issues,'report':str(DEST),'source_sha256':report['source_sha256'],'export_sha256':report['export_sha256']},indent=2))
