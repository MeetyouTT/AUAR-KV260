"""Create a checked byte-copy patch; source and destination are immutable files."""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path


def make_patch(old, new):
    anchors = {}
    for pos in range(0, len(old) - 15, 256):
        key = old[pos:pos + 16]
        values = anchors.setdefault(key, [])
        if len(values) < 4:
            values.append(pos)
    operations = []
    pos = literal_start = copied = 0

    def flush(end):
        if end > literal_start:
            operations.append(['literal', base64.b64encode(new[literal_start:end]).decode()])

    while pos + 16 <= len(new):
        matches = anchors.get(new[pos:pos + 16], ())
        best_offset = best_length = 0
        for offset in matches:
            limit = min(len(old) - offset, len(new) - pos)
            low, high = 16, min(32, limit)
            while high < limit and old[offset:offset + high] == new[pos:pos + high]:
                low, high = high, min(high * 2, limit)
            if old[offset:offset + high] == new[pos:pos + high]:
                low = high
            else:
                while high - low > 1:
                    middle = (high + low) // 2
                    if old[offset:offset + middle] == new[pos:pos + middle]:
                        low = middle
                    else:
                        high = middle
            if low > best_length:
                best_offset, best_length = offset, low
        if best_length >= 32:
            flush(pos)
            if operations and operations[-1][0] == 'copy' and operations[-1][1] + operations[-1][2] == best_offset:
                operations[-1][2] += best_length
            else:
                operations.append(['copy', best_offset, best_length])
            pos += best_length
            literal_start = pos
            copied += best_length
        else:
            pos += 1
    flush(len(new))
    result = {'format': 'aura-checked-byte-copy-patch-2', 'base_sha256': hashlib.sha256(old).hexdigest(),
              'result_sha256': hashlib.sha256(new).hexdigest(), 'result_bytes': len(new), 'operations': operations}
    return result, copied


def apply_patch(old, patch):
    if patch['format'] != 'aura-checked-byte-copy-patch-2' or hashlib.sha256(old).hexdigest() != patch['base_sha256']:
        raise ValueError('Patch base mismatch')
    parts = []
    total = 0
    for operation in patch['operations']:
        if operation[0] == 'copy':
            _, offset, size = operation
            if type(offset) is not int or type(size) is not int or not 0 <= offset < len(old) or not 0 < size <= len(old) - offset:
                raise ValueError('Invalid copy bounds')
            value = old[offset:offset + size]
        elif operation[0] == 'literal':
            value = base64.b64decode(operation[1], validate=True)
        else:
            raise ValueError('Unknown patch operation')
        total += len(value)
        if total > patch['result_bytes']:
            raise ValueError('Patch exceeds declared size')
        parts.append(value)
    value = b''.join(parts)
    if len(value) != patch['result_bytes'] or hashlib.sha256(value).hexdigest() != patch['result_sha256']:
        raise ValueError('Reconstructed model mismatch')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('result', type=Path)
    parser.add_argument('patch', type=Path)
    args = parser.parse_args()
    old, new = args.base.read_bytes(), args.result.read_bytes()
    patch, copied = make_patch(old, new)
    assert apply_patch(old, patch) == new
    encoded = gzip.compress(json.dumps(patch, separators=(',', ':')).encode(), mtime=0)
    args.patch.write_bytes(encoded)
    print(json.dumps({'copied_bytes': copied, 'literal_bytes': len(new) - copied,
                      'patch_bytes': len(encoded), 'operations': len(patch['operations']),
                      'reconstruction_verified': True}), flush=True)


if __name__ == '__main__':
    main()
