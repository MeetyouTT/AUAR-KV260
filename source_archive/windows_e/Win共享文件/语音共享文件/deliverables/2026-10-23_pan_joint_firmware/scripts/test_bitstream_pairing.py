import unittest

from bitstream_pairing import check_pairing, parse_bit


def make_bit(*, time='06:00:00', device='xck26-sfvc784-2LV-c', payload=b'\xaa\x99\x55\x66configuration'):
    result = b'\x00\x09' + b'\x0f\xf0\x0f\xf0\x0f\xf0\x0f\xf0\x00' + b'\x00\x01'
    for tag, value in [('a', 'test_design'), ('b', device), ('c', '2026/10/24'), ('d', time)]:
        raw = value.encode() + b'\0'
        result += tag.encode() + len(raw).to_bytes(2, 'big') + raw
    return result + b'e' + len(payload).to_bytes(4, 'big') + payload


class PairingTests(unittest.TestCase):
    def test_timestamp_change_keeps_exact_configuration(self):
        result = check_pairing(make_bit(), make_bit(time='06:02:00'))
        self.assertTrue(result['configuration_payloads_byte_identical'])
        self.assertEqual(result['changed_header_fields'], ['d'])
        self.assertNotEqual(result['original_sha256'], result['embedded_sha256'])

    def test_changed_configuration_rejected(self):
        with self.assertRaisesRegex(ValueError, 'configuration payload differs'):
            check_pairing(make_bit(), make_bit(payload=b'different configuration'))

    def test_wrong_device_rejected(self):
        with self.assertRaisesRegex(ValueError, 'design/device differs'):
            check_pairing(make_bit(), make_bit(device='wrong_device'))

    def test_truncation_rejected(self):
        with self.assertRaises(ValueError):
            parse_bit(make_bit()[:-1])

    def test_trailing_data_rejected(self):
        with self.assertRaises(ValueError):
            parse_bit(make_bit() + b'extra')

    def test_corrupt_magic_rejected(self):
        value = bytearray(make_bit())
        value[2] ^= 1
        with self.assertRaisesRegex(ValueError, 'Unsupported bitstream header'):
            parse_bit(bytes(value))


if __name__ == '__main__':
    unittest.main()
