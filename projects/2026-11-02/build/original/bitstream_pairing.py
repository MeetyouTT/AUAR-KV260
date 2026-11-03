"""Compare Xilinx .bit configuration data while recording exporter timestamps."""
import hashlib


def parse_bit(data):
    offset = 0

    def take(count):
        nonlocal offset
        value = data[offset:offset + count]
        if len(value) != count:
            raise ValueError('Truncated bitstream')
        offset += count
        return value

    def u16():
        return int.from_bytes(take(2), 'big')

    magic = take(u16())
    if magic != b'\x0f\xf0\x0f\xf0\x0f\xf0\x0f\xf0\x00' or u16() != 1:
        raise ValueError('Unsupported bitstream header')
    tag = take(1)
    headers = {}
    while tag != b'e':
        if tag not in (b'a', b'b', b'c', b'd') or tag.decode() in headers:
            raise ValueError('Unknown or duplicate bitstream header tag')
        headers[tag.decode()] = take(u16()).rstrip(b'\0').decode('ascii')
        tag = take(1)
    if set(headers) != {'a', 'b', 'c', 'd'}:
        raise ValueError('Missing bitstream header fields')
    payload = take(int.from_bytes(take(4), 'big'))
    if not payload or offset != len(data):
        raise ValueError('Empty configuration payload or trailing bytes')
    return headers, payload


def check_pairing(original, embedded):
    a, payload_a = parse_bit(original)
    b, payload_b = parse_bit(embedded)
    if a['a'] != b['a'] or a['b'] != b['b']:
        raise ValueError('XSA bitstream design/device differs')
    if payload_a != payload_b:
        raise ValueError('XSA FPGA configuration payload differs')
    digest = lambda value: hashlib.sha256(value).hexdigest()
    return {'original_headers': a, 'embedded_headers': b,
            'changed_header_fields': [key for key in a if a[key] != b[key]],
            'original_sha256': digest(original), 'embedded_sha256': digest(embedded),
            'configuration_payloads_byte_identical': True,
            'configuration_payload_sha256': digest(payload_a), 'configuration_payload_bytes': len(payload_a)}
