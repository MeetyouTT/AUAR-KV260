"""Check current source, installation receipts, package and report references."""
import hashlib
import json
from pathlib import Path
import re
import shutil
from urllib.parse import unquote, urlsplit
import zipfile

WORK=Path(__file__).resolve().parent
ROOT=Path('/home/ghmd/Win共享文件/共享文件夹/aura')
SHARE=ROOT/'report/display_coldboot_20261017'
EVIDENCE=Path('/home/ghmd/aura-asr-integration-20261016/evidence')
NAMES=['20261018T042245.939539Z-display-coldboot-readonly',
       '20261018T042411.183463Z-display-startup-inventory',
       '20261018T042705.608107Z-display-startup-install',
       '20261018T042856.255950Z-display-startup-verify']


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    responses=0;artifacts=0
    for name in NAMES:
        folder=EVIDENCE/name
        receipt=json.loads((folder/'result.json').read_text())
        assert receipt['complete'] and receipt['console_echo_restored']
        assert sha((folder/'source.py').read_bytes())==receipt['source_sha256']
        for row in receipt['commands']:
            data=(folder/(row['name']+'.output')).read_bytes()
            assert row['exit_code']==0 and len(data)==row['bytes'] and sha(data)==row['sha256']
            value=json.loads(data)
            for filename,item in value.get('artifacts',{}).items():
                actual=(folder/filename).read_bytes()
                assert len(actual)==item['bytes'] and sha(actual)==item['sha256']
                artifacts+=1
            responses+=1
    m=json.loads((WORK/'manifest.json').read_text())
    verify=json.loads((EVIDENCE/NAMES[3]/'response.json').read_text())
    install=json.loads((EVIDENCE/NAMES[2]/'response.json').read_text())
    assert install['status']=='INSTALLED_FOR_NEXT_START_CURRENT_UI_UNCHANGED'
    assert not install['cold_boot_verified'] and not install['physical_panel_verified']
    assert not verify['recovery_marker_exists']
    assert verify['supervisor_pid']==install['before']['supervisor_pid']
    assert verify['active_args']==install['before']['active_supervisor_args']
    for name,row in m['files'].items():
        assert verify['files'][name]==row['sha256']
        assert sha((ROOT/'scripts/board_ui_startup'/name).read_bytes())==row['sha256']
    assert sha(verify['installed_unit'].encode())==m['files']['aura-avatar-ui.service']['sha256']
    old=json.loads((EVIDENCE/NAMES[1]/'installed_config.json').read_text())
    new=json.loads((WORK/'candidate/config.json').read_text())
    assert old['gui_sha256']==new['gui_sha256']
    assert old['component_sha256']==new['component_sha256']
    for key in ('boot_id','supervisor_pid','gui_pid','active_supervisor_args','camera_pid','camera_epoch','protected'):
        assert install['before'][key]==install['after'][key]
    board_log=EVIDENCE/NAMES[3]/'board_display_tests.log'
    shutil.copy2(board_log,SHARE/board_log.name)
    for path in (WORK/'host_display_tests.log',board_log):
        text=path.read_text()
        assert re.search(r'Ran 17 tests in [0-9.]+s\s+OK\s*$',text)
        assert len(re.findall(r'^test_',text,re.M))==17
    build=json.loads((WORK/'build_validation.json').read_text())
    blob=Path(build['zip']).read_bytes()
    assert sha(blob)==build['zip_sha256'] and len(blob)==build['zip_bytes']
    with zipfile.ZipFile(Path(build['zip'])) as archive:
        assert archive.testzip() is None
        for name,row in m['files'].items():
            data=archive.read(name);assert sha(data)==row['sha256'] and len(data)==row['bytes']
    (SHARE/'installation.json').write_text(json.dumps(install,ensure_ascii=False,indent=2)+'\n')
    (SHARE/'display_inspection.json').write_bytes((EVIDENCE/NAMES[0]/'response.json').read_bytes())
    count=0
    for doc in (SHARE/'REPORT.md',ROOT/'docs/BOARD_UI_STARTUP.md',ROOT/'scripts/board_ui_startup/README.md',
                Path('/home/ghmd/AMD_Smart/logs/daily/2026-10-17-DISPLAY-COLDBOOT-FIX.md')):
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',doc.read_text()):
            parsed=urlsplit(target)
            if parsed.scheme or not parsed.path:continue
            path=Path(unquote(parsed.path))
            if not path.is_absolute():path=doc.parent/path
            assert path.exists(),(doc,target)
            count+=1
    result={'status':'PASS_INSTALLED_NEXT_START_ONLY_COLD_BOOT_NOT_VERIFIED',
            'release_id':m['release_id'],'uart_responses_verified':responses,
            'uart_artifacts_verified':artifacts,'host_tests':17,'board_software_tests':17,
            'display_commands_in_tests':'fixtures','deployment_files_verified':len(m['files']),
            'preserved_component_hashes':len(new['component_sha256']),
            'current_ui_and_camera_restarted':False,'real_display_output_cycled_this_turn':False,
            'cold_boot_verified':False,'physical_panel_verified':False,
            'local_document_links_verified':count,'evidence_folders':NAMES,
            'package_sha256':build['zip_sha256']}
    data=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    (SHARE/'validation.json').write_text(data);(WORK/'validation.json').write_text(data)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
