"""Boundary and output tests; all generated MIFs stay in temporary folders."""
from pathlib import Path
import tempfile
import unittest

from generate_operations import LCD_DIR, expected_rom, generate, read_operations, verify_generated_mif


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='lcd_map_test_')
        self.folder = Path(self.temporary.name)
        self.input = self.folder/'operations.txt'
        self.output = self.folder/'operations.mif'

    def tearDown(self):
        self.temporary.cleanup()

    def parse(self, text):
        self.input.write_text(text, encoding='utf-8')
        return read_operations(self.input)

    def test_high_opcode_boundary_and_padding(self):
        operations = self.parse('0 ADD\n6 OR\nf 1234567890ABCDEF\n9\n')
        generate(self.input, self.output)
        expected = expected_rom(operations)
        self.assertEqual(expected[0:16], b'ADD             ')
        self.assertEqual(expected[0x60:0x70], b'OR              ')
        self.assertEqual(expected[0xF0:0x100], b'1234567890ABCDEF')
        self.assertEqual(expected[0x90:0xA0], b'                ')
        verify_generated_mif(self.output, expected)

    def test_all_sixteen_codes(self):
        operations = self.parse(''.join(f'{opcode:X} OP{opcode:X}\n' for opcode in range(16)))
        generate(self.input, self.output)
        self.assertEqual(len(operations), 16)
        self.assertEqual(len(expected_rom(operations)), 256)

    def test_adding_names_preserves_the_nine_existing_slots(self):
        baseline = read_operations(LCD_DIR/'operations.txt')
        added = {**baseline, 9: 'LOAD', 10: 'STORE', 15: 'HALT'}
        self.parse(''.join(f'{opcode:X} {name}\n' for opcode, name in sorted(added.items())))
        generate(self.input, self.output)
        self.assertEqual(expected_rom(added)[:9*16], expected_rom(baseline)[:9*16])
        self.assertEqual(expected_rom(added)[0x90:0xA0], b'LOAD            ')
        self.assertEqual(expected_rom(added)[0xA0:0xB0], b'STORE           ')
        self.assertEqual(expected_rom(added)[0xF0:0x100], b'HALT            ')

    def test_duplicate_code_is_case_insensitive(self):
        with self.assertRaisesRegex(ValueError, 'repetido'):
            self.parse('a LOAD\nA STORE\n')

    def test_duplicate_empty_code_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'repetido'):
            self.parse('0 ADD\nF\nF HALT\n')

    def test_non_ascii_name_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'ASCII'):
            self.parse('0 ADIÇÃO\n')

    def test_control_byte_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'ASCII'):
            self.parse('0 ADD\x00HIDDEN\n')

    def test_embedded_tab_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'ASCII'):
            self.parse('0 ADD\tX\n')

    def test_control_separator_cannot_create_an_extra_record(self):
        for control in ('\v', '\f', '\x85'):
            with self.subTest(control=repr(control)), self.assertRaisesRegex(ValueError, 'ASCII'):
                self.parse(f'0 ADD{control}1 SUB\n')

    def test_seventeenth_character_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'limite e 16'):
            self.parse('0 1234567890ABCDEFG\n')

    def test_outside_four_bit_range_is_rejected(self):
        for code in ('10', 'G', '-1', '0000'):
            with self.subTest(code=code), self.assertRaisesRegex(ValueError, '0-F'):
                self.parse(f'{code} ADD\n')

    def test_empty_map_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'pelo menos uma'):
            self.parse('# Sem nomes\n0\nF\n')

    def test_bom_crlf_and_comment(self):
        operations = self.parse('\ufeff# Comentário permitido\r\n0 ADD\r\nF HALT\r\n')
        self.assertEqual(operations, {0: 'ADD', 15: 'HALT'})

    def test_bad_input_preserves_existing_output(self):
        self.output.write_bytes(b'previous image')
        self.input.write_text('0 1234567890ABCDEFG\n')
        with self.assertRaises(ValueError):
            generate(self.input, self.output)
        self.assertEqual(self.output.read_bytes(), b'previous image')

    def test_compiler_failure_preserves_existing_output(self):
        self.output.write_bytes(b'previous image')
        self.parse('0 ADD\n')
        with self.assertRaises(FileNotFoundError):
            generate(self.input, self.output, compiler=[str(self.folder/'absent_compiler')])
        self.assertEqual(self.output.read_bytes(), b'previous image')


if __name__ == '__main__':
    unittest.main()
