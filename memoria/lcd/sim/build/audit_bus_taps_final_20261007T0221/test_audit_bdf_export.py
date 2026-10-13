"""Targeted geometry/bit tests; never edits a circuit or simulation evidence."""
import unittest

from audit_bdf_export import Connectivity, expand_bits


class BusTapTests(unittest.TestCase):
    def test_bus_tap_selects_only_one_bit(self):
        net = Connectivity(
            [('bus', (0, 0), (0, 30)), ('wire', (0, 10), (10, 10))],
            [('bus', (0, 0), 'B[3:0]'), ('wire', (10, 10), 'B[1]')], [], {'B': 4})
        self.assertEqual(net.port_net((10, 10), 1), 'B[1]')
        self.assertEqual(net.port_net((0, 0), 4), 'B[3:0]')
        self.assertEqual([tap['member'] for tap in net.taps], ['B[1]'])

    def test_concat_preserves_order_and_distinct_taps(self):
        net = Connectivity(
            [('bus', (0, 0), (0, 30)), ('wire', (0, 10), (10, 10)),
             ('wire', (0, 20), (10, 20))],
            [('bus', (0, 0), '{OPCODE_Q[3:0],SLOT_Q[3:0]}'),
             ('wire', (10, 10), 'OPCODE_Q[2]'), ('wire', (10, 20), 'SLOT_Q[1]')],
            [], {'OPCODE_Q': 4, 'SLOT_Q': 5})
        self.assertEqual(expand_bits(net.port_net((0, 0), 8), net.widths),
                         ('OPCODE_Q[3]', 'OPCODE_Q[2]', 'OPCODE_Q[1]', 'OPCODE_Q[0]',
                          'SLOT_Q[3]', 'SLOT_Q[2]', 'SLOT_Q[1]', 'SLOT_Q[0]'))
        self.assertEqual(len(net.taps), 2)

    def test_tap_between_differently_sized_buses(self):
        net = Connectivity(
            [('bus', (0, 0), (0, 20)), ('bus', (20, 0), (20, 20)),
             ('wire', (0, 10), (20, 10))],
            [('bus', (0, 0), 'SLOT_Q[4:0]'), ('bus', (20, 0), 'SLOT_Q[3:0]'),
             ('wire', (0, 10), 'SLOT_Q[1]')], [], {'SLOT_Q': 5})
        self.assertEqual(len(net.taps), 2)
        self.assertEqual(net.port_net((0, 0), 5), 'SLOT_Q[4:0]')
        self.assertEqual(net.port_net((20, 0), 4), 'SLOT_Q[3:0]')

    def test_scalar_short_between_bus_bits_fails(self):
        with self.assertRaisesRegex(AssertionError, 'Conflicting net labels'):
            Connectivity(
                [('bus', (0, 0), (0, 20)), ('wire', (0, 10), (10, 10)),
                 ('wire', (10, 10), (20, 10))],
                [('bus', (0, 0), 'B[3:0]'), ('wire', (0, 10), 'B[0]'),
                 ('wire', (20, 10), 'B[1]')], [], {'B': 4})

    def test_out_of_bundle_tap_fails(self):
        with self.assertRaisesRegex(AssertionError, 'Tap is not a member'):
            Connectivity(
                [('bus', (0, 0), (0, 20)), ('wire', (0, 10), (10, 10))],
                [('bus', (0, 0), 'B[3:0]'), ('wire', (10, 10), 'B[4]')], [], {'B': 5})

    def test_wire_crossing_requires_junction(self):
        segments = [('wire', (-10, 0), (10, 0)), ('wire', (0, -10), (0, 10))]
        labels = [('wire', (-10, 0), 'A'), ('wire', (0, -10), 'B')]
        net = Connectivity(segments, labels, [], {'A': 1, 'B': 1})
        self.assertEqual(net.port_net((10, 0), 1), 'A')
        self.assertEqual(net.port_net((0, 10), 1), 'B')
        with self.assertRaisesRegex(AssertionError, 'Conflicting net labels'):
            Connectivity(segments, labels, [(0, 0)], {'A': 1, 'B': 1})

    def test_bus_wire_crossing_is_not_implicitly_a_tap(self):
        net = Connectivity(
            [('bus', (-10, 0), (10, 0)), ('wire', (0, -10), (0, 10))],
            [('bus', (-10, 0), 'B[3:0]'), ('wire', (0, -10), 'CLOCK')],
            [], {'B': 4, 'CLOCK': 1})
        self.assertEqual(net.taps, [])

    def test_reversed_bus_order_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'Conflicting net labels'):
            Connectivity([('bus', (0, 0), (0, 20))],
                         [('bus', (0, 0), 'B[3:0]'), ('bus', (0, 20), 'B[0:3]')],
                         [], {'B': 4})

    def test_unnamed_tap_is_not_guessed(self):
        with self.assertRaisesRegex(AssertionError, 'Unnamed scalar tap'):
            Connectivity([('bus', (0, 0), (0, 20)), ('wire', (0, 10), (10, 10))],
                         [('bus', (0, 0), 'B[3:0]')], [], {'B': 4})

    def test_bus_width_at_port_is_checked(self):
        net = Connectivity([('bus', (0, 0), (0, 20))],
                           [('bus', (0, 0), 'B[3:0]')], [], {'B': 4})
        with self.assertRaisesRegex(AssertionError, 'Port/bus width mismatch'):
            net.port_net((0, 0), 3)


if __name__ == '__main__':
    unittest.main()
