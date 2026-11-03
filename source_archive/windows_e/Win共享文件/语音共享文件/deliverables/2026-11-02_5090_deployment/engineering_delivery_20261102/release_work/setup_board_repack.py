from common import *
copy(W/'replay_public_startup.py',ROOT/'board/scripts/replay_public_startup.py')
meta=load(ROOT/'board/config/public_board_resources.json')
cmds=load(W/'public_unit_effective.json')['aura-camera-ui.service']['ExecStartPre']
assert len(meta['camera_prestart'])==len(cmds)==20
for group,cmd in zip(meta['camera_prestart'],cmds):
    group['command_sha256']=hashlib.sha256(cmd.encode()).hexdigest()
save(ROOT/'board/config/public_board_resources.json',meta)
f=ROOT/'board/readme.md';s=f.read_text(encoding='utf8')
if 'replay_public_startup.py' not in s:
    s+='''\n若 Ubuntu 安装了 bubblewrap 且启用了用户命名空间，可对暂存树另外运行原版文件读取逻辑。该工具在只读隔离环境中执行相机服务的 20 道原始文件哈希检查，再用角色程序自身的两处提示音入口读取三段 WAV。结果写入外部 JSON 文件。\n\n~~~sh\npython3 -B board/scripts/replay_public_startup.py --rootfs "$HOME/auar-rootfs-01" --out "$HOME/auar-public-replay-01.json"\n~~~\n'''
    f.write_bytes(s.encode())
src=(W/'finalize.py').read_text(encoding='utf-8-sig')
marker="run('host_unit',prefix+"
src=src.replace(marker,"run('public_consumers',prefix+['board/scripts/replay_public_startup.py','--rootfs',q/'rootfs','--out',q/'public_runtime.json'],ext/'aura',env)\n"+marker)
src=src.replace("'rootfs_stage_without_audio':'PASS','suite'","'rootfs_stage_without_audio':'PASS','public_consumers':json.loads((q/'public_runtime.json').read_text()),'suite'")
src=src.replace("get('receipt.json',QA/'release_receipt.json')","get('public_runtime.json',QA/'board_public_runtime_replay.json')\nget('receipt.json',QA/'release_receipt.json')")
src=src.replace("['stage_rootfs','host_unit'", "['stage_rootfs','public_consumers','host_unit'")
(W/'finalize_board_edition.py').write_bytes(src.encode())
print(len(meta['files']),len(cmds),'public receipts enabled')
