"""Read PE import names without loading or installing the candidate."""
from pathlib import Path
import struct

def imports(path):
    data = path.read_bytes()
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    count = struct.unpack_from('<H', data, pe + 6)[0]
    opt_size = struct.unpack_from('<H', data, pe + 20)[0]
    opt = pe + 24
    directory = opt + (112 if struct.unpack_from('<H', data, opt)[0] == 0x20b else 96)
    imp_rva = struct.unpack_from('<I', data, directory + 8)[0]
    sections = [struct.unpack_from('<IIII', data, opt + opt_size + i*40 + 8) for i in range(count)]
    def offset(rva):
        for virtual_size, va, raw_size, raw in sections:
            if va <= rva < va + max(virtual_size, raw_size): return raw + rva - va
        return rva
    pos = offset(imp_rva)
    result = []
    while imp_rva and any(data[pos:pos+20]):
        name = offset(struct.unpack_from('<I', data, pos+12)[0])
        result.append(data[name:data.index(b'\0', name)].decode())
        pos += 20
    return result

if __name__ == '__main__':
    root = Path(__file__).resolve().parent / 'runtime'
    for name in ('cosyvoice-cli.exe', 'cosyvoice.dll', 'ggml.dll', 'ggml-base.dll', 'onnxruntime.dll'):
        print(name, imports(root / name))
