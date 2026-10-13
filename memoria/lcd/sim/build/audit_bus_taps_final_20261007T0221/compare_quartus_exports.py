#!/usr/bin/env python3
"""Compare two frozen Quartus Verilog exports, retaining string literals."""
from pathlib import Path
import argparse
import hashlib
import json
import re


def tokens(text):
    pattern = r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|[a-zA-Z_$][\w$]*|\d+|[^\s]'
    return [token for token in re.findall(pattern, text, re.S)
            if not token.startswith('//') and not token.startswith('/*')]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('tested', type=Path)
    parser.add_argument('fresh', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    tested = {path.name: path for path in args.tested.glob('*.v')}
    fresh = {path.name: path for path in args.fresh.glob('*.v')}
    assert tested and tested.keys() == fresh.keys(), 'Source file sets differ'
    result = []
    without_created = lambda text: re.sub(r'^// CREATED[^\n]*\n', '', text, flags=re.M)
    for name in sorted(tested):
        before, after = tested[name].read_text(), fresh[name].read_text()
        result.append({'file': name, 'byte_identical': before == after,
                       'identical_except_created_comment': without_created(before) == without_created(after),
                       'verilog_tokens_identical': tokens(before) == tokens(after),
                       'tested_sha256': hashlib.sha256(tested[name].read_bytes()).hexdigest(),
                       'fresh_sha256': hashlib.sha256(fresh[name].read_bytes()).hexdigest()})
    passed = all(row['verilog_tokens_identical'] for row in result)
    args.output.write_text(json.dumps({
        'result': 'PASS' if passed else 'DIFFERENCES',
        'scope': 'Ordered Verilog token equality; comments and whitespace excluded, string contents retained',
        'files': result}, indent=2)+'\n')
    assert passed, ('Functional token differences; inspect', str(args.output))
    print(f'PASS: {len(result)} exported sources have identical functional tokens; '
          f'{sum(row["byte_identical"] for row in result)} are byte-identical')
    if all(row['identical_except_created_comment'] for row in result):
        print('All byte differences are confined to the // CREATED timestamp comment.')


if __name__ == '__main__':
    main()
