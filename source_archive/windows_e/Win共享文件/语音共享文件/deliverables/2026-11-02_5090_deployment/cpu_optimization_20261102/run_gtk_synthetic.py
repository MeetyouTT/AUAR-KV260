"""Run the independently hardened public-frame bench, never the production GUI."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
source=(HERE/'validation/gst_synthetic_compare_hardened.py').read_text(encoding='utf-8')
assert hashlib.sha256(source.encode()).hexdigest()=='a35e015752524e5ea353b1e999da792bc3ae5f4efac3e3fdac33c719b47df8c2'
prefix=r'''
import hashlib,os,subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='903cfade-b93c-48fa-804e-379be1967313'
unit=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=MainPID,ActiveState,Job'],capture_output=True,text=True,timeout=4)
assert unit.returncode==0
fields=dict(line.split('=',1) for line in unit.stdout.splitlines() if '=' in line)
assert fields['MainPID']=='0' and fields['ActiveState'] in ('inactive','failed') and not fields['Job']
root=Path('/proc/79866')
assert (root/'stat').read_text().rsplit(')',1)[1].split()[19]=='2265436'
assert hashlib.sha256((root/'cmdline').read_bytes()).hexdigest()=='acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
for root in Path('/proc').iterdir():
    if not root.name.isdigit():continue
    try:maps=(root/'maps').read_text()
    except OSError:continue
    assert 'libvsrv.so' not in maps and '/dev/mem' not in maps
os.nice(10)
'''
code=prefix+'\n'+source
helper=HERE.parent.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('gtk_public_bench_transport',helper)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
intent=HERE/'GTK_BENCH_HOST_INTENT.json';output=HERE/'GTK_SYNTHETIC_RESULT.json'
assert not intent.exists() and not output.exists()
with intent.open('x',encoding='utf-8') as stream:
    json.dump({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'collector_sha256_lf':hashlib.sha256(code.encode()).hexdigest(),
        'camera_or_screen_opened':False,'models_or_motion_requested':False,
        'input':'generated public color patterns','nice_increment':10},stream,indent=2)
try:
    value=json.loads(module.ssh('/usr/bin/python3 -B -I - --frames 30 --rounds 2 --sizes 568x300,587x440,640x480',code,timeout=80))
except Exception as exc:
    # Only public synthetic frame metadata or technical library errors exist here.
    with (HERE/'GTK_SYNTHETIC_FAILURE.txt').open('x',encoding='utf-8') as stream:
        stream.write(str(exc))
    raise
with output.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps({key:value.get(key) for key in ('status','duration_s','strict_visible_pixels_and_alpha_equal','performance_summary')}))
assert value['status']=='SYNTHETIC_COMPARE_PASS' and value['strict_visible_pixels_and_alpha_equal'] is True
