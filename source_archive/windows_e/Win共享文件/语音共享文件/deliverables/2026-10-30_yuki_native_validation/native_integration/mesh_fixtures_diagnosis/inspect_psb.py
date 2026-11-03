"""Read-only structural PSB v4 reader for generated diagnostic inputs.

This is a container inspector, not an E-mote evaluator. Resource tags are kept
separate from string values to detect accidental '#resource@N' string encoding.
"""
from pathlib import Path
import json
import struct
import sys


class Reader:
    def __init__(self, path):
        self.data = Path(path).read_bytes()
        if self.data[:4] != b'PSB\0':
            raise ValueError('not PSB')
        self.version = struct.unpack_from('<H', self.data, 4)[0]
        self.tags = {}
        bases, at = self.table(self.u32(12))
        parents, at = self.table(at)
        terminals, at = self.table(at)
        self.names = []
        for terminal in terminals:
            node, chars, visited = terminal, [], set()
            while node:
                if node in visited or node >= len(parents):
                    raise ValueError('invalid name trie')
                visited.add(node)
                parent = parents[node]
                char = node - bases[parent]
                if char:
                    chars.append(char)
                node = parent
            self.names.append(bytes(reversed(chars)).decode('utf8'))
        offsets, _ = self.table(self.u32(16))
        self.strings = []
        for offset in offsets:
            begin = self.u32(20) + offset
            end = self.data.index(0, begin)
            self.strings.append(self.data[begin:end].decode('utf8'))

    def u32(self, at):
        return struct.unpack_from('<I', self.data, at)[0]

    def table(self, at):
        cw = self.data[at] - 12
        if not 1 <= cw <= 4:
            raise ValueError('bad table count width')
        count = int.from_bytes(self.data[at+1:at+1+cw], 'little')
        width = self.data[at+1+cw] - 12
        if not 0 <= width <= 4 or (count and not width):
            raise ValueError('bad table value width')
        start = at + 2 + cw
        end = start + count * width
        if end > len(self.data):
            raise ValueError('truncated table')
        return [int.from_bytes(self.data[start+i*width:start+(i+1)*width], 'little')
                for i in range(count)], end

    def value(self, at, path=''):
        tag = self.data[at]
        self.tags[path] = {'offset': at, 'tag': hex(tag)}
        if tag == 1: return None
        if tag == 2: return False
        if tag == 3: return True
        if tag == 4 or tag == 29: return 0
        if 5 <= tag <= 12:
            return int.from_bytes(self.data[at+1:at+tag-3], 'little', signed=True)
        if 21 <= tag <= 28 or 34 <= tag <= 37:
            base = 21 if tag <= 24 else 25 if tag <= 28 else 34
            width = tag - base + 1
            index = int.from_bytes(self.data[at+1:at+1+width], 'little')
            if base == 21: return self.strings[index]
            return {'resource_kind': 'extra' if base == 34 else 'normal', 'index': index}
        if tag == 30: return struct.unpack_from('<f', self.data, at+1)[0]
        if tag == 31: return struct.unpack_from('<d', self.data, at+1)[0]
        if tag == 32:
            offsets, start = self.table(at+1)
            return [self.value(start+offset, path+'/'+str(i)) for i, offset in enumerate(offsets)]
        if tag == 33:
            keys, next_at = self.table(at+1)
            offsets, start = self.table(next_at)
            if len(keys) != len(offsets): raise ValueError('dict lengths mismatch')
            return {self.names[key]: self.value(start+offset, path+'/'+self.names[key])
                    for key, offset in zip(keys, offsets)}
        raise ValueError('unsupported PSB tag '+hex(tag))

    def inspect(self):
        value = self.value(self.u32(36))
        return {'version': self.version, 'root': value, 'resource_tags': {
            p: t for p, t in self.tags.items() if p.endswith('/rawMeshList') or p.endswith('/pixel')}}


if __name__ == '__main__':
    result = Reader(sys.argv[1]).inspect()
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    else:
        print(json.dumps(result, ensure_ascii=True, indent=2))
