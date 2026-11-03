# -*- coding: utf-8 -*-
"""AURA v3 说话素材：构建 API 图 -> 串行提交 ComfyUI -> 归集原始帧到候选批次。

用法（生成机本机执行，串行、可重入、不写正式 assets）：
  python zz_aura_v3_batch.py build  --only talking_calm_rest_v3 talking_calm_blink_v3 talking_warm_rest_v3 talking_low_rest_v3
  python zz_aura_v3_batch.py submit --only talking_calm_rest_v3 --limit 1
  python zz_aura_v3_batch.py submit            # 全部，已完成的自动跳过

纪律：
  * 只写候选目录 deliverables\\avatar_candidates\\batch_001，绝不触碰 aura\\assets；
  * 归集只接受该次 /history 返回的精确文件名，不用通配符，避免种子混批；
  * 每个种子 39 帧齐全才记 ok，否则记 partial 并保留现场。
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

AURA = r'D:\share、\项目开发\FPGA-amd自主命题赛道\aura'
DELIV = r'D:\share、\项目开发\FPGA-amd自主命题赛道\deliverables'
COMFY_OUT = (r'D:\sd-webui-aki-v4.11.1-cu128\ComfyUI_Windows_portable_cu130.7z'
             r'\ComfyUI_Windows_portable\ComfyUI\output')
BATCH = os.path.join(DELIV, 'avatar_candidates', 'batch_001')
URL = 'http://127.0.0.1:8188'
CLIENT_ID = 'aura-naturalness-v3'
BUILDER = os.path.join(AURA, 'tools', 'build_naturalness_workflows.py')
REST_REF = 'doll_green_9x16.png'
HELD_REF = 'doll_green_9x16_hold.png'
EXPECTED_FRAMES = 39
DEFAULT_IDS = ['talking_calm_rest_v3', 'talking_calm_blink_v3',
               'talking_warm_rest_v3', 'talking_low_rest_v3']
DEFAULT_SEEDS = [421001, 421002, 421003]
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


def do_build(ids, seeds):
    if not os.path.isfile(BUILDER):
        raise SystemExit('builder missing: %s' % BUILDER)
    wf_dir = os.path.join(BATCH, 'workflows')
    cmd = [sys.executable, '-B', BUILDER, '--outdir', wf_dir,
           '--rest-reference', REST_REF, '--held-reference', HELD_REF,
           '--seeds'] + [str(s) for s in seeds] + ['--only'] + list(ids)
    log('build: %s' % ' '.join(cmd[-6:]))
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    log('build rc=%s out=%s' % (r.returncode, (r.stdout or '').strip().splitlines()[-1:]))
    if r.returncode != 0:
        log('build stderr tail: %s' % (r.stderr or '').strip()[-400:])
        raise SystemExit('build failed')
    return wf_dir


def collect(hist, dest, meta):
    images = []
    for nid, out in (hist.get('outputs') or {}).items():
        for img in out.get('images', []) or []:
            images.append((nid, img))
    if not images:
        return 0
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
    meta['frame_count'] = wrote
    if wrote:
        meta['sha256_first'] = sha256(os.path.join(dest, '000000.png'))
        meta['sha256_last'] = sha256(os.path.join(dest, '%06d.png' % (wrote - 1)))
    return wrote


def do_submit(ids, seeds, limit, timeout):
    wf_dir = os.path.join(BATCH, 'workflows')
    raw_root = os.path.join(BATCH, 'raw')
    runs, done = [], 0
    for aid in ids:
        for seed in seeds:
            graph_path = os.path.join(wf_dir, '%s_s%d_api.json' % (aid, seed))
            dest = os.path.join(raw_root, '%s_s%d' % (aid, seed))
            if not os.path.isfile(graph_path):
                log('skip (no graph): %s' % os.path.basename(graph_path))
                continue
            have = len([n for n in os.listdir(dest) if n.endswith('.png')]) \
                if os.path.isdir(dest) else 0
            if have >= EXPECTED_FRAMES:
                log('skip (has %d frames): %s' % (have, os.path.basename(dest)))
                continue
            if limit and done >= limit:
                log('limit reached (%d)' % limit)
                return runs
            with open(graph_path, encoding='utf-8') as f:
                graph = json.load(f)
            mid = os.path.basename(graph_path)
            t0 = time.time()
            status, resp = http_json(URL + '/prompt',
                                     {'prompt': graph, 'client_id': CLIENT_ID}, timeout=60)
            if status != 200 or 'prompt_id' not in resp:
                log('SUBMIT_FAIL %s status=%s %s' % (mid, status, json.dumps(resp)[:300]))
                runs.append({'api_graph': mid, 'state': 'submit_failed', 'http': status})
                done += 1
                continue
            pid = resp['prompt_id']
            log('submitted %s prompt_id=%s' % (mid, pid))
            hist, waited = None, 0
            while waited < timeout:
                st, h = http_json('%s/history/%s' % (URL, pid), timeout=30)
                if st == 200 and pid in h:
                    hist = h[pid]
                    break
                time.sleep(5)
                waited += 5
            if hist is None:
                log('TIMEOUT %s after %ss' % (mid, timeout))
                runs.append({'api_graph': mid, 'state': 'timeout', 'prompt_id': pid})
                done += 1
                continue
            stt = (hist.get('status') or {}).get('status_str', '?')
            meta = {'api_graph': mid, 'api_graph_sha256': sha256(graph_path),
                    'seed': seed, 'asset_id': aid, 'prompt_id': pid, 'status': stt,
                    'seconds': round(time.time() - t0, 1),
                    'prefix': 'AURA_NATURAL_V3_%s_s%d' % (aid.upper(), seed)}
            n = collect(hist, dest, meta)
            meta['state'] = 'ok' if (n == EXPECTED_FRAMES and stt == 'success') else 'partial'
            with open(os.path.join(dest, 'meta.json'), 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            log('%s %s frames=%d status=%s %.1fs'
                % (meta['state'].upper(), mid, n, stt, meta['seconds']))
            runs.append(meta)
            done += 1
    return runs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['build', 'submit'])
    ap.add_argument('--only', nargs='+', default=DEFAULT_IDS)
    ap.add_argument('--seeds', nargs='+', type=int, default=DEFAULT_SEEDS)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--timeout', type=int, default=2400)
    a = ap.parse_args()

    if not BATCH.lower().startswith(DELIV.lower()) or 'assets' in BATCH.lower():
        raise SystemExit('candidate dir guard failed: %s' % BATCH)
    os.makedirs(os.path.join(BATCH, 'logs'), exist_ok=True)
    global LOG_PATH
    LOG_PATH = os.path.join(BATCH, 'logs',
                            'submit_%s.log' % time.strftime('%Y%m%d_%H%M%S'))
    log('mode=%s ids=%s seeds=%s limit=%s' % (a.mode, ','.join(a.only), a.seeds, a.limit))
    st, _ = http_json(URL + '/system_stats', timeout=10)
    log('comfyui reachable=%s' % (st == 200))
    if a.mode == 'build':
        do_build(a.only, a.seeds)
        log('build done')
        return 0
    if not os.path.isdir(COMFY_OUT):
        raise SystemExit('bad COMFY_OUT: %s' % COMFY_OUT)
    runs = do_submit(a.only, a.seeds, a.limit, a.timeout)
    man = os.path.join(BATCH, 'run_manifest.json')
    old = []
    if os.path.isfile(man):
        with open(man, encoding='utf-8') as f:
            old = json.load(f).get('runs', [])
    with open(man, 'w', encoding='utf-8') as f:
        json.dump({'batch': 'batch_001', 'runs': old + runs}, f,
                  ensure_ascii=False, indent=2)
    log('submit session done: %d runs' % len(runs))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
