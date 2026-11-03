"""Safe default entry: source/assets metadata only. There is no --run mode.

Does not import GTK, open a model/player/microphone/store, call HTTP, inspect a
process or read private board metadata. Hardware publication is parent-owned.
"""
import ast
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parent


def elf_dependencies(raw):
    """Read ELF metadata as bytes; never execute/load the ARM library."""
    if raw[:6] != b'\x7fELF\x02\x01':
        raise ValueError('Expected reviewed little-endian ELF64 library')
    machine = struct.unpack_from('<H', raw, 18)[0]
    phoff = struct.unpack_from('<Q', raw, 32)[0]
    phsize, phcount = struct.unpack_from('<HH', raw, 54)
    segments = [struct.unpack_from('<IIQQQQQQ', raw, phoff+phsize*i) for i in range(phcount)]
    dynamic = next(row for row in segments if row[0] == 2)
    entries = []
    for pos in range(dynamic[2], dynamic[2]+dynamic[5], 16):
        tag, value = struct.unpack_from('<qQ', raw, pos)
        if tag == 0: break
        entries.append((tag, value))
    address = next(value for tag, value in entries if tag == 5)
    load = next(row for row in segments if row[0] == 1 and row[3] <= address < row[3]+row[5])
    offset = load[2]+address-load[3]
    libraries = []
    for tag, value in entries:
        if tag == 1:
            begin = offset+value
            libraries.append(raw[begin:raw.index(b'\0', begin)].decode('ascii'))
    return dict(machine=machine, architecture='AArch64' if machine == 183 else 'unexpected',
                needed=libraries, executed=False)


def verify():
    candidate = ROOT/'candidate'
    manifest = json.loads((candidate/'manifest.json').read_text(encoding='utf-8'))
    for relative, row in manifest['files'].items():
        path = candidate/relative
        if not path.resolve(strict=True).is_relative_to(candidate.resolve()) or path.is_symlink():
            raise ValueError('Package member escapes candidate')
        raw = path.read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Package member changed: '+relative)
        if relative.endswith('.py'):
            ast.parse(raw, filename=relative)
    # Public candidate assets only: preparing does not load the native library.
    sys.path.insert(0, str(candidate/'aura'))
    from tools.yuki_business_candidate import prepare_pair
    config = json.loads((candidate/'yuki_business.config.fragment.json').read_text(encoding='utf-8'))
    config['board_business'] = dict(enabled=True)  # Metadata, not the GUI factory.
    pair = prepare_pair(config, candidate/'aura')
    return dict(status='PUBLIC_SOURCE_CONTRACT_OK_NOT_ACTIVATED', candidate_revision=manifest.get('candidate_revision',1),
        manifest_sha256=hashlib.sha256((candidate/'manifest.json').read_bytes()).hexdigest(), files_checked=len(manifest['files']),
        python_ast_checked=sum(name.endswith('.py') for name in manifest['files']),
        pair=pair.status(), prompt_utf8_bytes=len(pair.selected_prompt.encode('utf-8')),
        native=elf_dependencies((candidate/'aura/tools/libaura_yuki.so').read_bytes()),
        services_called=False, device_opened=False, private_metadata_read=False, identity_database_read=False,
        note='No GUI/business runtime is constructed. Future full runtime initialization needs root review and explicit private configuration.')


if __name__ == '__main__':
    print(json.dumps(verify(), ensure_ascii=True, indent=2))
