# -*- coding: utf-8 -*-
"""v2 批量入库：12 态绿幕帧 → 桌宠抠像(folder) + A/D1 去绿 → 抽帧缩放入库。

链路与 v1 试产（%TEMP%\\aura_ingest.py）完全一致，只把「单态」扩成「12 态批处理」：
    1. 归集 ComfyUI\\output\\<PREFIX>_<TAG>_*.png → %TEMP%\\aura_green_v2\\<TAG>
    2. scripts/prepare_avatar_frames.py --src <目录> --matte-src（先抠像再入库）
       → 抠像产物流向 %TEMP%，原始绿幕帧**只读**
    3. 强化去绿 A + D1（默认 --post-despill ad1，见 v1 技术记录 §十一）
    4. --fit-budget --budget-mb 12.5：装不下就自动降 fps，绝不让素材超预算
    5. burst 态（AWAKE / ACK_NOD）加 --burst-frames 22：只留前 22 帧（一次性动作）

用法（ComfyUI 便携 Python）：
    "<ComfyUI>\\python_standalone\\python.exe" -s tools\\aura_ingest_v2.py
    # 只入库部分状态：追加 tag，如 ... aura_ingest_v2.py SPEAKING AWAKE
产物：<aura>\\assets\\avatar\\<素材名>\\（**覆盖**现役素材，先自行备份）
日志：%TEMP%\\aura_ingest_v2.log
"""
import glob
import os
import re
import shutil
import subprocess
import sys
import time

PY = (r'D:\sd-webui-aki-v4.11.1-cu128\ComfyUI_Windows_portable_cu130.7z'
      r'\ComfyUI_Windows_portable\python_standalone\python.exe')
OUTDIR = (r'D:\sd-webui-aki-v4.11.1-cu128\ComfyUI_Windows_portable_cu130.7z'
          r'\ComfyUI_Windows_portable\ComfyUI\output')
AURA = ('D:\\share\u3001\\\u9879\u76ee\u5f00\u53d1\\FPGA-amd\u81ea\u4e3b'
        '\u547d\u9898\u8d5b\u9053\\aura')
MATTING = 'D:/share\u3001/\u9879\u76ee\u5f00\u53d1/\u684c\u9762AI\u684c\u5ba0'
PREFIX = 'DOLLGV2'
T = os.environ['TEMP']
BURST_FRAMES = 22          # 与生成端 --burst-len 22 对齐（模型网格 17k+5）
BUDGET_MB = 12.5           # v2 拍板 B：预算 10 → 12.5 MiB 以保住 24fps
LOG = os.path.join(T, 'aura_ingest_v2.log')

# 生成 tag → (素材名, 是否 burst)。素材名须与 avatar_assets.STATE_ASSET 一致。
MAP = [
    ('IDLE', 'idle_normal', False),
    ('PRESENT', 'idle_present', False),
    ('LISTENING', 'idle_listening', False),
    ('THINKING', 'idle_thinking', False),
    ('SPEAKING', 'talking_normal', False),
    ('SPEAKING_NEUTRAL', 'talking_neutral', False),
    ('SPEAKING_LOW', 'talking_low', False),
    ('PUZZLED', 'emo_puzzled', False),
    ('CAMERA_LOST', 'idle_offline', False),
    ('ERROR', 'emo_sad', False),
    ('AWAKE', 'emo_surprised', True),
    ('ACK_NOD', 'ack_nod', True),
    ('DENY_SHAKE', 'deny_shake', True),      # P1-1：否定摇头（burst）
]

lines = []


def log(s):
    lines.append(str(s))
    print(s, flush=True)
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def collect(tag):
    """把 ComfyUI 输出帧归集成 000000.png 序列目录（原始输出只读，只做复制）。

    **必须用正则精确匹配 `<PREFIX>_<TAG>_<序号>_.png`**：原来用
    `glob('%s_%s_*.png')`，`SPEAKING` 会把 `SPEAKING_NEUTRAL` / `SPEAKING_LOW`
    一起匹配进来（前缀通配），39x3 = 117 帧混成一条素材去抽帧，
    `--fit-budget` 再把它降成 8fps。真凶见技术记录「踩坑」一节。
    """
    pat = re.compile(r'^%s_%s_\d+_?\.png$' % (re.escape(PREFIX), re.escape(tag)))
    names = os.listdir(OUTDIR) if os.path.isdir(OUTDIR) else []
    files = sorted(os.path.join(OUTDIR, n) for n in names if pat.match(n))
    src = os.path.join(T, 'aura_green_v2', tag)
    if not files:
        log('FAIL %s: 未找到 %s_%s_*.png' % (tag, PREFIX, tag))
        return None
    if os.path.isdir(src):
        shutil.rmtree(src, ignore_errors=True)
    os.makedirs(src)
    for i, f in enumerate(files):
        shutil.copy2(f, os.path.join(src, '%06d.png' % i))
    log('%s: 归集 %d 帧' % (tag, len(files)))
    return src


def ingest(tag, name, burst, src):
    """单态入库：抠像 → 去绿 → 抽帧缩放 → meta.json / manifest.json。"""
    cmd = [PY, '-s', os.path.join(AURA, 'scripts', 'prepare_avatar_frames.py'),
           '--src', src, '--name', name, '--matte-src', '--force',
           '--framing', 'waist-up', '--max-side', '480',
           '--fps', '24', '--src-fps', '24', '--fit-budget',
           '--budget-mb', str(BUDGET_MB),
           '--matting-project', MATTING,
           '--out-root', os.path.join(AURA, 'assets', 'avatar'),
           '--temp-dir', os.path.join(T, 'aura_v2tmp'),
           '--keep-temp']
    if burst:
        cmd += ['--burst-frames', str(BURST_FRAMES)]
    log('RUN ' + ' '.join(cmd))
    t0 = time.time()
    p = subprocess.run(cmd, cwd=AURA, capture_output=True, text=True,
                       encoding='gbk', errors='replace')
    out = (p.stdout or '') + (p.stderr or '')
    for line in out.splitlines():
        if any(k in line for k in ('帧', 'MiB', '超预算', 'OK', 'Error', 'error',
                                   'Traceback', '警告', '预算')):
            log('  | ' + line.strip())
    log('%s -> %s  EXIT %s  %.1fs' % (tag, name, p.returncode, time.time() - t0))
    return p.returncode


wanted = [a for a in sys.argv[1:] if not a.startswith('--')]
todo = [m for m in MAP if not wanted or m[0] in wanted]
log('=== v2 批量入库 %d/%d 态  预算 %.1f MiB  burst=%d 帧 ==='
    % (len(todo), len(MAP), BUDGET_MB, BURST_FRAMES))
fails = []
for tag, name, burst in todo:
    src = collect(tag)
    if src is None:
        fails.append(tag)
        continue
    if ingest(tag, name, burst, src) != 0:
        fails.append(tag)
log('')
log('FAILED: %s' % (','.join(fails) if fails else 'none'))
log('done')
