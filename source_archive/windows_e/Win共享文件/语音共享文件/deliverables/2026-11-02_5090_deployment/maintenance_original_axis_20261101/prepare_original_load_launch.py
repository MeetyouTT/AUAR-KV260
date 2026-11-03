"""Prepare the separate existing-client load call after confirmed physical unload."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
text=(HERE/'launch_original_remove.py').read_text(encoding='utf-8')
changes=[
 ("UNIT='aura-original-remove-903c-v1.service'","UNIT='aura-original-load-903c-v1.service'",1),
 ("TX/'remove.stdout.raw'","TX/'load.stdout.raw'",1),
 ("TX/'remove.stderr.raw'","TX/'load.stderr.raw'",1),
 ("CLIENT,'-remove','0'","CLIENT,'-load','aura-visual-servo-b4096-wide-v1'",2),
 ("'original_remove_slot0'","'original_load_original_wide'",1),
 ("TX/'remove-intent.json'","TX/'load-intent.json'",2),
 ("TX/'remove-submission.json'","TX/'load-submission.json'",1)]
for old,new,count in changes:
    assert text.count(old)==count,(old,text.count(old))
    text=text.replace(old,new)
old="assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\\0')==b'kv260-benchmark-b4096.bit.bin'"
assert text.count(old)==1
new="""assert not Path('/proc/device-tree/fpga-full/firmware-name').exists()
assert not list(Path('/sys/kernel/config/device-tree/overlays').iterdir())
assert not list(Path('/sys/class/drm').glob('renderD*'))
removed=show('aura-original-remove-903c-v1.service','InvocationID,ExecMainPID,ExecMainCode,ExecMainStatus,SubState,Job')
assert removed=={'InvocationID':'2f576a41a8f44a34b173cbca8305a82a','ExecMainPID':'79180','ExecMainCode':'1','ExecMainStatus':'0','SubState':'exited','Job':''}
assert (TX/'remove.stdout.raw').read_bytes()==b'remove from slot 0 returns: 0 (Ok)\\n' and not (TX/'remove.stderr.raw').read_bytes()
release=Path('/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c')
manifest_bytes=(release/'candidate-manifest.json').read_bytes()
assert hashlib.sha256(manifest_bytes).hexdigest()=='6a4b645a5bbfd35c9107976edf27886cf8e0c91e40f48be6f052a95e1172c1cf'
manifest=json.loads(manifest_bytes)
assert manifest['app']=='aura-visual-servo-b4096-wide-v1' and manifest['build_id']==0x10282601
assert len(manifest['runtime_files'])==4 and len(manifest['payload_files'])==3
assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected for path,expected in manifest['runtime_files'].items())
assert all(hashlib.sha256((release/'driver'/name).read_bytes()).hexdigest()==expected for name,expected in manifest['payload_files'].items())"""
text=text.replace(old,new)
target=HERE/'launch_original_load.py';assert not target.exists()
target.write_text(text,encoding='utf-8')

host=(HERE/'launch_remove_host.py').read_text(encoding='utf-8')
for old,new,count in [('remove_host_intent.json','load_host_intent.json',1),
    ('remove_job_submission.json','load_job_submission.json',1),
    ('launch_original_remove.py','launch_original_load.py',1),
    ('aura-original-remove-903c-v1.service','aura-original-load-903c-v1.service',1)]:
    assert host.count(old)==count
    host=host.replace(old,new)
host=host.replace("intent=HERE/'load_host_intent.json'", "assert json.loads((HERE/'remove_result_02.json').read_text(encoding='utf-8'))['board_result']['status']=='REMOVE_CONFIRMED_AND_ACTUAL_PLATFORM_UNLOADED'\nintent=HERE/'load_host_intent.json'")
target=HERE/'launch_load_host.py';assert not target.exists();target.write_text(host,encoding='utf-8')
print('Separate original load call prepared; no board command sent')
