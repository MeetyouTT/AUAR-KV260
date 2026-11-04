"""Read KV260 telemetry over the project's existing authenticated SSH connection."""
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
import queue
import shlex
import subprocess
import threading
import time

INTERVAL = 5.0
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
PROBE = Path(__file__).with_name('runtime_board_probe.py')
# The SSH session owns the probe. Closing stdin ends the remote sampling loop.
BOOTSTRAP = """import json,sys
stream=sys.stdin.buffer
size=int(stream.readline())
assert 0 < size <= 65536
scope={'__name__':'runtime_probe'}
exec(compile(stream.read(size),'<aura-runtime-observer>','exec'),scope)
for command in stream:
    if command != b'S\\n': break
    print(json.dumps(scope['snapshot'](),ensure_ascii=True,separators=(',',':')),flush=True)
"""

ROLE_NAMES = {
    'camera': '相机与视觉引擎', 'supervisor': '界面启动与监督', 'gui': '角色界面与对话业务',
    'frontend': '音频前端', 'capture': '麦克风采集', 'playback': 'GStreamer 播放',
    'follow': '连续人脸跟随', 'manual': '手动转轴', 'editor': '人脸边界编辑',
    'auxiliary': '项目辅助进程', 'display': '显示与桌面', 'fabric': 'FPGA 固件管理',
    'sound': '系统音频',
}


def percentage(delta, total):
    if total <= 0 or delta < 0:
        return None
    return min(100.0, 100.0 * delta / total)


def prepare_sample(raw, previous):
    if raw.get('schema') != 1 or not isinstance(raw.get('processes'), list):
        raise ValueError('Invalid board snapshot')
    same_boot = previous is not None and raw['boot_id'] == previous['boot_id']
    total = raw['total_ticks'] - previous['total_ticks'] if same_boot else 0
    busy = total - (raw['idle_ticks'] - previous['idle_ticks']) if same_boot else 0
    raw['system_cpu_pct'] = percentage(busy, total)
    old_processes = {p['pid']: p for p in previous['processes']} if same_boot else {}
    for proc in raw['processes']:
        prior = old_processes.get(proc['pid'])
        proc['cpu_pct'] = (percentage(proc['ticks'] - prior['ticks'], total)
                           if prior and prior['birth'] == proc['birth'] else None)
    elapsed = raw['monotonic'] - previous['monotonic'] if same_boot else 0
    camera, gui = raw['camera'], raw['gui']
    camera['rates'] = {}
    if elapsed > 0 and camera.get('available') and previous['camera'].get('pid') == camera.get('pid'):
        for name, path in [('yolo', ('schedule', 'primary_calls')), ('yunet', ('faces', 'processed')),
                           ('sface', ('features', 'completed'))]:
            section, key = path
            new = camera.get(section, {}).get(key)
            old = previous['camera'].get(section, {}).get(key)
            if type(new) is int and type(old) is int and new >= old:
                camera['rates'][name] = (new - old) / elapsed
    avatar = gui.get('avatar', {})
    old_avatar = previous['gui'].get('avatar', {}) if same_boot else {}
    gui_owner = next(((p['pid'], p['birth']) for p in raw['processes'] if p['role'] == 'gui'), None)
    raw['gui_owner'] = gui_owner
    if (elapsed > 0 and gui_owner and gui_owner == previous.get('gui_owner')
            and type(avatar.get('frames')) is int and type(old_avatar.get('frames')) is int
            and avatar['frames'] >= old_avatar['frames']):
        avatar['observed_fps'] = (avatar['frames'] - old_avatar['frames']) / elapsed
    raw.update(online=True, local_time=datetime.now().astimezone().isoformat(), received_at=time.monotonic())
    return raw


class BoardSampler:
    def __init__(self):
        self.process = None
        self.previous = None
        self.responses = None

    def connect(self):
        probe = PROBE.read_bytes()
        remote = 'python3 -B -u -c ' + shlex.quote(BOOTSTRAP)
        args = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                '-o', 'ConnectTimeout=3', '-o', 'ClearAllForwardings=yes',
                '-o', 'ServerAliveInterval=3', '-o', 'ServerAliveCountMax=1', 'aura-kv260', remote]
        proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
        self.process = proc
        responses = self.responses = queue.Queue()

        def read_pipe():
            try:
                while True:
                    line = proc.stdout.readline(2 * 1024 * 1024 + 1)
                    if not line:
                        break
                    responses.put(line)
                    if len(line) > 2 * 1024 * 1024:
                        break
            except (OSError, ValueError):
                pass
            finally:
                responses.put(None)

        threading.Thread(target=read_pipe, daemon=True, name='kv260-observer-pipe').start()
        proc.stdin.write(str(len(probe)).encode('ascii') + b'\n' + probe)
        proc.stdin.flush()

    def sample(self):
        began = time.monotonic()
        try:
            if self.process is None:
                self.connect()
            self.process.stdin.write(b'S\n')
            self.process.stdin.flush()
            line = self.responses.get(timeout=7)
            if not line or len(line) > 2 * 1024 * 1024:
                raise ValueError('SSH 连接已中断')
            if not line.startswith(b'{'):
                if b'Permission denied' in line or b'Host key verification failed' in line:
                    raise ValueError('SSH 身份或主机指纹校验失败')
                raise ValueError('无法取得采样，请检查网线与 SSH 连接')
            sample = prepare_sample(json.loads(line), self.previous)
            self.previous = sample
            sample['roundtrip_ms'] = (time.monotonic() - began) * 1000
            return sample
        except (OSError, ValueError, KeyError, TypeError, queue.Empty) as exc:
            self.close()
            reason = str(exc) if type(exc) is ValueError else 'SSH 连接或板端采样暂不可用'
            return {'online': False, 'error': reason, 'received_at': time.monotonic(),
                    'local_time': datetime.now().astimezone().isoformat()}

    def close(self):
        self.previous = None
        proc, self.process = self.process, None
        if proc is None:
            return
        try:
            proc.stdin.close()
        except OSError:
            pass
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)
        proc.stdout.close()


def format_number(value, suffix='', precision=0):
    return '—' if value is None else f'{value:,.{precision}f}{suffix}'


def flag(value, yes='运行中', no='已停止'):
    return yes if value is True else no if value is False else '未知'


def board_tasks(board):
    """Logical workers share their process's resources; never add those twice."""
    if not board.get('online'):
        return []
    by_role = defaultdict(list)
    for proc in board['processes']:
        if proc['role']:
            by_role[proc['role']].append(proc)
    gui, cam = board['gui'], board['camera']
    listen, pan, follow = (gui.get(k, {}) for k in ('listening', 'pan', 'follow'))
    audio, avatar, memory, speaker = (gui.get(k, {}) for k in ('audio', 'avatar', 'memory', 'speaker'))
    rows = []

    def add(key, name, state, detail, role, shared=False):
        owners = by_role[role]
        def aggregate(field):
            if shared or not owners or any(p.get(field) is None for p in owners):
                return None
            return sum(p[field] for p in owners)
        rows.append(dict(id=key, name=name, state=state, detail=detail, pids=[p['pid'] for p in owners],
                         owner=ROLE_NAMES[role], shared=shared, cpu_pct=aggregate('cpu_pct'), rss_mib=aggregate('rss_mib')))

    details = {
        'supervisor': '管理原生界面生命周期',
        'gui': '界面、语音调度与板端业务',
        'camera': '采集 ' + format_number(cam.get('capture_hz'), ' 帧/秒', 1),
        'frontend': '麦克风' + flag(listen.get('microphone_open'), '已打开', '已关闭') + ' · ' + str(listen.get('state', '待观测')),
        'capture': '按轮次启动的 ALSA 录音进程',
        'playback': str(audio.get('device_state', '设备状态未知')) + ' · 缓冲 ' + format_number(audio.get('queued_ms'), ' ms'),
        'follow': str(follow.get('phase', '待观测')) + ' · 已接受 ' + format_number(follow.get('commands_accepted'), ' 条指令'),
        'manual': '手动控制后端',
        'editor': '调节与显示跟随边界',
        'fabric': '管理视觉与转轴的联合固件',
        'display': 'X11 显示及桌面子进程',
        'sound': '板端音频服务',
        'auxiliary': '服务进程组内的其他工作进程',
    }
    for role, name in ROLE_NAMES.items():
        status = '运行中' if by_role[role] else '未运行'
        if role == 'follow' and gui.get('available'):
            status = flag(pan.get('automatic_following'), '已开启', '已关闭')
        add(role, name, status, details[role], role)
    rates = cam.get('rates', {})
    for key, name, present, extra in (
        ('yolo', '人体检测与 ByteTrack 跟踪', cam.get('schedule', {}).get('native_critical'), 'YOLOX'),
        ('yunet', '人脸检测', cam.get('faces', {}).get('worker_alive'), 'YuNet'),
        ('sface', '人脸特征提取', cam.get('features', {}).get('ready'), 'SFace'),
    ):
        add(key, name, flag(present, '已就绪', '未就绪'), extra + ' · ' + format_number(rates.get(key), ' 次/秒', 1), 'camera', True)
    add('asr', 'Paraformer 语音识别', '板端识别' if gui.get('processing', {}).get('asr_location') == 'board' else '未知',
        '最近轮次识别 ' + format_number(gui.get('latency', {}).get('asr_ms'), ' ms'), 'gui', True)
    add('speaker', 'ECAPA 声纹识别', flag(speaker.get('ready'), '已就绪', '未就绪'),
        'CPU · 完成 ' + format_number(speaker.get('complete'), ' 次'), 'gui', True)
    add('memory', '对话记忆与摘要', flag(memory.get('running')), '已完成 ' + format_number(memory.get('completed'), ' 项'), 'gui', True)
    add('retention', '记忆保留维护', flag(gui.get('retention', {}).get('running')),
        '板端持久记忆维护', 'gui', True)
    add('timeline', '视觉时间线', flag(gui.get('timeline', {}).get('thread_alive')),
        '更新 ' + format_number(gui.get('timeline', {}).get('steps'), ' 次'), 'gui', True)
    add('avatar', '雪妃动画渲染', flag(avatar.get('visible'), '角色可见', '当前页隐藏'),
        '观测 ' + format_number(avatar.get('observed_fps'), ' 帧/秒', 1) + ' · 目标 ' + format_number(avatar.get('target_fps')), 'gui', True)
    return rows
