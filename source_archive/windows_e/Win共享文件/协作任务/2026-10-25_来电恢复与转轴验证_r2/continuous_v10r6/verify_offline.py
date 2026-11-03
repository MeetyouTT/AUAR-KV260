"""Verify an offline Linux x86_64 snapshot. Never contacts a board/service."""
import argparse,hashlib,json,platform,subprocess,sys,tempfile
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parent
    if platform.machine() not in ('x86_64','AMD64') or platform.system()!='Linux':
        raise RuntimeError('This host-only verification bundle needs Linux x86_64')
    manifest=json.loads((root/'OFFLINE_PACKAGE_MANIFEST.json').read_text())
    checked=0
    for name,digest in manifest['files'].items():
        path=(root/name).resolve();path.relative_to(root.parent)
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Snapshot changed: '+name)
        checked+=1
    tests=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(root),'-p','test_*.py'],
        capture_output=True,text=True,timeout=30)
    if tests.returncode:raise RuntimeError(tests.stderr[-4000:])
    for path in root.glob('*.py'):compile(path.read_text(),str(path),'exec')
    with tempfile.TemporaryDirectory(prefix='aura-pan-offline-') as tmp:
        reports={}
        for name,controller in [('baseline',root.parent/'continuous_v9'),('candidate',root)]:
            output=Path(tmp)/(name+'.json')
            subprocess.run([sys.executable,str(root/'replay_scenarios.py'),'--controller-root',str(controller),
                '--output',str(output)],check=True,capture_output=True,text=True,timeout=30)
            reports[name]=json.loads(output.read_text())
    before={x['name']:x for x in reports['baseline']['scenarios']}
    after={x['name']:x for x in reports['candidate']['scenarios']}
    for side in ['right','left']:
        assert before[side+'_single_inside']['maximum_displacement_us']==18
        assert after[side+'_single_inside']['maximum_displacement_us']==3
    assert after['stable_return_allows_later_correction']['arms']==1
    assert after['stable_return_allows_later_correction']['maximum_displacement_us']==12
    assert after['brief_refresh_without_deadline_extension']['active']
    for name in ['refresh_never_renews_frozen_source','no_new_frames_stop','no_target_stop','multiple_faces_stop',
                 'new_boot_is_rejected','body_is_rejected','old_anchor_cannot_use_full_image_lease']:
        assert not after[name]['active'],name
    assert after['new_boot_is_rejected']['fatal'] and after['body_is_rejected']['fatal']
    assert all(x['maximum_anchor_overrun_ms']==0 for x in after.values())
    assert all(x['closed_stopped'] for x in after.values())
    result=dict(status='OFFLINE_VERIFICATION_PASS',scope='host command math and fake device only',
        files_checked=checked,software_test_summary=tests.stderr.strip(),scenario_pairs=len(after),
        reports=reports,board_accessed=False,MMIO_opened=False,deployed=False,physical_follow_validated=False)
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(status=result['status'],files_checked=checked,scenario_pairs=len(after),
        board_accessed=False,output=str(a.output))))


if __name__=='__main__':main()
