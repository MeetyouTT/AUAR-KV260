"""Hash-pinned COPY/ADD transport; no output is used unless all bytes verify."""
import base64
import hashlib


def digest(data):
    return hashlib.sha256(data).hexdigest()


def apply_delta(base, patch, expected_target_sha256):
    if (patch.get('schema') != 'aura-copy-add-1' or patch['base_sha256'] != digest(base)
            or patch['base_size'] != len(base) or patch['target_sha256'] != expected_target_sha256
            or type(patch['target_size']) is not int or not 0 < patch['target_size'] <= 16 * 1024 * 1024):
        raise ValueError('Delta context differs from approved artifacts')
    out = bytearray()
    for op in patch['ops']:
        if not isinstance(op, list) or not op:
            raise ValueError('Invalid operation')
        if op[0] == 'copy' and len(op) == 3:
            offset, length = op[1:]
            if type(offset) is not int or type(length) is not int or offset < 0 or length <= 0 or offset + length > len(base):
                raise ValueError('Copy outside base')
            out.extend(base[offset:offset + length])
        elif op[0] == 'add' and len(op) == 2:
            out.extend(base64.b64decode(op[1], validate=True))
        else:
            raise ValueError('Unknown operation')
        if len(out) > patch['target_size']:
            raise ValueError('Target overflow')
    if len(out) != patch['target_size'] or digest(out) != expected_target_sha256:
        raise ValueError('Reconstructed target differs')
    return bytes(out)


def make_delta(base, target):
    width = 32
    index = {}
    for offset in range(0, len(base) - width + 1, width):
        block = base[offset:offset + width]
        positions = index.setdefault(block, [])
        if len(positions) < 3:
            positions.append(offset)
        elif offset != positions[-1]:
            positions[-1] = offset
    ops, literal = [], bytearray()
    position = copied = 0
    while position < len(target):
        candidates = index.get(target[position:position + width], []) if position + width <= len(target) else []
        best_offset, best_length = 0, 0
        for offset in candidates:
            length = width
            limit = min(len(base) - offset, len(target) - position)
            while length + 4096 <= limit and base[offset + length:offset + length + 4096] == target[position + length:position + length + 4096]:
                length += 4096
            while length < limit and base[offset + length] == target[position + length]:
                length += 1
            if length > best_length:
                best_offset, best_length = offset, length
        if best_length >= 64:
            if literal:
                ops.append(['add', base64.b64encode(literal).decode()])
                literal.clear()
            ops.append(['copy', best_offset, best_length])
            position += best_length
            copied += best_length
        else:
            literal.append(target[position])
            position += 1
    if literal:
        ops.append(['add', base64.b64encode(literal).decode()])
    patch = {'schema': 'aura-copy-add-1', 'base_size': len(base), 'base_sha256': digest(base),
             'target_size': len(target), 'target_sha256': digest(target), 'ops': ops}
    if apply_delta(base, patch, digest(target)) != target:
        raise RuntimeError('Host roundtrip failed')
    return patch, copied
