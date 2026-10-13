#!/usr/bin/env python3
"""Generate the LCD text ROM through the repository's unchanged C converter."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

LCD_DIR = Path(__file__).resolve().parent
C_SOURCE = LCD_DIR.parent / 'teste' / 'txt_to_mif.c'
OPCODES = 16
NAME_WIDTH = 16


def read_operations(path: Path) -> dict[int, str]:
    """Accept one hex opcode per line; omitted or empty slots display spaces."""
    operations = {}
    # UTF-8 comments and a Windows UTF-8 BOM are allowed. Display text is ASCII.
    # Split only actual text lines, so vertical-tab/form-feed bytes inside a
    # name are rejected instead of silently becoming extra valid records.
    for number, line in enumerate(path.read_text(encoding='utf-8-sig').split('\n'), 1):
        line = line.lstrip(' \t')
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'([0-9A-Fa-f])(?:[ \t]+(.*))?', line)
        if not match:
            raise ValueError(f'Linha {number}: use um codigo hexadecimal 0-F, espaco e nome.')
        opcode = int(match[1], 16)
        if opcode in operations:
            raise ValueError(f'Linha {number}: codigo {opcode:X} repetido.')
        name = match[2] or ''
        if len(name) > NAME_WIDTH:
            raise ValueError(f'Linha {number}: nome com {len(name)} caracteres; o limite e 16.')
        if any(not 0x20 <= ord(character) <= 0x7E for character in name):
            raise ValueError(f'Linha {number}: o nome deve usar ASCII imprimivel, sem acentos ou controles.')
        operations[opcode] = name
    if not any(operations.values()):
        raise ValueError('Defina pelo menos uma operacao com nome.')
    return operations


def expected_rom(operations: dict[int, str]) -> bytes:
    return b''.join(operations.get(opcode, '').ljust(NAME_WIDTH).encode('ascii')
                    for opcode in range(OPCODES))


def verify_generated_mif(path: Path, expected: bytes) -> None:
    text = path.read_text(encoding='ascii')
    header, separator, body = text.partition('CONTENT BEGIN\n')
    settings = dict(re.findall(r'([A-Z_]+)=([A-Z0-9]+);', header))
    required = {'WIDTH': '8', 'DEPTH': '256', 'ADDRESS_RADIX': 'HEX', 'DATA_RADIX': 'HEX'}
    if not separator or settings != required or not body.endswith('END;\n'):
        raise ValueError('O conversor C gerou um cabecalho MIF inesperado.')
    entries = re.findall(r'^([0-9A-F]{2}) : ([0-9A-F]{2});$', body, re.M)
    if len(entries) != 256 or [int(address, 16) for address, _ in entries] != list(range(256)):
        raise ValueError('O conversor C nao gerou os 256 enderecos em ordem.')
    actual = bytes(int(value, 16) for _, value in entries)
    if actual != expected:
        raise ValueError('O MIF gerado diverge dos nomes ou do preenchimento de 16 caracteres.')


def generate(input_path: Path, output_path: Path, compiler: list[str] | None = None) -> dict[int, str]:
    operations = read_operations(input_path)
    if output_path.suffix.lower() != '.mif':
        raise ValueError('O arquivo de saida deve ter extensao .mif.')
    if output_path.resolve() in {input_path.resolve(), C_SOURCE.resolve(), (LCD_DIR/'control.mif').resolve()}:
        raise ValueError('Escolha uma saida que nao sobrescreva a entrada, o conversor ou control.mif.')
    command = compiler if compiler is not None else shlex.split(os.environ.get('CC', 'cc'))
    if not command:
        raise ValueError('Defina CC com um compilador C, como cc, gcc ou clang.')
    with tempfile.TemporaryDirectory(prefix='lcd_operations_') as temporary:
        folder = Path(temporary)
        binary_input = folder/'operations_binary.txt'
        converted = folder/'operations.mif'
        executable = folder/('txt_to_mif.exe' if os.name == 'nt' else 'txt_to_mif')
        binary_input.write_text(''.join(f'{opcode:04b} {name}\n'
                                        for opcode, name in sorted(operations.items()) if name), encoding='ascii')
        subprocess.run([*command, '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2',
                        str(C_SOURCE), '-o', str(executable)], check=True, capture_output=True, text=True)
        subprocess.run([str(executable), str(binary_input), str(converted)],
                       check=True, capture_output=True, text=True)
        verify_generated_mif(converted, expected_rom(operations))
        # Publish only a fully generated, independently checked image. Failure
        # before this point leaves an existing destination untouched.
        output_path.parent.mkdir(parents=True, exist_ok=True)
        mode = output_path.stat().st_mode & 0o777 if output_path.exists() else 0o644
        staged = None
        try:
            with tempfile.NamedTemporaryFile(prefix='.operations_', suffix='.mif',
                                             dir=output_path.parent, delete=False) as file:
                staged = Path(file.name)
                file.write(converted.read_bytes())
            staged.chmod(mode)
            os.replace(staged, output_path)
        finally:
            if staged is not None and staged.exists():
                staged.unlink()
    return operations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=LCD_DIR/'operations.txt')
    parser.add_argument('--output', type=Path, default=LCD_DIR/'operations.mif')
    parser.add_argument('--check', action='store_true', help='validar o mapa sem compilar nem escrever o MIF')
    args = parser.parse_args()
    try:
        operations = read_operations(args.input) if args.check else generate(args.input, args.output)
    except (OSError, UnicodeError, ValueError, subprocess.CalledProcessError) as error:
        print(f'Erro: {error}', file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr.strip(), file=sys.stderr)
        return 1
    count = sum(bool(name) for name in operations.values())
    print(f'OK: {count} nomes, {OPCODES} codigos de 4 bits, {NAME_WIDTH} caracteres por codigo.')
    if args.check:
        print('Validacao concluida; nenhum MIF foi alterado.')
    else:
        print(f'MIF gerado e conferido byte a byte: {args.output}')
        print('Recompile o projeto Quartus e use o novo SOF para atualizar a placa.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
