import hashlib
import gzip
import mmap
import re
import struct
import tarfile
from pathlib import Path

AUD = Path('/home/ghmd/kv260_readonly_audit_20260927_7sM1wd')
FIT = Path('/home/ghmd/work/petalinux-kv260-dpu/images/linux/image.ub')
ROOTFS = Path('/home/ghmd/work/petalinux-kv260-dpu/images/linux/rootfs.tar.gz')

with (AUD / 'logs/fit_members.txt').open('w') as out, FIT.open('rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
    magic, total, off_struct, off_strings, off_resv, version, last, boot, size_strings, size_struct = struct.unpack_from('>10I', mm, 0)
    out.write(f'FDT magic={magic:08x} total={total} structure={size_struct} strings={size_strings}\n')
    strings = mm[off_strings:off_strings+size_strings]
    pos = off_struct
    stack = []
    while pos < off_struct + size_struct:
        token = struct.unpack_from('>I', mm, pos)[0]
        pos += 4
        if token == 1:
            end = mm.find(b'\0', pos)
            stack.append(mm[pos:end].decode(errors='replace'))
            pos = (end + 4) & ~3
        elif token == 2:
            stack.pop()
        elif token == 3:
            length, nameoff = struct.unpack_from('>2I', mm, pos)
            pos += 8
            end = strings.find(b'\0', nameoff)
            name = strings[nameoff:end].decode(errors='replace')
            node = '/' + '/'.join(x for x in stack if x)
            if node.startswith('/images/') and name in ('description', 'type', 'arch', 'os', 'compression'):
                out.write(f'{node} {name}={mm[pos:pos+length].rstrip(bytes([0])).decode(errors="replace")}\n')
            if node.startswith('/images/') and name == 'data':
                sha = hashlib.sha256(mm[pos:pos+length]).hexdigest()
                out.write(f'{node} data offset={pos} size={length} sha256={sha}\n')
                if node == '/images/kernel-1':
                    try:
                        raw = gzip.decompress(mm[pos:pos+length])
                        out.write(f'{node} decompressed size={len(raw)} sha256={hashlib.sha256(raw).hexdigest()}\n')
                    except Exception as e:
                        out.write(f'{node} decompress ERROR={type(e).__name__}: {e}\n')
            pos = (pos + length + 3) & ~3
        elif token == 4:
            pass
        elif token == 9:
            break
        else:
            out.write(f'UNKNOWN_TOKEN={token} at {pos-4}\n')
            break

with (AUD / 'logs/rootfs_runtime.txt').open('w') as out, tarfile.open(ROOTFS, 'r:gz') as tf:
    names = tf.getnames()
    out.write(f'rootfs tar entries={len(names)}\n')
    for name in names:
        if re.search(r'(^|/)(libvart|libxir|libunilog|libtarget-factory|libxrt|libvart-dpu-runner).*\.so|/lib/modules/.*\.ko$|(^|/)etc/os-release$', name):
            member = tf.getmember(name)
            if name.endswith('.ko') and member.isfile():
                data = tf.extractfile(member).read()
                match = re.search(rb'vermagic=([^\0]+)', data)
                out.write(f'{name}\t{member.size}\tvermagic={match.group(1).decode(errors="replace") if match else "not-found"}\n')
            else:
                out.write(f'{name}\t{member.size}\t{member.type!r}\n')
