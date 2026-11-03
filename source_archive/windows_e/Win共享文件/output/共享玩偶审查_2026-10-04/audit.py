import ast
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

ROOT = Path('E:/项目/共享文件夹/aura')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['TEMP'] = str(OUT)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
from PIL import Image, ImageDraw
import numpy as np
from board.interaction import avatar_assets as aa, avatar_board as ab, avatar_fsm as af, avatar_timing as at
from board.runtime.fsm import RuntimeFSM, RuntimeState
from board.runtime.events import EventType as E
from board.runtime.event_bus import EventEnvelope

result = {}
syntax = []
for sub in ['board', 'tools', 'tests', 'scripts']:
    for p in (ROOT / sub).rglob('*.py'):
        try:
            ast.parse(p.read_text(encoding='utf-8-sig'), filename=str(p))
        except Exception as ex:
            syntax.append({'file': str(p.relative_to(ROOT)), 'error': str(ex)})
result['syntax_errors'] = syntax
states = [s.name for s in RuntimeState]
schema = json.loads((ROOT / 'ui/ui_state.schema.json').read_text(encoding='utf-8'))['properties']['runtime_state']['enum']
result['states'] = {'runtime': states, 'schema': schema, 'presentation': af.all_states(), 'missing_schema': sorted(set(states)-set(schema)), 'board_export': [r['state'] for r in ab.state_rows()]}

def ev(t, p=None):
    return EventEnvelope(event_type=t, source='audit', created_at_ms=0, payload=p or {})

traces = {}
for name, events in {
    'normal_kws': [E.SCENE_PERSON_ENTER,E.AUDIO_KWS_DETECTED,E.AUDIO_VAD_END,E.DIALOGUE_RESPONSE_RECEIVED,E.AUDIO_PLAYBACK_STOP],
    'duplicate_vad': [E.SCENE_PERSON_ENTER,E.AUDIO_KWS_DETECTED,E.AUDIO_VAD_END,E.AUDIO_VAD_END,E.DIALOGUE_RESPONSE_RECEIVED,E.AUDIO_PLAYBACK_STOP],
    'button': [E.SCENE_PERSON_ENTER,E.BOARD_KEY_PRESSED,E.AUDIO_VAD_END,E.DIALOGUE_RESPONSE_RECEIVED,E.AUDIO_PLAYBACK_STOP],
    'wake_animation_finished': [E.AUDIO_KWS_DETECTED,E.AUDIO_PLAYBACK_STOP],
}.items():
    f = RuntimeFSM(publish_state_changes=False)
    traces[name] = []
    for t in events:
        before = f.rejected_count
        f.handle_event(ev(t, {'emotion':'neutral','reply_text':'hello'}))
        traces[name].append({'event':t,'state':f.state.name,'rejected': f.rejected_count>before})
result['fsm_traces'] = traces

tests = {'passed': [], 'failed': [], 'skipped': []}
for p in sorted((ROOT / 'tests').glob('test_*.py')):
    # Direct invocation is restricted to undecorated tests with no fixtures.
    source = p.read_text(encoding='utf-8-sig')
    tree = ast.parse(source)
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_') and not n.decorator_list and not n.args.args and not n.args.kwonlyargs]
    if not funcs:
        tests['skipped'].append({'module':p.stem,'reason':'requires test runner or fixtures'})
        continue
    try:
        m = importlib.import_module('tests.' + p.stem)
    except (Exception, SystemExit) as ex:
        tests['skipped'].append({'module':p.stem,'reason':str(ex)})
        continue
    for f in funcs:
        label = p.stem + '.' + f.name
        try:
            getattr(m, f.name)()
            tests['passed'].append(label)
        except (Exception, SystemExit) as ex:
            tests['failed'].append({'test':label,'error':str(ex),'trace':traceback.format_exc(limit=3)})
result['direct_tests'] = tests

assets = []
tiles = []
for d in sorted(aa.AVATAR_DIR.iterdir()):
    if not d.is_dir():
        continue
    paths = aa.list_frames(d)
    if not paths:
        continue
    meta = aa.read_meta(d)
    manifest = json.loads((d/'manifest.json').read_text(encoding='utf-8')) if (d/'manifest.json').exists() else {}
    entries = manifest.get('entries',[])
    bad = []
    for item in entries:
        name = item.get('file') or item.get('name') or item.get('path')
        if name:
            p = d/name
            if not p.exists() or (item.get('sha256') and hashlib.sha256(p.read_bytes()).hexdigest().lower()!=item['sha256'].lower()):
                bad.append(name)
    motion = aa.read_motion(d)
    segdata = aa.read_segments(d)
    seg = at.segments_from_dict(segdata)
    blob = d/'frames.rgb565'
    with Image.open(paths[0]) as im:
        size=im.size
    row={'asset':d.name,'frames':len(paths),'fps':aa.frames_fps(d),'size':size,'png_mib':round(sum(p.stat().st_size for p in paths)/2**20,2),'manifest_entries':len(entries),'bad_hash':bad,'motion_length':len(motion) if motion else None,'segments':segdata,'rgb565_exists':blob.exists(),'rgb565_bytes':blob.stat().st_size if blob.exists() else 0,'rgb565_expected':size[0]*size[1]*2*len(paths)}
    if seg:
        a,b=seg.loop
        ims=[np.asarray(Image.open(paths[i]).convert('RGBA').resize((96,100)),dtype=np.float32) for i in (a,b)]
        mask=ims[0][...,3]>100
        row['loop_pose_gap_rechecked']=round(float(np.abs(ims[0][...,:3].mean(2)-ims[1][...,:3].mean(2))[mask].mean()),3)
        row['segment_period_short']=round((sum((seg.frames()[0],seg.frames()[1]*3,seg.frames()[2]))/row['fps'])*1.5,3)
    assets.append(row)
    for idx in [0,len(paths)//2,len(paths)-1]:
        im=Image.open(paths[idx]).convert('RGBA')
        im.thumbnail((176,184))
        tile=Image.new('RGB',(196,212),(252,252,243))
        tile.paste(im,((196-im.width)//2,184-im.height),im)
        ImageDraw.Draw(tile).text((7,190),d.name+' '+str(idx),fill=(15,25,40))
        tiles.append(tile)
sheet=Image.new('RGB',(196*6,212*((len(tiles)+5)//6)),(228,229,230))
for i,t in enumerate(tiles):
    sheet.paste(t,((i%6)*196,(i//6)*212))
sheet.save(OUT/'asset_contact_sheet.png')
result['assets']=assets
old=json.loads((ROOT/'ui/avatar_board_manifest.json').read_text(encoding='utf-8'))
result['stale_board_manifest']=[{'state':r['state'],'recorded_frames':r['frames'],'actual_frames':len(aa.list_frames(aa.asset_dir(r['asset_resolved']))),'recorded_fps':r['fps'],'actual_fps':aa.frames_fps(aa.asset_dir(r['asset_resolved']))} for r in old['states'] if r['frames']!=len(aa.list_frames(aa.asset_dir(r['asset_resolved']))) or abs(r['fps']-aa.frames_fps(aa.asset_dir(r['asset_resolved'])))>0.01]

scripts=['verify_idle_alive.py','verify_loop_seam.py','verify_v2_actions.py','verify_v2_timing.py','verify_p01_sync.py','verify_v2_amp.py','build_motion_table.py','split_avatar_segments.py']
checks=[]
for name in scripts:
    p=subprocess.run([sys.executable,'-B',str(ROOT/'tools'/name)],cwd=ROOT,encoding='utf-8',errors='replace',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (OUT/(name+'.log')).write_text(p.stdout,encoding='utf-8')
    checks.append({'script':name,'exit':p.returncode,'summary':[l for l in p.stdout.splitlines() if any(x in l for x in ['RESULT','FAIL','需检查','Traceback','Error:'])]})
result['checks']=checks
p=subprocess.run([sys.executable,'-B',str(ROOT/'tools/demo_stage.py'),'--selftest','--backend','mock','--outdir',str(OUT/'stage')],cwd=ROOT,encoding='utf-8',errors='replace',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
(OUT/'demo_stage.log').write_text(p.stdout,encoding='utf-8')
result['stage_selftest']={'exit':p.returncode,'output':p.stdout}
(OUT/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'syntax_errors':syntax,'states':result['states'],'traces':traces,'direct_tests':{'passed':len(tests['passed']),'failed':tests['failed'],'skipped':tests['skipped']},'checks':checks,'stage_selftest':result['stage_selftest'],'asset_summary':[{k:v for k,v in r.items() if k not in ['segments','bad_hash']} for r in assets],'stale_board_manifest':result['stale_board_manifest']},ensure_ascii=False,indent=2))
