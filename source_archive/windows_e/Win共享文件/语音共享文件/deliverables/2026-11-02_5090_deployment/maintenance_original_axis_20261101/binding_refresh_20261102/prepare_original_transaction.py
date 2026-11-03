"""Rebase the existing original transaction, preserving its write and rollback code."""
import ast,datetime,difflib,hashlib,json,os
from pathlib import Path
L=Path(__file__).parent;M=L.parent;B=M.parent;J=B/'joint_acceptance_180s_20261102'
load=lambda p:json.loads(Path(p).read_bytes())
g=load(J/'AXIS_BINDING_REFRESH_PHASE_HANDOFF.json');probe=load(L/'preflight.json');axis=load(J/'AXIS_WIDE_IDSTOP_RESULT.json')
original=(M/'reconnect_original_axis_config.py').read_text(encoding='utf-8')
assert hashlib.sha256((M/'reconnect_original_axis_config.py').read_bytes()).hexdigest()=='9aed06263338fbf1fd44e3491c46dbd1ad29001ddade7fc7a8437ce193ba09b2'
text=original
def change(before,after,count=1):
    global text
    assert text.count(before)==count,(before,text.count(before),count)
    text=text.replace(before,after)
change("BOOT='903cfade-b93c-48fa-804e-379be1967313'",'BOOT='+repr(g['boot_id']))
change("EXPECTED='3f5e81abc20ce5169ac91ae302611cba8958175a6a2bdb615fd9b858353120d5'",'EXPECTED='+repr(g['startup_before_sha256']))
change("BASE=Path('/home/root/aura-5090-recovery-20261102-903cfade')","BASE=Path('/home/root/aura-5090-recovery-20261102-a6d4a069')")
change("TX=BASE/'original-follow-current-v1'","TX=BASE/'original-follow-binding-185858-v1'")
change("RESTORE=BASE/'original-axis-restore-v1'",'RESTORE=Path('+repr(axis['board_transaction_root'])+')')
change("CONTROL=Path('/home/root/aura-pan-wide-20261028/control-10282601')",'CONTROL=Path('+repr(probe['pan']['face']['release_root'])+')')
change('d68bc147f22f5ab23bc60f0c2762af4bcd7b64340953e9c948e28ffa6b80f7ca',probe['context']['fdt_sha256'])
change('79866',str(g['camera_owner']['pid']),count=4)
change('2265436',g['camera_owner']['birth_ticks'],count=2)
change('5c8206ee626c91c9f311ee870245813e169ac14e554e2579554c74489066f562',probe['pan']['face']['manifest_sha256'])
change('a329dcb4ef7d701a659d949a8739b0d7bad3789d0ecbad74c2ec8b77e9c70152',probe['old_manual_release_sha256'])
change("assert old_zone['left_camera_ratio']==.1 and old_zone['right_ratio']==.7158253629442671","assert old_zone==PB['zone']")
change('now=datetime.datetime.now(datetime.timezone.utc).isoformat()',"now=PB['host_prepared_utc']")
change("user_instruction_quote='转轴我已经接好了，按照原来Ubuntu上写的；按照原来已优化的直接进行人脸跟随，我一次性调试'","user_instruction_quote='转轴解冻，我要进行整个流程的验收'")
change("current_user_mount_and_power_confirmation='安装未动，可观察且空间充足；大致在中间且相机朝前；转轴动力已接好'","current_user_mount_and_power_confirmation='转轴动力保持断开；沿用本轮已确认的安装未动、可观察、左右空间及线缆余量充足',\n    motor_power_state='OFF',motor_power_off_is_human_confirmation=True")
change("receipt={'schema':'aura-original-axis-current-config-1'","receipt={'schema':'aura-original-axis-current-config-1'")
needle='if not APPLY:\n    print(json.dumps(receipt));raise SystemExit(0)'
extra="""assert all(new_startup['component_sha256'][k]==v for k,v in pins.items() if k not in receipt['changed_component_keys'])
receipt.update(component_sha256=new_startup['component_sha256'],unchanged_component_count=377,
    new_manual_release_path=str(TX/'manual-release/release.json'),new_context_path=str(RESTORE/'wide-context.json'),
    original_direction_predecessor_sha256=sha(direction_path),original_authorization_predecessor_sha256=old_release['authorization']['sha256'],
    motor_power_state='OFF',selected27_and_four_core_preserved=True,
    BIND_sent=False,REFERENCE_sent=False,STOP_sent=False,MMIO_opened=False,
    phase_grant_sha256='7b1f3f1de563a8488f0692e4f7fb29d559a9e82aa79d7016fed45f9aaf5e62dc')
"""
change(needle,extra+needle)
PB={'zone':probe['zone'],'host_prepared_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
prefix='PB=json.loads('+repr(json.dumps(PB))+')\n'
# The same original fresh metadata probe runs before either dry-run or apply.
pre=(L/'preflight.py').read_text(encoding='utf-8')
assert pre.count('print(json.dumps(')==1
pre=pre.rsplit('print(json.dumps(',1)[0]
pre+='assert sha(S)==G["startup_before_sha256"]\n'
prefix=pre+'\n'+prefix
for apply,step in [(False,'dryrun'),(True,'apply')]:
    code=text.replace("APPLY=sys.argv[1:]==['--apply-original-axis-config']",'APPLY='+repr(apply))
    source=prefix+code
    tree=ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='run':
            for arg in node.args:
                assert not any(isinstance(n,ast.Constant) and n.value in ('start','stop','restart','reboot','loadapp','unloadapp') for n in ast.walk(arg))
    with (L/(step+'.py')).open('x',encoding='utf-8',newline='\n') as f:f.write(source)
with (L/'original_transaction_rebase.diff').open('x',encoding='utf-8',newline='\n') as f:f.write(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='original_reconnect',tofile='fresh_phase_reconnect')))
print(json.dumps({'prepared':True,'original_transaction_sha256':'9aed06263338fbf1fd44e3491c46dbd1ad29001ddade7fc7a8437ce193ba09b2','write_replace_rollback_functions_preserved':True,'step_scripts_compiled':True}))
