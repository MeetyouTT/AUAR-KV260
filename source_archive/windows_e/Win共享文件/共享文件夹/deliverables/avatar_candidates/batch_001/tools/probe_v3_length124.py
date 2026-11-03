# -*- coding: utf-8 -*-
"""E1 单变量试产：只把 MiniMax H3 图生视频的 length 由 39 改成 124，其余逐字不动。

依据：`MiniMaxH3ImageToVideo.length` 官方 tooltip 写明
      "trained range is ~124-362"（见 review_20261005/生成机可用约束调研_2026-10-06.md §3）。
本脚本用于**验证**该假设，不修改 batch_001 任何文件，也不写 aura\\assets。

用法（生成机本机、串行长任务，必须脱离终端启动）：
  python -B probe_v3_length124.py --dry-run          # 只生成 API 图 + 差异清单，不提交
  python -B probe_v3_length124.py                    # 生成并提交 1 条，产物落 batch_002_probe
可选：--length 124 --src-graph <api.json> --out-root <batch_002_probe> --timeout 5400

纪律：
  * 只写 deliverables\\avatar_candidates\\batch_002_probe（守卫：不得含 assets、不得越出 deliverables）；
  * 归集只认本次 /history 返回的文件名，不用通配符；
  * 任何失败都落盘 meta.json（含 ComfyUI 状态消息尾部），便于诊断 OOM/超时。
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
SRC_GRAPH = os.path.join(AVATARS, 'batch_001', 'workflows',
                         'talking_calm_rest_v3_s421001_api.json')
DEFAULT_OUT = os.path.join(AVATARS, 'batch_002_probe')
COMFY_OUT = (r'D:\sd-webui-aki-v4.11.1-cu128\ComfyUI_Windows_portable_cu130.7z'
             r'\ComfyUI_Windows_portable\ComfyUI\output')
URL = 'http://127.0.0.1:8188'
CLIENT_ID = 'aura-e1-probe'
CASE_ID = 'e1_rest_s421001_L124'
NODE_CLASS = 'MiniMaxH3ImageToVideo'
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


def patch_graph(graph, length):
    """把唯一的 MiniMaxH3ImageToVideo 节点 length 改掉，返回 (新图, 差异清单)。"""
    targets = [nid for nid, n in graph.items()
               if isinstance(n, dict) and n.get('class_type') == NODE_CLASS]
    if len(targets) != 1:
        raise SystemExit('expect exactly 1 %s node, got %d' % (NODE_CLASS, len(targets)))
    nid = targets[0]
    old = graph[nid]['inputs'].get('length')
    graph[nid]['inputs']['length'] = length
    changed = [{'node': nid, 'input': 'length', 'from': old, 'to': length}]
    return graph, changed


def diff_paths(a, b, prefix=''):
    """递归比较两份图，返回所有不同路径（用于"只改了一处"的自证）。"""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            out += diff_paths(a.get(k, '<MISSING>'), b.get(k, '<MISSING>'),
                              '%s/%s' % (prefix, k))
    elif isinstance(a, list) and isinstance(b, list):
        for i in range(max(len(a), len(b))):
            out += diff_paths(a[i] if i < len(a) else '<MISSING>',
                              b[i] if i < len(b) else '<MISSING>',
                              '%s/%d' % (prefix, i))
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
    ap.add_argument('--length', type=int, default=124)
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
    log('E1 probe: src=%s length->%d out=%s' % (os.path.basename(a.src_graph),
                                                a.length, a.out_root))

    graph, changed = patch_graph(load_graph(a.src_graph), a.length)
    paths = diff_paths(load_graph(a.src_graph), graph)
    log('diff paths=%d %s' % (len(paths), json.dumps(paths, ensure_ascii=False)[:400]))
    if len(paths) != 1 or 'length' not in str(paths[0].get('path', '')):
        log('WARNING: expected exactly the length field to differ')

    dest_graph = os.path.join(wf_dir, '%s_api.json' % a.case_id)
    with open(dest_graph, 'w', encoding='utf-8') as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    manifest = {
        'case_id': a.case_id,
        'source_graph': os.path.basename(a.src_graph),
        'source_graph_sha256': sha256(a.src_graph),
        'probe_graph': os.path.basename(dest_graph),
        'probe_graph_sha256': sha256(dest_graph),
        'changed': changed,
        'all_diff_paths': paths,
        'hypothesis': 'length 39 低于 MiniMax H3 训练区间 ~124-362，导致中段自行编排手位/躯干',
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
        log('SUBMIT_FAIL status=%s %s' % (status, json.dumps(resp)[:400]))
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
        meta = {'case_id': a.case_id, 'prompt_id': pid, 'state': 'timeout',
                'seconds': round(time.time() - t0, 1)}
        with open(os.path.join(raw_dir, 'meta.json'), 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        log('TIMEOUT after %ss' % int(time.time() - t0))
        return 1

    stt = (hist.get('status') or {}).get('status_str', '?')
    n = collect(hist, raw_dir)
    meta = {'case_id': a.case_id, 'api_graph': os.path.basename(dest_graph),
            'api_graph_sha256': sha256(dest_graph), 'prompt_id': pid,
            'status': stt, 'seconds': round(time.time() - t0, 1),
            'length': a.length, 'frame_count': n, 'changed': changed,
            'state': 'ok' if (n == a.length and stt == 'success') else 'partial'}
    if n:
        meta['sha256_first'] = sha256(os.path.join(raw_dir, '000000.png'))
        meta['sha256_last'] = sha256(os.path.join(raw_dir, '%06d.png' % (n - 1)))
    if stt != 'success':
        meta['status_tail'] = status_tail(hist)
    with open(os.path.join(raw_dir, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    log('%s frames=%d status=%s %.1fs seconds' % (meta['state'].upper(), n, stt,
                                                  meta['seconds']))
    log('E1_DONE')
    return 0 if meta['state'] == 'ok' else 1


if __name__ == '__main__':
    raise SystemExit(main())

