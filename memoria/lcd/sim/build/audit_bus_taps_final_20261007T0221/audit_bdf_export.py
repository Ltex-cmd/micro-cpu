#!/usr/bin/env python3
"""Read-only structural audit for this Quartus BDF and its real Verilog export.

This supports this circuit's primitives and axis-aligned named wires/buses,
including named bit taps. Unsupported constructs fail rather than being ignored.
It is a structural cross-check, not a formal equivalence proof or Quartus parser.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import re


def children(node, kind):
    return [x for x in node[1:] if isinstance(x, list) and x[0] == kind]


def one(node, kind):
    found = children(node, kind)
    assert len(found) == 1, (node[0], kind, len(found))
    return found[0]


def parse_bdf(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|\(|\)|[^\s()]+', text)
    root, stack = [], []
    current = root
    for token in tokens:
        if token == '(':
            new = []
            current.append(new)
            stack.append(current)
            current = new
        elif token == ')':
            current = stack.pop()
        else:
            current.append(json.loads(token) if token.startswith('"') else token)
    assert not stack
    return ['root', *root]


def normalized(expression, widths):
    expression = re.sub(r'\s+', '', expression.replace('..', ':'))
    expression = expression.replace('BUSY_ALTERA_SYNTHESIZED', 'BUSY')
    expression = expression.replace('GDFX_TEMP_SIGNAL_0', '{OPCODE_Q[3:0],SLOT_Q[3:0]}')
    if ',' in expression and not expression.startswith('{'):
        expression = '{' + expression + '}'
    for name, width in widths.items():
        if width > 1:
            expression = re.sub(r'\b' + re.escape(name) + r'\[' + str(width-1) + r':0\]', name, expression)
    return expression


def expand_bits(expression, widths):
    """Expand a named vector/selection/concatenation in left-to-right bit order."""
    expression = expression.replace('..', ':').replace(' ', '').strip('{}')
    bits = []
    for term in expression.split(','):
        match = re.fullmatch(r'(\w+)(?:\[(\d+)(?::(\d+))?\])?', term)
        assert match, ('Unsupported net expression', expression)
        name, high, low = match.groups()
        if high is None:
            width = widths.get(name, 1)
            bits.extend([f'{name}[{n}]' for n in reversed(range(width))] if width > 1 else [name])
        else:
            high, low = int(high), int(low) if low is not None else int(high)
            assert name not in widths or max(high, low) < widths[name], ('Bit outside declared width', term)
            step = -1 if high >= low else 1
            bits.extend(f'{name}[{n}]' for n in range(high, low+step, step))
    assert len(set(bits)) == len(bits), ('Repeated member in bus expression', expression)
    return tuple(bits)


def symbol_port_width(port, parameters):
    text = children(port, 'text')[0][1]
    match = re.search(r'\[([^]]+)\]', text)
    if not match:
        return 1
    def bound(expression):
        expression = re.sub(r'LPM_\w+', lambda m: parameters[m[0].lower()], expression)
        assert re.fullmatch(r'\d+(?:-\d+)?', expression), ('Unsupported port bound', text)
        values = list(map(int, expression.split('-')))
        return values[0] - sum(values[1:])
    bounds = match[1].split('..')
    assert len(bounds) == 2
    return abs(bound(bounds[0])-bound(bounds[1]))+1


class Connectivity:
    """Keep wire and bus components separate; a tap joins only its named bit.

    A geometric crossing is connected only when an endpoint, port or explicit
    junction is there. Bus members are never shorted together by the drawing.
    Different scalar labels on one wire are a real conflict and remain fatal.
    """
    def __init__(self, segments, labels, points, widths):
        self.widths = widths
        points = set(points)
        for _, a, b in segments:
            points.update((a, b))
            assert a[0] == b[0] or a[1] == b[1], 'Non-axis-aligned connector'
        self.parent = {(kind, point): (kind, point) for kind in ('wire', 'bus') for point in points}
        occupied = collections.defaultdict(set)
        for kind, a, b in segments:
            for point in points:
                if (min(a[0], b[0]) <= point[0] <= max(a[0], b[0]) and
                        min(a[1], b[1]) <= point[1] <= max(a[1], b[1])):
                    self.parent[self.root(kind, point)] = self.root(kind, a)
                    occupied[kind].add(point)
        self.labels = collections.defaultdict(set)
        self.bits = {}
        for kind, point, label in labels:
            self.labels[self.root(kind, point)].add(label)
        for component, names in self.labels.items():
            vectors = {expand_bits(name, widths) for name in names}
            assert len(vectors) == 1, ('Conflicting net labels', component, sorted(names))
            vector = next(iter(vectors))
            assert component[0] == 'bus' or len(vector) == 1, ('Vector label on scalar wire', names)
            self.bits[component] = vector
        self.taps = []
        inferred = collections.defaultdict(set)
        for point in sorted(occupied['wire'] & occupied['bus']):
            scalar = self.root('wire', point)
            bus = self.root('bus', point)
            assert scalar in self.bits, ('Unnamed scalar tap is ambiguous', point)
            bit, = self.bits[scalar]
            if bus in self.bits:
                assert bit in self.bits[bus], ('Tap is not a member of bus', point, bit, self.bits[bus])
            inferred[bus].add(bit)
            self.taps.append({'point': list(point), 'member': bit,
                              'bus_members': list(self.bits[bus]) if bus in self.bits else None})
        self.unlabeled_bus_members = {str(component): sorted(bits) for component, bits in inferred.items()
                                     if component not in self.bits}

    def root(self, kind, point):
        node = (kind, point)
        while self.parent[node] != node:
            self.parent[node] = self.parent[self.parent[node]]
            node = self.parent[node]
        return node

    def port_net(self, point, width):
        component = self.root('bus' if width > 1 else 'wire', point)
        names = self.labels[component]
        if not names:
            assert str(component) not in self.unlabeled_bus_members, ('Unordered unnamed bus at port', point)
            return None
        assert len(self.bits[component]) == width, ('Port/bus width mismatch', point, width, self.bits[component])
        return sorted(names)[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('bdf', type=Path)
    parser.add_argument('source_dir', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    files = {p.name: p for p in args.source_dir.glob('*.v')}
    raw = files['lcd_operation_display.v'].read_text()
    top = re.search(r'^module lcd_operation_display\b.*?^endmodule', raw, re.M | re.S)[0]
    widths = {}
    declarations = {}
    for kind, width, name in re.findall(r'\b(input|output|wire|reg)\s+(?:(?:wire|reg)\s+)?(?:\[(\d+):0\]\s+)?(\w+)\s*;', top):
        widths[name] = int(width) + 1 if width else 1
        if kind in {'input', 'output'}:
            declarations[name] = (kind, widths[name])
    norm = lambda s: normalized(s, widths)
    assigns = {norm(a): norm(b) for a, b in re.findall(r'\bassign\s+(\w+)\s*=\s*([^;]+);', top)
               if norm(a) != norm(b)}
    instances = {}
    for module, name, body in re.findall(r'\b(\w+)\s+b2v_(\w+)\s*\((.*?)\);', top, re.S):
        instances[name] = {'module': module, 'ports': {p: norm(s) for p, s in re.findall(r'\.(\w+)\(([^)]*)\)', body)}}
    dffs = {}
    pattern = (r'always@\(posedge\s+(\w+)\s+or\s+negedge\s+(\w+)\)\s*begin\s*'
               r'if\s*\(!(\w+)\)\s*begin\s*(\w+)\s*<=\s*0;\s*end\s*else\s*begin\s*'
               r'(\w+)\s*<=\s*(\w+);\s*end\s*end')
    for clock, reset, checked, q, q2, data in re.findall(pattern, top, re.S):
        assert reset == checked and q == q2
        dffs[q] = {'CLK': clock, 'CLRN': reset, 'D': data, 'Q': q}
    assert len(dffs) == len(re.findall(r'\balways\s*@', top)), 'Unsupported sequential block'
    tree = parse_bdf(args.bdf.read_text())
    points, segments, connector_labels = set(), [], []
    for connector in children(tree, 'connector'):
        pts = [tuple(map(int, x[1:])) for x in children(connector, 'pt')]
        assert len(pts) == 2
        kind = 'bus' if children(connector, 'bus') else 'wire'
        segments.append((kind, *pts))
        points.update(pts)
        for label in children(connector, 'text'):
            connector_labels.append((kind, pts[0], norm(label[1])))
    for junction in children(tree, 'junction'):
        points.add(tuple(map(int, one(junction, 'pt')[1:])))
    # Pins carry real net labels too: an accidentally wired output must not be
    # accepted merely because its declaration still has the expected name.
    for pin in children(tree, 'pin'):
        origin = tuple(map(int, one(pin, 'rect')[1:3]))
        relative = tuple(map(int, one(pin, 'pt')[1:]))
        point = tuple(a+b for a, b in zip(origin, relative))
        points.add(point)
        label = norm(children(pin, 'text')[1][1])
        kind = 'bus' if len(expand_bits(label, widths)) > 1 else 'wire'
        connector_labels.append((kind, point, label))
    symbols = []
    for symbol in children(tree, 'symbol'):
        origin = tuple(map(int, one(symbol, 'rect')[1:3]))
        texts = children(symbol, 'text')
        kind, name = texts[0][1], texts[1][1]
        params = {p[1].lower(): p[2] for p in children(symbol, 'parameter') if p[2] != ''}
        ports = {}
        for port in children(symbol, 'port'):
            relative = tuple(map(int, one(port, 'pt')[1:]))
            point = tuple(a+b for a, b in zip(origin, relative))
            points.add(point)
            pname = children(port, 'text')[-1][1].split('[')[0]
            ports[pname] = (point, symbol_port_width(port, params))
        symbols.append((kind, name, ports, params))
    connectivity = Connectivity(segments, connector_labels, points, widths)
    bdf_declarations = {}
    for pin in children(tree, 'pin'):
        direction = 'input' if children(pin, 'input') else 'output'
        for name in children(pin, 'text')[1][1].split(','):
            match = re.fullmatch(r'(\w+)(?:\[(\d+)\.\.0\])?', name)
            assert match
            bdf_declarations[match[1]] = (direction, int(match[2])+1 if match[2] else 1)
    assert bdf_declarations == declarations, ('Top declarations differ', bdf_declarations, declarations)
    checks, used_instances, used_dffs, covered_assigns = [], set(), set(), set()
    for kind, name, coordinates, params in symbols:
        ports = {p: connectivity.port_net(point, width) for p, (point, width) in coordinates.items()
                 if connectivity.port_net(point, width) is not None}
        row = {'instance': name, 'type': kind, 'connected_ports': ports, 'parameters': params,
               'connected_port_bits': {p: list(expand_bits(net, widths)) for p, net in ports.items()}}
        if kind.startswith('LPM_') or kind == 'lcd_data_mux':
            actual = instances[name]
            assert ports == actual['ports'], (name, 'Port mismatch', ports, actual['ports'])
            wrapper = files[actual['module'] + '.v'].read_text()
            if kind.startswith('LPM_'):
                assert re.search(r'\b'+kind.lower()+r'\s+lpm_instance\b', wrapper)
                actual_params = {p.lower(): v.strip() for p, v in re.findall(r'defparam\s+\w+\.(\w+)\s*=\s*([^;]+);', wrapper)}
                assert params == actual_params, (name, 'Parameter mismatch', params, actual_params)
                wrapper_ports = {p: s for p, s in re.findall(r'\.(\w+)\(([^)]*)\)', wrapper)}
                assert wrapper_ports == {p: p for p in ports}, (name, 'Wrapper reorders ports')
            else:
                assert actual['module'] == kind
            row['export_module'] = actual['module']
            used_instances.add(name)
        elif kind == 'DFF':
            assert ports == dffs[ports['Q']], (name, 'DFF mismatch', ports, dffs.get(ports['Q']))
            used_dffs.add(ports['Q'])
        elif kind.startswith('AND'):
            inputs = [s for p, s in ports.items() if p.startswith('IN')]
            assert len(inputs) == int(kind[3:])
            assert sorted(inputs) == sorted(assigns[ports['OUT']].split('&')), (name, 'Gate mismatch')
            covered_assigns.add(ports['OUT'])
        elif kind == 'NOT':
            assert assigns[ports['OUT']] == '~' + ports['IN'], (name, 'NOT mismatch')
            covered_assigns.add(ports['OUT'])
        elif kind == 'WIRE':
            assert assigns[ports['OUT']] == ports['IN'], (name, 'WIRE mismatch')
            covered_assigns.add(ports['OUT'])
        elif kind in {'VCC', 'GND'}:
            assert len(ports) == 1
            output = next(iter(ports.values()))
            assert assigns[output] == ('1' if kind == 'VCC' else '0'), (name, 'Constant mismatch')
            covered_assigns.add(output)
        else:
            raise AssertionError(('Unsupported primitive', name, kind))
        checks.append(row)
    assert used_instances == set(instances), ('Unmatched IPs', set(instances)-used_instances)
    assert used_dffs == set(dffs), ('Unmatched DFFs', set(dffs)-used_dffs)
    # Exporter-created aliases were normalized above and checked at their uses.
    remaining = {a: b for a, b in assigns.items() if a not in covered_assigns}
    assert not remaining, ('Unmatched assignments', remaining)
    hashed = [args.bdf, *sorted(files.values())]
    report = {
        'result': 'PASS',
        'scope': 'Structural BDF-to-export cross-check; not a formal equivalence proof or Quartus re-export',
        'sources_sha256': {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in hashed},
        'top_ports': bdf_declarations,
        'counts': {'symbols': len(symbols), 'ips': len(used_instances), 'dffs': len(used_dffs),
                   'primitive_combinational_symbols': len(symbols)-len(used_instances)-len(used_dffs)},
        'checks': checks,
        'named_bit_taps': connectivity.taps,
        'unlabeled_bus_members': connectivity.unlabeled_bus_members,
        'limits': ['Custom lcd_data_mux body is matched by source module identity and hashed; it is not independently regenerated.',
                   'Only explicit nonempty LPM parameters are compared; official library defaults remain library-defined.',
                   'No fitting, pin assignment, analog LCD, board, or timing analysis is performed.'],
    }
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print('PASS BDF/export structural cross-check:', report['counts'])
    print('Report:', args.output)


if __name__ == '__main__':
    main()
