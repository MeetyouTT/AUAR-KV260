"""Build ComfyUI API graphs only; never submits jobs or overwrites live assets."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools import gen_talking_variants as baseline

CATALOG = ROOT / 'docs' / '说话素材自然度提示词_v3.json'

def build(entry, common, seed, rest, held):
    first = rest if entry['first_anchor'] == 'rest' else held
    last = rest if entry['last_anchor'] == 'rest' else held
    prompt = common + ' ' + entry['prompt']
    graph = copy.deepcopy(baseline.wf(entry['id'].upper(), prompt, seed, length=39))
    graph['5']['inputs']['image'] = first
    if first != last:
        graph['6'] = {'class_type':'LoadImage', 'inputs':{'image':last}}
        graph['7']['inputs']['last_frame'] = ['6',0]
    graph['14']['inputs']['filename_prefix'] = 'AURA_NATURAL_V3_%s_s%d' % (entry['id'].upper(),seed)
    return graph

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--outdir',type=Path,required=True)
    ap.add_argument('--rest-reference',default='doll_green_9x16.png')
    ap.add_argument('--held-reference',default='doll_green_9x16_hold.png')
    ap.add_argument('--only',nargs='+')
    ap.add_argument('--seeds',nargs='+',type=int,default=[421001,421002,421003])
    args = ap.parse_args(argv)
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    entries = [e for e in catalog['assets'] if not args.only or e['id'] in args.only]
    if args.only and set(args.only) - {e['id'] for e in entries}:
        ap.error('unknown asset id')
    outputs=[]
    for e in entries:
        for seed in args.seeds:
            path=args.outdir / ('%s_s%d_api.json' % (e['id'],seed))
            if path.exists():
                ap.error('output exists; choose a new staging directory: %s' % path)
            graph=build(e,catalog['common_prompt'],seed,args.rest_reference,args.held_reference)
            outputs.append((path,graph))
    if (args.outdir/'workflow_manifest.json').exists():
        ap.error('manifest already exists; choose a new staging directory')
    args.outdir.mkdir(parents=True,exist_ok=True)
    records=[]
    for path,graph in outputs:
        raw=(json.dumps(graph,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
        path.write_bytes(raw)
        records.append({'file':path.name,'sha256':hashlib.sha256(raw).hexdigest(),
                        'seed':graph['11']['inputs']['noise_seed'],
                        'first_reference':graph['5']['inputs']['image'],
                        'last_reference':graph.get('6',graph['5'])['inputs']['image']})
    (args.outdir/'workflow_manifest.json').write_text(json.dumps({
        'status':'BUILT_NOT_SUBMITTED_NOT_GENERATED',
        'input_images_must_exist_in_comfyui':True,
        'catalog_sha256':hashlib.sha256(CATALOG.read_bytes()).hexdigest(),
        'files':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Built %d API graphs. No generation jobs submitted.' % len(outputs))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
