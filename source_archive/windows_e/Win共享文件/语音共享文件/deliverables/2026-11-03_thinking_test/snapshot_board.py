import hashlib, importlib.util, json, pathlib
here=pathlib.Path(__file__).resolve().parent
helper=here.parent/'2026-10-18_board_dialogue/board_ssh.py'
spec=importlib.util.spec_from_file_location('board_transport',helper)
transport=importlib.util.module_from_spec(spec); spec.loader.exec_module(transport)
source='''import hashlib,json,pathlib,subprocess
p=pathlib.Path("/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json")
cfg=json.loads(p.read_bytes()); aura=pathlib.Path(cfg["runtime"])/"aura"
paths=["board/runtime/board_dialogue.py","board/runtime/board_memory_policy.py","board/runtime/board_business.py","board/runtime/board_speaker_business.py","board/runtime/audio/board_dialogue_jobs.py","tools/board_business_gui.py","tools/model_inference_host.py","common/model_inference_wire.py","common/inference_output_contract.py"]
files={name:(aura/name).read_text() for name in paths if (aura/name).is_file()}
units=subprocess.check_output(["systemctl","show","aura-avatar-ui.service","--property=MainPID,ExecStart,Restart,KillMode,SendSIGKILL,TimeoutStopUSec,ActiveState,SubState,Job"],text=True)
print(json.dumps(dict(boot_id=pathlib.Path("/proc/sys/kernel/random/boot_id").read_text().strip(),startup_path=str(p),startup=cfg,startup_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),unit=units,files=files)))'''
result=json.loads(transport.ssh('python3 -B -',source,timeout=20))
(here/'baseline').mkdir(exist_ok=True)
for name,code in result.pop('files').items():
    out=here/'baseline'/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(code,encoding='utf-8',newline='')
(here/'BASELINE.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('boot_id','startup_path','startup_sha256','unit')},ensure_ascii=False))
