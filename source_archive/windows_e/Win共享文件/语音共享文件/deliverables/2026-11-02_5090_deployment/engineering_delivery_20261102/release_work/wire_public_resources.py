from common import *
release_module='''"""Verify the public KV260 inputs in the archive or in an offline rootfs."""
import hashlib
import importlib.util
import json
from pathlib import Path


def verify_public_files(root, staged=None):
    def load(path):
        return json.loads(path.read_text(encoding='utf-8-sig'))

    def need(value, message):
        if not value:
            raise ValueError(message)

    def resolve(source, destination):
        if staged is None:
            return root / source
        return staged / destination.lstrip('/')

    meta = load(root / 'board/config/public_board_resources.json')
    plan = {row['destination']: row['source'] for row in load(root / 'board/config/deployment_files.json')}
    files = meta['files']
    for destination, row in files.items():
        need(destination.startswith('/') and '..' not in Path(destination).parts, 'Invalid board path')
        need(plan.get(destination) == row['source'], 'Deployment source differs: ' + destination)
        actual = resolve(row['source'], destination)
        need(actual.is_file() and actual.stat().st_size == row['bytes'], 'Missing public file: ' + destination)
        need(hashlib.sha256(actual.read_bytes()).hexdigest() == row['sha256'], 'Public file differs: ' + destination)
    for destination, digest in load(root / 'board/config/image_inputs.json')['files'].items():
        need(files[destination]['sha256'] == digest, 'Historical board pin differs: ' + destination)
    checked = {path for rule in meta['camera_prestart'] for path in rule['paths']}
    need(checked <= files.keys() and len(checked) == meta['camera_prestart_unique_paths'], 'Camera prestart inputs incomplete')
    for service, sequence in meta['systemd_order'].items():
        prefix = '/etc/systemd/system/' + service
        need(prefix in files and all(p.startswith(prefix + '.d/') and p in files for p in sequence), 'Unit override missing: ' + service)

    gui = meta['gui_file']
    gui_file = resolve(gui['source'], gui['destination'])
    need(hashlib.sha256(gui_file.read_bytes()).hexdigest() == gui['sha256'], 'GUI configuration differs')
    config = load(gui_file)
    fixed = load(root / 'data/reference/public_feedback.json')
    binding = {'path': fixed['manifest'], 'sha256': fixed['manifest_sha256']}
    need(config['formal_static_cues'] == binding, 'GUI cue binding differs')
    business = config['board_business']
    need((business['feedback_manifest'], business['feedback_manifest_sha256']) == (binding['path'], binding['sha256']), 'Business cue binding differs')
    manifest = files[binding['path']]
    need(manifest['sha256'] == binding['sha256'], 'Cue manifest pin differs')
    assets = load(resolve(manifest['source'], binding['path']))['assets']
    expected = {a['name']: a for a in fixed['assets']}
    need(set(assets) == set(expected) == {'arrival', 'invitation', 'thinking'}, 'Missing fixed prompt')
    # Run the same PCM and metadata validation used by the released audio provider.
    spec = importlib.util.spec_from_file_location('auar_public_voice_wire', root / 'src/software/common/voice_wire.py')
    wire = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wire)
    for name, item in assets.items():
        ref = expected[name]
        target = item['path']
        need(target == ref['path'] and files[target]['sha256'] == ref['sha256'], 'Wrong cue identity: ' + name)
        blob = resolve(files[target]['source'], target).read_bytes()
        result = wire.wav_payload(item['metadata'], blob)
        need(result['reply_text'] == ref['text'] and result['duration_seconds'] * 24000 == ref['samples'], 'Wrong cue text or duration: ' + name)
    print('Public KV260 files verified: {} destinations, {} camera prestart checks, 3 original fixed WAVs'.format(len(files), len(meta['camera_prestart'])))
'''
(ROOT/'build/scripts/public_board_files.py').write_bytes(release_module.encode())
f=ROOT/'build/scripts/verify.py';s=f.read_text(encoding='utf8')
if 'from public_board_files import' not in s:
    s=s.replace('import statistics','import statistics\nfrom public_board_files import verify_public_files')
    mark="    print('PASS | {} release files"
    assert mark in s;s=s.replace(mark,"    verify_public_files(ROOT)\n"+mark)
    f.write_bytes(s.encode())
f=ROOT/'board/scripts/stage.py';s=f.read_text(encoding='utf8')
if 'from public_board_files import' not in s:
    mark='from verify import main as verify_release';s=s.replace(mark,mark+'\nfrom public_board_files import verify_public_files')
    mark="    print('PASS: offline rootfs staging:',out)";assert mark in s;s=s.replace(mark,"    verify_public_files(ROOT, staged=out)\n"+mark)
    f.write_bytes(s.encode())
f=ROOT/'board/readme.md';s=f.read_text(encoding='utf8')
key='板上固定提示音及已保存的路径'
if key in s:s=s.split(key)[0].rstrip()+'\n'
if '## 板上原件与归位检查' not in s:
    s+='''
## 板上原件与归位检查

三段系统提示音原件和 feedback.json 位于 board/public_cues。角色界面与语音业务都固定绑定这份清单。默认暂存命令将它们放回原板路径；校验会核对两处配置、清单 SHA、固定台词、采样数和音频数据。三段均为原选定音色的 24 kHz 单声道 PCM16，分别为问候 2.66 秒、邀请 2.28 秒和思考 1.79 秒。

board/config/image_inputs.json 中原先需从原卡补取的 12 个文件已全部收录，包括 7 项相机历史校验文件和现役原生算子共享库。两个 AArch64 共享库的原件位于 board/camera_binaries。board/systemd 保留界面和相机服务本体及两项服务实际加载的 56 份追加配置。board/config/public_board_resources.json 记录原路径、SHA 和加载顺序，并列出相机服务启动前实际核验的 20 组输入。data/reference/public_feedback.json 是历史生成回执；本轮取件和解包复验记录在交付目录的 verification 中。

普通电脑按本页第一条暂存命令即可还原这些文件。若另有匹配的原卡镜像，--image-root /mnt/kv260-original 可附加比对 12 个历史哈希。真实目标上的摄像头需重新绑定本次开机信息，个人数据初始化按本页的实机步骤进行。
'''
    f.write_bytes(s.encode())
f=ROOT/'report/release_status.md';s=f.read_text(encoding='utf8')
old='原机专属文件的迁移入口见 board/readme.md。'
if old in s:
    s=s.split(old)[0].rstrip()+'\n\n本轮已从 KV260 只读取回 12 个发布清单文件的原件，包括三段固定提示音及清单、7 项相机历史校验文件和现役原生算子库。两项服务的公开配置按原加载顺序入包；20 道相机启动前文件检查的依赖已按板端哈希归位。board/config/public_board_resources.json 列出路径、来源和 SHA。实机整机冷启动及三分钟协同的验收范围沿用上表。\n'
    f.write_bytes(s.encode())
f=ROOT/'README.md';s=f.read_text(encoding='utf8')
if 'board/public_cues' not in s:
    s+='\n原板的问候、邀请、思考音频和原运行清单位于 board/public_cues。主包包含界面及相机的公开启动配置、现役相机原生库和相机启动前的校验文件。执行上述低核检查时会验证它们的 SHA 与提示音绑定。部署到离线暂存树时会再次核对实际落盘位置。\n'
    f.write_bytes(s.encode())
print('runtime verification and board docs updated')
