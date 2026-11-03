#!/usr/bin/env python3
"""Verify the packaged formal Yuki resources, pinned runtime references and native-library architecture."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def within(root, name):
    value = Path(name)
    if value.is_absolute() or '..' in value.parts:
        raise ValueError('Invalid relative resource path: '+name)
    path = root / value
    if any(p.is_symlink() for p in [path]+list(path.parents) if p == root or root in p.parents):
        raise ValueError('Redirected resource: '+name)
    resolved = path.resolve(strict=True)
    if root.resolve() not in resolved.parents or not resolved.is_file():
        raise ValueError('Resource outside runtime: '+name)
    return resolved


def evaluate(runtime=None):
    release = read(ROOT/'board/release_9a4f.json')
    deploy = read(ROOT/'board/deploy.json')
    manifest = read(ROOT/'src/assets/yuki/manifest.json')
    rows = release['runtime_files']
    checks = []
    def check(name, observed, expected):
        checks.append(dict(check=name, observed=observed, expected=expected, passed=observed==expected))
    def locate(name):
        row = rows[name]
        if runtime is not None:
            return within(runtime, name)
        if 'source' in row:
            return within(ROOT, row['source'])
        if 'template' in row and not deploy['templates'][row['template_key']]['site_fields']:
            return within(ROOT, row['template'])
        raise ValueError('Pinned reference is not packaged: '+name)
    check('selected_startup_sha256', manifest['baseline_startup_sha256'], release['baseline_startup_sha256'])
    check('resource_files', len(manifest['files']), 6)
    for item in manifest['files']:
        name = item['runtime_path']
        path = locate(name)
        check('size:'+name, path.stat().st_size, item['bytes'])
        check('sha256:'+name, sha(path), item['sha256'])
        check('runtime_binding:'+name, rows[name]['sha256'], item['sha256'])
        check('packaged_source:'+name, rows[name].get('source'), item['package_path'])
        check('external_input_removed:'+name, item['sha256'] in deploy['external_inputs'], False)
    selection = 'config/yuki_pair.formal.json'
    check('formal_selection_sha256', sha(locate(selection)), rows[selection]['sha256'])
    pair = read(locate(selection))
    check('formal_name', pair['identity']['formal_name'], '御笠雪妃')
    check('renderer_fps', pair['native_config']['fps'], 16)
    for name, expected in pair['runtime_pins'].items():
        check('formal_pin:'+name, sha(locate(name)), expected)
    profile = read(locate('assets/yuki/source_profile.json'))
    check('profile_id', profile['profile_id'], pair['identity']['render_profile_id'])
    for name, expected in profile['files'].items():
        check('profile_file:'+name, sha(locate('assets/yuki/'+name)), expected)
    for name in ['assets/yuki/model.runtime.json','assets/yuki/model.source.ems.json','assets/yuki/yuk_0.ems.resx.json']:
        check('json_object:'+name, isinstance(read(locate(name)),dict), True)
    texture = locate('assets/yuki/yuk_0.ems/tex-texture.png').read_bytes()
    if texture[:8] != bytes.fromhex('89504e470d0a1a0a'):
        raise ValueError('Texture is not PNG')
    position=8;chunks=0;ended=False;dimensions=None
    while position<len(texture):
        if position+12>len(texture):raise ValueError('Truncated PNG chunk')
        size=struct.unpack_from('>I',texture,position)[0]
        if position+12+size>len(texture):raise ValueError('Truncated PNG payload')
        kind=texture[position+4:position+8]
        data=texture[position+8:position+8+size]
        expected=struct.unpack_from('>I',texture,position+8+size)[0]
        if zlib.crc32(kind+data)!=expected:raise ValueError('Texture PNG CRC mismatch')
        if kind==b'IHDR':dimensions=list(struct.unpack_from('>II',data))
        chunks+=1;position+=12+size
        if kind==b'IEND':ended=True;break
    check('texture_png_complete', ended and position==len(texture), True)
    check('texture_dimensions', dimensions, manifest['texture_dimensions'])
    library=locate('tools/libaura_yuki.so').read_bytes()
    check('renderer_elf64_little_endian',library[:6].hex(),'7f454c460201')
    check('renderer_aarch64_machine',struct.unpack_from('<H',library,18)[0],183)
    return dict(status='PASS' if all(c['passed'] for c in checks) else 'FAIL',
                scope='OFFLINE_FORMAL_CHARACTER_RESOURCE_AND_REFERENCE_CHECK',
                resource_files=6,formal_reference_files=len(pair['runtime_pins'])+1,
                texture_dimensions=dimensions,png_chunks=chunks,checks=checks,
                runtime_checked=runtime is not None,board_rendered=False,
                native_library_executed=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,help='optional separately staged aura runtime')
    parser.add_argument('--out',type=Path,help='new JSON receipt outside the package and runtime')
    args=parser.parse_args()
    runtime=args.runtime.resolve(strict=True) if args.runtime else None
    out=args.out.resolve() if args.out else None
    if out and (out.exists() or out==ROOT or ROOT in out.parents or runtime and (out==runtime or runtime in out.parents)):
        parser.error('select a new receipt outside the package and checked runtime')
    result=evaluate(runtime)
    if out:
        out.parent.mkdir(parents=True,exist_ok=True)
        with out.open('x',encoding='utf-8') as stream:
            json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print(json.dumps(result if out is None else {k:v for k,v in result.items() if k!='checks'},ensure_ascii=False))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':
    try:
        sys.exit(main())
    except (OSError,ValueError,KeyError,struct.error) as exc:
        print('FAIL:',str(exc),file=sys.stderr);sys.exit(1)
