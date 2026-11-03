# -*- coding: utf-8 -*-
"""E2 单变量试产：在 E1（length=124）之上，新增**一个中间帧锚定**（MiniMaxH3AddGuide）。

依据：接收端 `batch_002_probe/review_20261006/接收端验收结论.md` §4——
「先修正测量区域和命名，再做一条保持姿势的约束小样……优先验证交接中提出的
 E2 中间帧参考约束是否能在实际节点版本中正确接入」；每次只改一个条件。

本脚本**不改** batch_001 / batch_002_probe 的任何文件，也不写 aura\\assets。

唯一变化（相对 E1 图 `batch_002_probe\\workflows\\e1_rest_s421001_L124_api.json`）：
  1. 新增节点 15：`MiniMaxH3AddGuide`，输入 positive=[7,0]、latent=[7,1]、
     image=[5,0]（与首/末帧同一张参考图）、vae=[3,0]、frame_idx=62（0..123 中间帧）；
  2. 节点 10(BasicGuider) 的 conditioning 由 ["7",0] 改为 ["15",0]。
其余逐字不动：参考图 doll_green_9x16.png、864x1536、length=124、提示词全文、种子 421001、
8 步 turbo LoRA、采样器 res_multistep、首/末帧同为节点 5。

节点可用性实测（2026-10-06，/object_info/MiniMaxH3AddGuide）：
  必需输入 positive(CONDITIONING)/latent(LATENT)/frame_idx(INT)，可选 vae/image/audio；
  **不依赖任何额外权重文件**，属 comfy_extras.nodes_minimax_h3（ComfyUI 0.38.0 内置）。

用法（生成机本机、长任务必须脱离终端启动）：
  python.exe -s probe_v3_guide_mid.py --dry-run     # 只出图 + 差异清单，不提交
  python.exe -s probe_v3_guide_mid.py               # 生成并提交 1 条
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
import urllib.error
import urllib.request

DELIV = r'D:\share、\项目开发\FPGA-amd自主命题赛道\deliverables'
AVATARS = os.path.join(DELIV, 'avatar_candidates')
SRC_GRAPH = os.path.join(AVATARS, 'batch_002_probe', 'workflows',
                         'e1_rest_s421001_L124_api.json')
DEFAULT_OUT = os.path.join(AVATARS, 'batch_003_guide_probe')
COMFY_OUT = (r'D:\sd-webui-aki-v4.11.1-cu128\ComfyUI_Windows_portable_cu130.7z'
             r'\ComfyUI_Windows_portable\ComfyUI\output')
URL = 'http://127.0.0.1:8188'
CLIENT_ID = 'aura-e2-guide'
CASE_ID = 'e2_rest_s421001_L124_guide62'
GUIDE_NODE = '15'
GUIDER_NODE = '10'
LENGTH = 124
FRAME_IDX = 62
LOG_PATH = ''


def log(line):
    text = '[%s] %s' % (time.strftime('%H:%M:%S'), line)
    print(text, flush=True)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(text + '\n')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def http_json(url, payload=None, timeout=30):
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    req = urllib.request.Request(url, data=data,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace')
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {'raw': body[:2000]}
    except (urllib.error.URLError, OSError) as e:
        return 0, {'error': str(e)}


def load_graph(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def patch_graph(graph, frame_idx):
    """新增一个 AddGuide 锚点并把它接到 BasicGuider；返回 (新图, 变更说明)。"""
    classes = [n.get('class_type') for n in graph.values()]
    if 'MiniMaxH3AddGuide' in classes:
        raise SystemExit('source graph already contains MiniMaxH3AddGuide')
    if '7' not in graph or graph['7'].get('class_type') != 'MiniMaxH3ImageToVideo':
        raise SystemExit('expect node 7 = MiniMaxH3ImageToVideo')
    if '10' not in graph or graph['10'].get('class_type') != 'BasicGuider':
        raise SystemExit('expect node 10 = BasicGuider')
    if graph['7']['inputs'].get('length') != LENGTH:
        raise SystemExit('source graph length is not %d' % LENGTH)
    graph[GUIDE_NODE] = {
        'class_type': 'MiniMaxH3AddGuide',
        'inputs': {
            'positive': ['7', 0],
            'latent': ['7', 1],
            'frame_idx': frame_idx,
            'vae': ['3', 0],
            'image': ['5', 0],
        },
    }
    before = list(graph[GUIDER_NODE]['inputs']['conditioning'])
    graph[GUIDER_NODE]['inputs']['conditioning'] = [GUIDE_NODE, 0]
    changed = [
        {'op': 'add_node', 'node': GUIDE_NODE, 'class_type': 'MiniMaxH3AddGuide',
         'inputs': dict(graph[GUIDE_NODE]['inputs'])},
        {'op': 'rewire', 'node': GUIDER_NODE, 'input': 'conditioning',
         'from': before, 'to': [GUIDE_NODE, 0]},
    ]
    return graph, changed


def diff_paths(a, b, prefix=''):
    """递归比较两份图，返回所有不同路径（用于“改了几处”的自证）。"""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append({'path': '%s/%s' % (prefix, k),
                            'from': a.get(k, '<MISSING>'), 'to': b.get(k, '<MISSING>')})
            else:
                out += diff_paths(a[k], b[k], '%s/%s' % (prefix, k))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append({'path': prefix, 'from': a, 'to': b})
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                out += diff_paths(x, y, '%s/%d' % (prefix, i))
    elif a != b:
        out.append({'path': prefix, 'from': a, 'to': b})
    return out


def guard(out_root):
    low = out_root.lower()
    if not low.startswith(DELIV.lower()) or 'assets' in low:
        raise SystemExit('output guard failed: %s' % out_root)


def collect(hist, dest):
    images = []
    for nid, out in (hist.get('outputs') or {}).items():
        for key in ('images', 'gifs'):
            for img in (out.get(key) or []):
                if isinstance(img, dict) and img.get('filename', '').endswith('.png'):
                    images.append((nid, img))
    os.makedirs(dest, exist_ok=True)
    images.sort(key=lambda t: t[1].get('filename', ''))
    wrote = 0
    for idx, (nid, img) in enumerate(images):
        sub = img.get('subfolder', '') or ''
        src = os.path.join(COMFY_OUT, sub, img['filename'])
        if not os.path.isfile(src):
            log('  ! missing source %s' % src)
            continue
        shutil.copy2(src, os.path.join(dest, '%06d.png' % idx))
        wrote += 1
    return wrote


def status_tail(hist, n=3):
    msgs = ((hist.get('status') or {}).get('messages') or [])[-n:]
    return json.dumps(msgs, ensure_ascii=False)[:1500]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src-graph', default=SRC_GRAPH)
    ap.add_argument('--frame-idx', type=int, default=FRAME_IDX)
    ap.add_argument('--out-root', default=DEFAULT_OUT)
    ap.add_argument('--case-id', default=CASE_ID)
    ap.add_argument('--timeout', type=int, default=5400)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    guard(a.out_root)
    wf_dir = os.path.join(a.out_root, 'workflows')
    raw_dir = os.path.join(a.out_root, 'raw', a.case_id)
    log_dir = os.path.join(a.out_root, 'logs')
    for d in (wf_dir, raw_dir, log_dir):
        os.makedirs(d, exist_ok=True)
    global LOG_PATH
    LOG_PATH = os.path.join(log_dir, 'probe_%s.log' % time.strftime('%Y%m%d_%H%M%S'))
    log('E2 probe: src=%s frame_idx=%d out=%s'
        % (os.path.basename(a.src_graph), a.frame_idx, a.out_root))

    src = load_graph(a.src_graph)
    graph, changed = patch_graph(src, a.frame_idx)
    # 注意：patch_graph 会**就地修改**传入的图，因此自证必须重新从磁盘读源图比较
    paths = diff_paths(load_graph(a.src_graph), graph)
    log('diff paths=%d %s' % (len(paths), json.dumps(paths, ensure_ascii=False)[:600]))
    expect = 2
    if len(paths) < expect:
        log('WARNING: expected at least %d differing paths (new node + rewire)' % expect)

    dest_graph = os.path.join(wf_dir, '%s_api.json' % a.case_id)
    with open(dest_graph, 'w', encoding='utf-8') as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    manifest = {
        'case_id': a.case_id,
        'experiment': 'E2 中间帧锚定（保持姿势约束）',
        'basis': 'review_20261006/接收端验收结论.md §4：先做一条保持姿势的约束小样，'
                 '优先验证 E2 中间帧参考约束能否在实际节点版本接入',
        'source_graph': os.path.basename(a.src_graph),
        'source_graph_sha256': sha256(a.src_graph),
        'probe_graph': os.path.basename(dest_graph),
        'probe_graph_sha256': sha256(dest_graph),
        'single_variable': '相对 E1（length=124）只增加 1 个中间帧锚定 + 1 处重连',
        'changed': changed,
        'all_diff_paths': paths,
        'node_availability': 'MiniMaxH3AddGuide 由 /object_info 实测存在（comfy_extras.nodes_minimax_h3），'
                             '无额外权重依赖',
        'frame_idx': a.frame_idx,
        'length': LENGTH,
    }
    with open(os.path.join(wf_dir, '%s_manifest.json' % a.case_id), 'w',
              encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    log('graph written: %s' % dest_graph)
    if a.dry_run:
        log('dry-run: 未提交')
        return 0

    st, _ = http_json(URL + '/system_stats', timeout=10)
    log('comfyui reachable=%s' % (st == 200))
    if st != 200:
        raise SystemExit('comfyui unreachable')
    status, resp = http_json(URL + '/prompt',
                             {'prompt': graph, 'client_id': CLIENT_ID}, timeout=60)
    if status != 200 or 'prompt_id' not in resp:
        log('SUBMIT_FAIL status=%s %s' % (status, json.dumps(resp)[:600]))
        with open(os.path.join(raw_dir, 'meta.json'), 'w', encoding='utf-8') as f:
            json.dump({'case_id': a.case_id, 'state': 'submit_fail', 'http_status': status,
                       'response': resp}, f, ensure_ascii=False, indent=2)
        return 1
    pid = resp['prompt_id']
    log('submitted prompt_id=%s' % pid)

    t0, hist, last_log = time.time(), None, 0
    while time.time() - t0 < a.timeout:
        st2, h = http_json('%s/history/%s' % (URL, pid), timeout=30)
        if st2 == 200 and pid in h:
            hist = h[pid]
            break
        el = int(time.time() - t0)
        if el - last_log >= 60:
            last_log = el
            log('waiting %ss' % el)
        time.sleep(6)
    if hist is None:
        with open(os.path.join(raw_dir, 'meta.json'), 'w', encoding='utf-8') as f:
            json.dump({'case_id': a.case_id, 'prompt_id': pid, 'state': 'timeout',
                       'seconds': round(time.time() - t0, 1)}, f, ensure_ascii=False, indent=2)
        log('TIMEOUT after %ss' % int(time.time() - t0))
        return 1

    stt = (hist.get('status') or {}).get('status_str', '?')
    n = collect(hist, raw_dir)
    meta = {'case_id': a.case_id, 'api_graph': os.path.basename(dest_graph),
            'api_graph_sha256': sha256(dest_graph), 'prompt_id': pid,
            'status': stt, 'seconds': round(time.time() - t0, 1),
            'length': LENGTH, 'frame_idx': a.frame_idx, 'frame_count': n,
            'changed': changed,
            'state': 'ok' if (n == LENGTH and stt == 'success') else 'partial'}
    if n:
        meta['sha256_first'] = sha256(os.path.join(raw_dir, '000000.png'))
        meta['sha256_last'] = sha256(os.path.join(raw_dir, '%06d.png' % (n - 1)))
    if stt != 'success':
        meta['status_tail'] = status_tail(hist)
    with open(os.path.join(raw_dir, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    log('%s frames=%d status=%s %.1fs seconds'
        % (meta['state'].upper(), n, stt, meta['seconds']))
    log('E2_DONE')
    return 0 if meta['state'] == 'ok' else 1


if __name__ == '__main__':
    raise SystemExit(main())

