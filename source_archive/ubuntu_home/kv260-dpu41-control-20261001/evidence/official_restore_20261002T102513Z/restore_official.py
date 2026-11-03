#!/usr/bin/env python3
"""Restore only when necessary and verify the official hardware and fixed input."""
import base64
import datetime
import fcntl
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import traceback
import zlib

root = Path(__file__).resolve().parent
port = '/dev/serial/by-id/usb-Xilinx_ML_Carrier_Card_XFL1EMEBC1R5-if01-port0'
official = 'kv260-benchmark-b4096'
result_path = root / 'restore_result.json'

def packed_command(name, args=()):
    payload = base64.b64encode(zlib.compress((root / name).read_bytes(), 9)).decode()
    code = ('import base64,zlib,sys;sys.argv=' + repr([name] + list(args)) +
            ';exec(compile(zlib.decompress(base64.b64decode(' + repr(payload) + ')),' +
            repr(name) + ",'exec'))")
    return 'python3 -B -c ' + shlex.quote(code)

def phase(name, entries):
    with (root / (name + '.commands.json')).open('x') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('\n=== ' + name + ' ===', flush=True)
    subprocess.run([sys.executable, '-u', str(root / 'collect.py'), name], check=True)
    commands = []
    for line in (root / (name + '.results.jsonl')).read_text().splitlines():
        r = json.loads(line)
        if r.get('type') != 'command':
            continue
        p = root / (name + '.' + r['id'] + '.output')
        if not r['complete'] or r['exit_code'] != 0 or hashlib.sha256(p.read_bytes()).hexdigest() != r['integrity_sha256']:
            raise RuntimeError('Failed or incomplete command: ' + r['id'])
        commands.append(r)
        if 'kernel' not in r['id']:
            print(r['output'], flush=True)
    if [r['id'] for r in commands] != [e['id'] for e in entries]:
        raise RuntimeError('Evidence command list mismatch')
    return {r['id']: r for r in commands}

def state_from(record):
    lines = [line for line in record['output'].splitlines() if line.startswith('STATE_JSON ')]
    if len(lines) != 1:
        raise RuntimeError('State output missing')
    return json.loads(lines[0][len('STATE_JSON '):])

def top5(text):
    return [(int(i), float(s)) for i, s in re.findall(r'r.index (\d+) [^\n]*?r.score ([0-9.]+)', text)]

def run():
    owner = subprocess.run(['fuser', str(Path(port).resolve())], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True)
    if owner.returncode == 0:
        raise RuntimeError('UART already open by process IDs: ' + owner.stdout.strip())
    if owner.returncode != 1:
        raise RuntimeError('Unable to check UART ownership: ' + owner.stderr.strip())
    print('KV260 官方应用恢复 / 核验', flush=True)
    print('先检查当前状态；官方已经运行时直接核验。', flush=True)
    before = phase('01-check', [
        {'id': 'current_state', 'command': packed_command('board_state.py'), 'timeout': 45},
        {'id': 'before_kernel_log', 'command': 'dmesg', 'timeout': 60},
    ])
    current = state_from(before['current_state'])
    active = current['active_apps']
    changed = False
    if active == [official]:
        print('当前官方应用已运行，跳过卸载和重载，开始核验。', flush=True)
    else:
        if active:
            phase('02-remove-candidate', [
                {'id': 'remove_candidate', 'command': packed_command('client_action.py', ('remove', active[0], 'NONE')), 'timeout': 100}
            ])
        phase('03-load-official', [
            {'id': 'load_official', 'command': packed_command('client_action.py', ('load', 'NONE', official)), 'timeout': 100}
        ])
        changed = True
    firmware = '/lib/firmware/xilinx/' + official + '/' + official + '.xclbin'
    verified = phase('04-verify', [
        {'id': 'official_state', 'command': packed_command('board_state.py'), 'timeout': 45},
        {'id': 'official_dpu', 'command': 'env XLNX_VART_FIRMWARE=' + firmware + ' xdputil query', 'timeout': 40},
        {'id': 'official_classification', 'command':
            'cd /home/root/kv260-test-20261001 && env XLNX_VART_FIRMWARE=' + firmware +
            ' /home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification resnet18 /home/root/kv260-test-20261001/pytorch-resnet-dog.jpg', 'timeout': 45},
        {'id': 'after_kernel_log', 'command': 'dmesg', 'timeout': 60},
    ])
    state = state_from(verified['official_state'])
    if (state['active_apps'] != [official] or state['fpga_manager'] != 'operating' or
            state['live_firmware_name'] != official + '.bit.bin' or
            state['vart_firmware_lines'] != ['firmware: ' + firmware]):
        raise RuntimeError('Official application/runtime state mismatch')
    query = json.loads(verified['official_dpu']['output'])
    k = query['kernels'][0]
    if (query['DPU IP Spec']['DPU Core Count'] != 1 or
            query['DPU IP Spec']['git commit id'] != 'ce8dd1' or
            k['fingerprint'] != '0x101000056010407' or k['cu_addr'] != '0xa0010000' or
            k['DPU Frequency (MHz)'] != 300):
        raise RuntimeError('Original official DPU hardware identity mismatch')
    expected = [(258, 0.949879), (270, 0.00931229), (259, 0.00821807), (257, 0.00498451), (279, 0.00388194)]
    scores = top5(verified['official_classification']['output'])
    if scores != expected:
        raise RuntimeError('Official classification differs from the fixed baseline')
    def ref_errors(text):
        return {line for line in text.splitlines() if 'of_node_get()/of_node_put() unbalanced' in line}
    errors = sorted(ref_errors(verified['after_kernel_log']['output']) - ref_errors(before['before_kernel_log']['output']))
    if not re.search(r'zocl_xclbin_read_axlf eedb44e9-3f77-0244-9ea9-23b953894638 ret: 0',
                     verified['after_kernel_log']['output']):
        raise RuntimeError('Official runtime UUID not confirmed')
    result = {
        'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'result': 'PASS', 'application_switch_performed': changed,
        'initial_active_apps': active, 'final_active_apps': state['active_apps'],
        'official_state': state, 'actual_dpu_ip_spec': query['DPU IP Spec'],
        'official_classification_top5': scores, 'new_observed_overlay_refcount_errors': errors,
        'kernel_scope': 'Ring-buffer snapshots; old history may be overwritten.',
        'previous_overlay_refcount_issue_resolved': False,
    }
    with result_path.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('\n核验通过：官方应用 active slot 0，原 DPU 标记、固件及输入哈希一致，Samoyed 0.949879。', flush=True)
    print('实际执行应用切换：' + ('是' if changed else '否（原本已恢复）'), flush=True)
    print('本次快照中新观察到的引用计数错误：' + str(len(errors)), flush=True)
    print('历史 overlay 引用计数问题仍未修复。', flush=True)
    print('日志目录：' + str(root), flush=True)

try:
    with Path('/tmp/kv260-official-restore-uart.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run()
except Exception as exc:
    if not result_path.exists():
        with result_path.open('x') as f:
            json.dump({'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       'result': 'FAILED', 'error': str(exc),
                       'scope': 'Stopped; inspect original command evidence before retrying.'}, f, ensure_ascii=False, indent=2)
            f.write('\n')
    traceback.print_exc()
    sys.exit(1)

