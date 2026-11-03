from common import *
items=load(P/'deliverables/2026-10-30_board_owner/integration/resume_yuki_run_assembly/actual_public_resources.json')['public_resources']
plan=load(ROOT/'board/config/deployment_files.json')
mapped={entry['destination']:entry['source'] for entry in plan}
def bind(a,dest,h):
    assert sha(ROOT/a)==h,(dest,a)
    if dest in mapped:
        assert sha(ROOT/mapped[dest])==h,dest
    else:
        plan.append(dict(source=a,destination=dest));mapped[dest]=a
for x in items:
    if not x['exists']:continue
    rel=x['relative']
    if rel.startswith('aura/'):
        a='src/software/'+rel[5:]
    elif 'xilan_live' in rel:
        a='board/stage_assets/'+rel.rsplit('/',1)[-1];copy(P/rel,ROOT/a)
    else:
        a='src/windows/'+rel
    for dest in [x['path'],x['resolved']]:bind(a,dest,x['sha256'])
    if 'reference_audio' in x:
        a='src/windows/'+str(PurePosixPath(rel).parent/x['reference_audio'])
        for dest in [str(PurePosixPath(x['path']).parent/x['reference_audio']),x['reference_audio_resolved']]:
            bind(a,dest,x['reference_audio_sha256'])
save(ROOT/'board/config/deployment_files.json',plan)
save(ROOT/'board/stage_assets/source.json',{'existing':[{k:x[k] for k in ['relative','sha256','bytes']} for x in items if x['exists']],'source':'2026-10-30-board-owner/actual_public_resources.json','reference_voice_sha256':next(x['reference_audio_sha256'] for x in items if 'reference_audio' in x)})
report=json.loads(ssh("from pathlib import Path\np=Path.home()/'aura-native-critical-20261024/v2-target-link-result.json'; print(p.read_text())"))['report']
n=ROOT/'src/camera/native_v2'; s=P/'deliverables/2026-10-24_native_critical_live/source/native'
for name,h in report['source_sha256'].items():
    assert sha(s/name)==h,(name,h);copy(s/name,n/name)
object_name='native_bridge.v2.aarch64.o'
remote_collect("import sys,tarfile\nfrom pathlib import Path\np=Path.home()/'aura-native-critical-20261024/schedule-integration/native_bridge.v2.aarch64.o'\nwith tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as t:t.add(p,arcname=p.name)",n)
assert sha(n/object_name)==report['object_sha256']
save(n/'historical_link.json',{k:report[k] for k in ['source_sha256','object_sha256','link_argv','link_exit_code','library_sha256','library_bytes']})
script=ROOT/'build/scripts/native_build.sh'
old=script.read_text(encoding='utf8')
mark='# The object above retains'
new='c++ -pthread -shared -Wl,-z,defs "$root/src/camera/native_v2/native_bridge.v2.aarch64.o" -o "$out/libaura_native_v2_candidate.so" -lvart-runner -lxir -ldl\n'
if new not in old:script.write_bytes(old.replace(mark,new+mark).encode())
pins=load(ROOT/'board/config/original_camera_inputs.json')
cue=load(ROOT/'data/reference/public_feedback.json')
op=load(ROOT/'src/camera/native_operator/board-build-report.json')
wanted=dict(pins['unresolved_from_offline_archives'])
wanted[op['library']]=op['library_sha256'];wanted.update({x['path']:x['sha256'] for x in cue['assets']});wanted[cue['manifest']]=cue['manifest_sha256']
save(ROOT/'board/config/image_inputs.json',{'purpose':'Allowlisted public files on a matching original rootfs. All SHA-256 values come from the recorded release.','files':wanted})
base=ROOT/'third_party_notices.md'
base.write_bytes(base.read_text(encoding='utf8').replace('、runtime_hashes.json','、data/reference/runtime_hashes.json').encode('utf8'))
print('hashed stage assets',sum(x['exists'] for x in items),'plus reference audio; original native-v2 source/object',len(report['source_sha256'])+1,'allowlisted files',len(wanted))