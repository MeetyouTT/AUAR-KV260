import xml.etree.ElementTree as ET
from pathlib import Path

AUD = Path('/home/ghmd/kv260_readonly_audit_20260927_7sM1wd')
projects = [Path(x) for x in [
    '/home/ghmd/work/kv260_dpu',
    '/home/ghmd/work/kv260_dpu_b2304_uram',
    '/home/ghmd/kv260_clockfix_rebuild_20260926',
]]
with (AUD/'logs/source_refs.txt').open('w') as out:
    for root in projects:
        xpr = root/'kv260_dpu.xpr'
        tree = ET.parse(xpr)
        out.write(f'PROJECT {xpr}\n')
        repo = None
        for elem in tree.iter():
            if elem.tag == 'Option' and elem.attrib.get('Name') == 'IPRepoPath':
                repo = elem.attrib['Val'].replace('$PPRDIR', str(root))
                p = Path(repo).resolve()
                out.write(f'IP_REPO {p} exists={p.exists()}\n')
            if elem.tag == 'File' and 'Path' in elem.attrib:
                val = elem.attrib['Path']
                p = val.replace('$PSRCDIR', str(root/'kv260_dpu.srcs')).replace('$PGENDIR', str(root/'kv260_dpu.gen'))
                out.write(f'FILE {val} exists={Path(p).exists()} resolved={p}\n')
    repo = Path('/home/ghmd/work/dpu/DPUCZDX8G_ip_repo_VAI_v3.0/DPUCZDX8G_v4_1_0')
    comp = ET.parse(repo/'component.xml')
    missing = []
    count = 0
    for elem in comp.iter():
        if not elem.tag.endswith('}file'):
            continue
        for ch in elem:
            if ch.tag.endswith('}name') and ch.text:
                if '://' in ch.text:
                    break
                count += 1
                p = (repo/ch.text).resolve()
                if not p.exists():
                    missing.append(ch.text)
                break
    out.write(f'IP component.xml file references={count} missing={len(missing)}\n')
    for name in missing[:100]:
        out.write(f'IP_MISSING {name}\n')
