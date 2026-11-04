"""Read-only Windows model and KV260 performance dashboard."""
from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import ctypes as C
from ctypes import wintypes as W
import datetime as dt
import http.client
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

TITLE = 'AURA · 模型运行观测台'
PROJECT = Path(os.environ.get('AURA_MONITOR_PROJECT', Path(__file__).resolve().parents[2])).expanduser().resolve()
INTERVAL = 2.0
MIB = 1024 * 1024
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def finite(value, default=None):
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (ValueError, TypeError, OverflowError):
        return default


def percent_delta(previous, current, elapsed, logical_cpus):
    """Task Manager style: 100% is all logical CPU capacity, not one core."""
    if previous is None or elapsed <= 0 or logical_cpus < 1:
        return None
    delta = current - previous
    if delta < 0:
        return None
    return min(100.0, max(0.0, delta / elapsed / logical_cpus * 100))


def descendants(roots, processes):
    selected = set(roots) & set(processes)
    while True:
        added = {pid for pid, value in processes.items()
                 if value['ppid'] in selected and pid not in selected
                 and value.get('birth', math.inf) >= processes[value['ppid']].get('birth', 0)}
        if not added:
            return selected
        selected.update(added)


def exclusive_groups(roots, processes):
    """Specific model groups own children before the orchestration group."""
    result, claimed = {}, set()
    for name in ('llm', 'tts', 'other', 'portrait', 'legacy', 'monitor', 'host', 'project'):
        members = descendants(roots.get(name, ()), processes) - claimed
        result[name] = members
        claimed.update(members)
    return result


def engine_usage(values, members):
    """Sum a group's contexts per physical engine, then use busiest engine."""
    engines = defaultdict(float)
    for name, value in values.items():
        match = re.match(r'pid_(\d+)_(.+?)(?:#\d+)?$', name)
        if match and int(match[1]) in members and finite(value) is not None:
            engines[match[2]] += max(0.0, float(value))
    return min(100.0, max(engines.values(), default=0.0))


class PROCESSENTRY32W(C.Structure):
    _fields_ = [('dwSize', W.DWORD), ('cntUsage', W.DWORD), ('th32ProcessID', W.DWORD),
        ('th32DefaultHeapID', C.c_size_t), ('th32ModuleID', W.DWORD), ('cntThreads', W.DWORD),
        ('th32ParentProcessID', W.DWORD), ('pcPriClassBase', W.LONG), ('dwFlags', W.DWORD),
        ('szExeFile', W.WCHAR * 260)]


class PROCESS_MEMORY_COUNTERS_EX(C.Structure):
    _fields_ = [('cb', W.DWORD), ('PageFaultCount', W.DWORD)] + [
        (name, C.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
        'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
        'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage')]


class MEMORYSTATUSEX(C.Structure):
    _fields_ = [('dwLength', W.DWORD), ('dwMemoryLoad', W.DWORD)] + [
        (name, C.c_ulonglong) for name in ('ullTotalPhys', 'ullAvailPhys', 'ullTotalPageFile',
        'ullAvailPageFile', 'ullTotalVirtual', 'ullAvailVirtual', 'ullAvailExtendedVirtual')]


class TCPROW(C.Structure):
    _fields_ = [(name, W.DWORD) for name in ('state', 'local_addr', 'local_port',
                                           'remote_addr', 'remote_port', 'pid')]


def filetime(value):
    return ((value.dwHighDateTime << 32) | value.dwLowDateTime) / 10_000_000


class WindowsReader:
    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('This dashboard reads Windows counters only')
        self.kernel = C.WinDLL('kernel32', use_last_error=True)
        self.psapi = C.WinDLL('psapi', use_last_error=True)
        self.ip = C.WinDLL('iphlpapi', use_last_error=True)
        self.kernel.CreateToolhelp32Snapshot.argtypes = [W.DWORD, W.DWORD]
        self.kernel.CreateToolhelp32Snapshot.restype = W.HANDLE
        self.kernel.Process32FirstW.argtypes = [W.HANDLE, C.POINTER(PROCESSENTRY32W)]
        self.kernel.Process32NextW.argtypes = [W.HANDLE, C.POINTER(PROCESSENTRY32W)]
        self.kernel.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
        self.kernel.OpenProcess.restype = W.HANDLE
        self.kernel.CloseHandle.argtypes = [W.HANDLE]
        self.kernel.GetProcessTimes.argtypes = [W.HANDLE] + [C.POINTER(W.FILETIME)] * 4
        self.psapi.GetProcessMemoryInfo.argtypes = [W.HANDLE, C.c_void_p, W.DWORD]
        self.kernel.GetSystemTimes.argtypes = [C.POINTER(W.FILETIME)] * 3
        self.kernel.GlobalMemoryStatusEx.argtypes = [C.POINTER(MEMORYSTATUSEX)]
        self.ip.GetExtendedTcpTable.argtypes = [C.c_void_p, C.POINTER(W.DWORD),
            W.BOOL, W.ULONG, C.c_int, W.ULONG]

    def processes(self):
        handle = self.kernel.CreateToolhelp32Snapshot(2, 0)
        if handle == C.c_void_p(-1).value:
            raise OSError(C.get_last_error(), 'Process snapshot unavailable')
        row = PROCESSENTRY32W(); row.dwSize = C.sizeof(row)
        values = {}
        try:
            more = self.kernel.Process32FirstW(handle, C.byref(row))
            while more:
                values[int(row.th32ProcessID)] = dict(ppid=int(row.th32ParentProcessID), name=row.szExeFile,
                                                       threads=int(row.cntThreads))
                more = self.kernel.Process32NextW(handle, C.byref(row))
        finally:
            self.kernel.CloseHandle(handle)
        return values

    def process_usage(self, pid):
        handle = self.kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        created, exited, kernel, user = [W.FILETIME() for _ in range(4)]
        memory = PROCESS_MEMORY_COUNTERS_EX(); memory.cb = C.sizeof(memory)
        try:
            if not self.kernel.GetProcessTimes(handle, C.byref(created), C.byref(exited),
                                               C.byref(kernel), C.byref(user)):
                return None
            got_memory = bool(self.psapi.GetProcessMemoryInfo(handle, C.byref(memory), C.sizeof(memory)))
            return dict(birth=filetime(created), cpu_seconds=filetime(kernel) + filetime(user),
                rss_mib=memory.WorkingSetSize / MIB if got_memory else None,
                private_mib=memory.PrivateUsage / MIB if got_memory else None)
        finally:
            self.kernel.CloseHandle(handle)

    def system(self):
        idle, kernel, user = [W.FILETIME() for _ in range(3)]
        got = self.kernel.GetSystemTimes(C.byref(idle), C.byref(kernel), C.byref(user))
        memory = MEMORYSTATUSEX(); memory.dwLength = C.sizeof(memory)
        got_memory = self.kernel.GlobalMemoryStatusEx(C.byref(memory))
        return dict(idle=filetime(idle) if got else None,
            total_cpu=filetime(kernel) + filetime(user) if got else None,
            ram_total_mib=memory.ullTotalPhys / MIB if got_memory else None,
            ram_used_mib=(memory.ullTotalPhys - memory.ullAvailPhys) / MIB if got_memory else None)

    def listeners(self):
        size = W.DWORD()
        result = self.ip.GetExtendedTcpTable(None, C.byref(size), False, 2, 3, 0)
        if result not in (0, 122) or size.value > 4 * MIB:
            raise OSError(result, 'Listening socket table unavailable')
        raw = C.create_string_buffer(size.value)
        result = self.ip.GetExtendedTcpTable(raw, C.byref(size), False, 2, 3, 0)
        if result:
            raise OSError(result, 'Listening socket table unavailable')
        count = C.cast(raw, C.POINTER(W.DWORD)).contents.value
        rows = C.cast(C.addressof(raw) + C.sizeof(W.DWORD), C.POINTER(TCPROW))
        result = defaultdict(list)
        for index in range(count):
            row = rows[index]
            port = socket.ntohs(row.local_port & 0xffff)
            address = socket.inet_ntoa(int(row.local_addr).to_bytes(4, 'little'))
            result[port].append(dict(pid=int(row.pid), address=address))
        return dict(result)


class PDHValue(C.Structure):
    _fields_ = [('status', W.DWORD), ('value', C.c_double)]


class PDHItem(C.Structure):
    _fields_ = [('name', W.LPWSTR), ('value', PDHValue)]


class GpuCounters:
    """Language-neutral WDDM performance counters, a single persistent query."""
    def __init__(self):
        self.query = W.HANDLE(); self.handles = {}; self.error = ''
        try:
            self.dll = C.WinDLL('pdh')
            self.dll.PdhOpenQueryW.argtypes = [W.LPCWSTR, C.c_size_t, C.POINTER(W.HANDLE)]
            self.dll.PdhAddEnglishCounterW.argtypes = [W.HANDLE, W.LPCWSTR, C.c_size_t, C.POINTER(W.HANDLE)]
            self.dll.PdhCollectQueryData.argtypes = [W.HANDLE]
            self.dll.PdhGetFormattedCounterArrayW.argtypes = [W.HANDLE, W.DWORD,
                C.POINTER(W.DWORD), C.POINTER(W.DWORD), C.c_void_p]
            self.dll.PdhCloseQuery.argtypes = [W.HANDLE]
            self._check(self.dll.PdhOpenQueryW(None, 0, C.byref(self.query)))
            for name, path in dict(engines=r'\GPU Engine(*)\Utilization Percentage',
                                  memory=r'\GPU Process Memory(*)\Dedicated Usage').items():
                handle = W.HANDLE()
                status = self.dll.PdhAddEnglishCounterW(self.query, path, 0, C.byref(handle))
                if status == 0:
                    self.handles[name] = handle
            self._check(self.dll.PdhCollectQueryData(self.query))
        except Exception as error:
            self.error = str(error)[:120]

    @staticmethod
    def _check(status):
        if status:
            raise OSError(status & 0xffffffff, 'WDDM counter unavailable')

    def sample(self):
        if self.error or not self.query:
            return dict(available=False, error=self.error)
        try:
            self._check(self.dll.PdhCollectQueryData(self.query))
            result = dict(available=True)
            for name, handle in self.handles.items():
                size, count = W.DWORD(), W.DWORD()
                status = self.dll.PdhGetFormattedCounterArrayW(handle, 0x200 | 0x8000,
                    C.byref(size), C.byref(count), None)
                if (status & 0xffffffff) != 0x800007d2 or not 0 < size.value < 16 * MIB:
                    result[name] = None
                    continue
                raw = C.create_string_buffer(size.value)
                self._check(self.dll.PdhGetFormattedCounterArrayW(handle, 0x200 | 0x8000,
                    C.byref(size), C.byref(count), raw))
                items = C.cast(raw, C.POINTER(PDHItem))
                result[name] = {items[i].name:items[i].value.value for i in range(count.value)
                    if items[i].value.status in (0, 1) and finite(items[i].value.value) is not None}
            return result
        except Exception as error:
            return dict(available=False, error=str(error)[:120])

    def close(self):
        if self.query:
            self.dll.PdhCloseQuery(self.query); self.query = W.HANDLE()


def nvidia_snapshot():
    fields = 'index,name,utilization.gpu,memory.used,memory.total,temperature.gpu'
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=' + fields, '--format=csv,noheader,nounits'],
            capture_output=True, timeout=1.0, creationflags=NO_WINDOW)
        if result.returncode:
            raise ValueError('NVIDIA telemetry unavailable')
        cards = []
        for line in result.stdout.decode('utf-8', 'replace').splitlines():
            values = [part.strip() for part in line.split(',')]
            if len(values) == 6:
                cards.append(dict(index=values[0], name=values[1], gpu_pct=finite(values[2]),
                    memory_used_mib=finite(values[3]), memory_total_mib=finite(values[4]),
                    temperature_c=finite(values[5])))
        return dict(available=bool(cards), cards=cards)
    except (OSError, ValueError, subprocess.SubprocessError):
        return dict(available=False, cards=[])


def command_task_roots(project=PROJECT):
    """Read only Python command metadata; immediately discard command strings."""
    command = r'''[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$tasks = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'pythonw.exe'" |
 ForEach-Object { [pscustomobject]@{pid=[int]$_.ProcessId;command=$_.CommandLine;birth=$_.CreationDate.ToFileTimeUtc()} })
$services = @(Get-CimInstance Win32_Service -Property Name,DisplayName,State,ProcessId,StartMode |
 ForEach-Object { [pscustomobject]@{unit=$_.Name;name=$_.DisplayName;state=$_.State;pid=[int]$_.ProcessId;mode=$_.StartMode} })
@{tasks=$tasks;services=$services} | ConvertTo-Json -Depth 4 -Compress'''
    roots = {kind: set() for kind in ('tts', 'host', 'monitor', 'project')}
    births = {}
    try:
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
            capture_output=True, timeout=3.5, creationflags=NO_WINDOW)
        if result.returncode or len(result.stdout) > MIB:
            raise ValueError()
        value = json.loads(result.stdout.decode('utf-8-sig'))
        rows = value['tasks']
        project_name = str(project).replace('\\', '/').casefold()
        for row in rows:
            text = str(row.get('command') or '').replace('\\', '/').casefold()
            if project_name not in text or type(row.get('pid')) is not int:
                continue
            pid = row['pid']
            if type(row.get('birth')) is not int:
                continue
            births[pid] = row['birth'] / 10_000_000
            if re.search(r'/omnivoice_voice\.py(?:\s|\"|$)', text):
                roots['tts'].add(pid)
            elif re.search(r'/(?:production_runtime|model_candidate_runner|model_inference_host)\.py(?:\s|\"|$)', text):
                roots['host'].add(pid)
            elif re.search(r'/model_runtime_dashboard\.py(?:\s|\"|$)', text):
                roots['monitor'].add(pid)
            else:
                roots['project'].add(pid)
        return dict(available=True, roots=roots, births=births, services=value['services'])
    except (OSError, ValueError, subprocess.SubprocessError, TypeError, KeyError):
        return dict(available=False, roots=roots, births={}, services=None)


def local_json(address, port, path):
    """Hardcoded local GET metadata routes only; no proxies or model request."""
    if address not in ('127.0.0.1', '192.168.50.1') or path not in ('/health', '/api/ps'):
        raise ValueError('Only the known local observer endpoints are allowed')
    began = time.monotonic()
    connection = http.client.HTTPConnection(address, port, timeout=.45)
    try:
        connection.request('GET', path, headers={'Connection':'close'})
        response = connection.getresponse()
        raw = response.read(256 * 1024 + 1)
        if len(raw) > 256 * 1024:
            raise ValueError('Health metadata exceeded its bound')
        if response.status != 200:
            return dict(ok=False, status=response.status, rtt_ms=(time.monotonic()-began)*1000)
        value = json.loads(raw)
        return dict(ok=True, status=200, data=value, rtt_ms=(time.monotonic()-began)*1000)
    except (OSError, ValueError, http.client.HTTPException):
        return dict(ok=False, status=None, rtt_ms=None)
    finally:
        connection.close()


def nonnegative_count(value, maximum=(1 << 53) - 1):
    # bool is an int subclass; accepting it would invent a task or completion.
    return value if type(value) is int and 0 <= value <= maximum else None


def health_metadata(response):
    """Project the known model-only health schema into bounded scalar telemetry.

    Missing fields stay unknown. An empty *present* Counter dict on the known
    healthy host means zero occurrences, whereas absent/invalid health does not.
    No lease tokens, request IDs, arbitrary counters or full backend data escape.
    """
    result = dict(available=False, active=None, pending=None, counters={}, tts_ready=None,
        gpu_active={'llm':None,'tts':None}, gpu_queued=None, gpu_last_wait_ms=None)
    if not isinstance(response,dict) or response.get('ok') is not True:
        return result
    host = response.get('data')
    if (not isinstance(host,dict) or host.get('ok') is not True
            or host.get('role') != 'model_inference_only'
            or type(host.get('protocol_version')) is not int or host['protocol_version'] != 1):
        return result
    result['available'] = True
    result['active'] = host.get('active') if type(host.get('active')) is bool else None
    result['pending'] = nonnegative_count(host.get('pending'),4096)
    counts = host.get('counts')
    if isinstance(counts,dict):
        for key in ('accepted_llm','accepted_tts','completed','failed','cancelled','deadline_exceeded'):
            value = nonnegative_count(counts[key]) if key in counts else 0
            if value is not None:
                result['counters'][key] = value
    backend = host.get('backend')
    if not isinstance(backend,dict):
        return result
    if type(backend.get('tts_ready')) is bool:
        result['tts_ready'] = backend['tts_ready']
    gpu = backend.get('gpu_coordination')
    if not isinstance(gpu,dict):
        return result
    active = gpu.get('active')
    if isinstance(active,dict):
        result['gpu_active'] = {key:nonnegative_count(active.get(key),4096) for key in ('llm','tts')}
    result['gpu_queued'] = nonnegative_count(gpu.get('queued'),4096)
    wait = gpu.get('last_wait_ms')
    if type(wait) in (int,float) and finite(wait) is not None and wait >= 0:
        result['gpu_last_wait_ms'] = float(wait)
    return result


def phase_summary(telemetry):
    phases = telemetry.get('gpu_active',{})
    llm,tts = phases.get('llm'),phases.get('tts')
    llm = type(llm) is int and llm > 0
    tts = type(tts) is int and tts > 0
    if llm and tts:return 'LLM 推理 / TTS 合成中','busy'
    if llm:return 'LLM 推理中','busy'
    if tts:return 'TTS 合成中','busy'
    if telemetry.get('active') is True:return '处理 / 等待资源','busy'
    if telemetry.get('active') is False:return '当前待机','ready'
    return '任务遥测未提供','online'


def task_phase_state(task, telemetry, fallback):
    value = telemetry.get('gpu_active',{}).get(task)
    if task in ('llm','tts') and type(value) is int and value > 0:
        return ('LLM 推理中' if task == 'llm' else 'TTS 合成中'),'busy'
    if task == 'host' and telemetry.get('available'):
        text,kind = phase_summary(telemetry)
        return ('在线 · 待机' if text == '当前待机' else text),kind
    return fallback


TASKS = [
    ('llm', '27B · 语言模型', '对话生成 / 空闲记忆压缩', 11435, '#9c9aff'),
    ('tts', 'OmniVoice · 语音合成', '将回复文字合成为声音', None, '#60d9c0'),
    ('host', '模型请求调度', '接收板端请求 / 排队 / 取消', 8797, '#69baff'),
    ('portrait', '形象画面服务', '当前 Windows 画面输出实例', 8796, '#e9b06d'),
    ('other', '其他 Ollama 实例', '独立服务 · 保留原运行状态', 11434, '#899cb8'),
    ('legacy', '早期业务服务', '旧版服务端口 8791 / 8792 / 8795', None, '#a0a5b4'),
    ('monitor', '性能观测台', '双端遥测与显示，含 SSH 采集客户端', None, '#55c8bc'),
    ('project', '其他项目进程', '项目路径内的其他 Python 任务及子进程', None, '#a6b3c7'),
]


def model_detail(host_response, ps_response, expected_model):
    """Project the model host and the *matching* Ollama instance independently."""
    host = (host_response or {}).get('data', {}) if health_metadata(host_response)['available'] else {}
    def mapping(value):
        return value if isinstance(value, dict) else {}
    backend = mapping(host.get('backend'))
    policy = mapping(backend.get('gpu_coordination'))
    voice = mapping(backend.get('voice'))
    ps_data = (ps_response or {}).get('data')
    models = ps_data.get('models') if isinstance(ps_data, dict) else None
    known = (ps_response or {}).get('ok') is True and isinstance(models, list) and bool(expected_model)
    match = next((row for row in models if isinstance(row, dict) and row.get('name') == expected_model), None) if known else None
    instance = match or {}
    details = mapping(instance.get('details'))

    def flag(doc, key):
        value = doc.get(key) if isinstance(doc, dict) else None
        return value if type(value) is bool else None

    def label(doc, key):
        value = doc.get(key) if isinstance(doc, dict) else None
        return value if isinstance(value, str) and re.fullmatch(r'[\w./:+ -]{1,128}', value, re.ASCII) else None

    def number(doc, key):
        value = doc.get(key) if isinstance(doc, dict) else None
        return value if type(value) in (int, float) and finite(value) is not None and value >= 0 else None

    stats = mapping(policy.get('tts_stats'))
    inference = stats.get('last_inference') or {}
    gpu_counts = policy.get('counts') or {}
    tts_counts = policy.get('tts_counts')
    def tts_count(key):
        return nonnegative_count(tts_counts.get(key, 0)) if isinstance(tts_counts, dict) else None
    warm_runs, cold_runs = tts_count('generated'), tts_count('cold_generated')
    return dict(expected_model=expected_model, reported_model=label(backend, 'model'), resident=bool(match) if known else None,
                parameter_size=label(details, 'parameter_size'), quantization=label(details, 'quantization_level'),
                format=label(details, 'format'), runner=label(instance, 'runner'), instance_context=number(instance, 'context_length'),
                model_bytes=number(instance, 'size'), gpu_bytes=number(instance, 'size_vram'),
                context_limit=number(backend, 'context_limit'), tts=label(backend, 'tts'), steps=number(backend, 'num_step'),
                tts_alive=flag(voice, 'alive'), tts_request=flag(voice, 'request_active'),
                tts_ready=flag(backend, 'tts_ready'), tts_quarantined=flag(voice, 'quarantined'),
                mode=label(policy, 'mode'), enforcing=flag(policy, 'enforcing'), queue_limit=number(policy, 'queue_limit'),
                max_wait_ms=number(policy, 'max_wait_ms'), last_reason=label(policy, 'last_reason'),
                llm_admitted=number(gpu_counts, 'llm_admitted'), tts_admitted=number(gpu_counts, 'tts_admitted'),
                tts_generated=warm_runs + cold_runs if None not in (warm_runs, cold_runs) else None,
                tts_cold_generated=cold_runs, tts_cache_hits=tts_count('cache_hit'), tts_warmup=tts_count('warmup'),
                previous_reserved_peak_bytes=number(inference, 'peak_reserved_bytes'),
                previous_extra_peak_bytes=number(inference, 'reserved_extra_peak_bytes'),
                host_queue_limit=number(host.get('limits'), 'max_pending'))


def process_gpu(gpu):
    by_engine, memory = defaultdict(lambda: defaultdict(float)), defaultdict(float)
    for name, value in (gpu.get('engines') or {}).items():
        match = re.fullmatch(r'pid_(\d+)_(.+?)(?:#\d+)?', name)
        if match:
            by_engine[int(match[1])][match[2]] += max(0, value)
    for name, value in (gpu.get('memory') or {}).items():
        match = re.match(r'pid_(\d+)_', name)
        if match:
            memory[int(match[1])] += max(0, value) / MIB
    return {pid: min(100., max(values.values())) for pid, values in by_engine.items()}, memory


class Sampler:
    def __init__(self):
        self.reader = WindowsReader(); self.gpu = GpuCounters()
        self.previous = {}; self.last_system = None; self.last_at = None
        self.command_at = -math.inf; self.commands = dict(available=False, roots={}, births={})
        try:
            self.expected_model = json.loads((PROJECT / 'aura/config/board_dialogue_model.json').read_bytes())['model']
        except (ValueError, KeyError, OSError):
            self.expected_model = None
        self.pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='read-only-metadata')

    def sample(self):
        began = time.monotonic()
        processes = self.reader.processes(); listeners = self.reader.listeners()
        if began - self.command_at >= 10:
            self.commands = command_task_roots(); self.command_at = began
        usages = {pid: self.reader.process_usage(pid) for pid in processes}
        for pid, usage in usages.items():
            if usage:
                processes[pid]['birth'] = usage['birth']
        roots = {key: {pid for pid in values if usages.get(pid)
                       and abs(usages[pid]['birth'] - self.commands['births'][pid]) < .001}
                 for key, values in self.commands['roots'].items()}
        roots.setdefault('monitor', set()).add(os.getpid())
        for key, _, _, port, _ in TASKS:
            if port:
                roots.setdefault(key,set()).update(row['pid'] for row in listeners.get(port,()))
        roots['legacy'] = {row['pid'] for port in (8791,8792,8795) for row in listeners.get(port,())}
        groups = exclusive_groups(roots, processes)
        gpu = self.gpu.sample()
        nvidia_future = self.pool.submit(nvidia_snapshot)
        futures = {}
        for key, port, path in (('llm',11435,'/api/ps'),('other',11434,'/api/ps'),('host',8797,'/health')):
            if port in listeners:
                address = listeners[port][0]['address']
                address = '127.0.0.1' if address in ('0.0.0.0','127.0.0.1') else address
                if address in ('127.0.0.1','192.168.50.1'):
                    futures[key] = self.pool.submit(local_json,address,port,path)
        monitor = usages.get(os.getpid())
        system = self.reader.system(); now = time.monotonic()
        elapsed = now - self.last_at if self.last_at is not None else None
        cpu_by_pid = {}
        for pid, usage in usages.items():
            if usage:
                old = self.previous.get(pid)
                prior = old['cpu_seconds'] if old and old['birth'] == usage['birth'] else None
                cpu_by_pid[pid] = percent_delta(prior, usage['cpu_seconds'], elapsed or 0, os.cpu_count() or 1)
        health = {key:future.result(timeout=1.0) for key,future in futures.items()}
        telemetry = health_metadata(health.get('host'))
        model = model_detail(health.get('host'), health.get('llm'), self.expected_model)
        rows = []
        for key, name, description, port, color in TASKS:
            members = groups[key]
            values = [usages[pid] for pid in members if usages.get(pid)]
            online = bool(listeners.get(port)) if port else bool(members)
            status, kind = ('运行中', 'online') if members else ('未运行', 'offline')
            ownership_unknown = not members and key in ('tts', 'project') and not self.commands['available']
            if ownership_unknown:
                status, kind = '归属待确认', 'limited'
            detail = health.get(key, {})
            model_names = []
            if key in ('llm','other') and detail.get('ok') and isinstance(detail.get('data', {}).get('models'), list):
                model_names = [str(row.get('name',''))[:96] for row in detail['data'].get('models',())
                               if isinstance(row,dict)]
                resident = model['resident'] if key == 'llm' else bool(model_names)
                status = '模型已驻留' if resident else '在线 · 模型未驻留' if resident is False else '在线 · 驻留未知'
                kind = 'ready' if resident else 'online'
            elif key == 'host' and detail.get('ok'):
                status,kind = '在线 · 状态未提供','online'
            elif key == 'host' and detail.get('status') == 403:
                status, kind = '在线 · 遥测受限', 'limited'
            elif online and port:
                status = '监听中' if not detail else '监听中 · 检查未通过'
            if key == 'tts':
                if model['tts_ready'] is True:
                    status, kind = '模型就绪', 'ready'
                    ownership_unknown = not members
                elif model['tts_alive'] is True or members:
                    status = '进程运行 · 预备中' if model['tts_ready'] is False else '进程运行 · 就绪未知'
                    kind = 'online'
                    ownership_unknown = not members
            status,kind = task_phase_state(key,telemetry,(status,kind))
            valid_cpu = [cpu_by_pid[pid] for pid in members if cpu_by_pid.get(pid) is not None]
            memory = [value['rss_mib'] for value in values if value.get('rss_mib') is not None]
            private = [value['private_mib'] for value in values if value.get('private_mib') is not None]
            gpu_pct = engine_usage(gpu['engines'],members) if gpu.get('engines') is not None else None
            vram = None
            if gpu.get('memory') is not None:
                vram=sum(value for item,value in gpu['memory'].items()
                    if re.match(r'pid_(\d+)_',item) and int(re.match(r'pid_(\d+)_',item)[1]) in members) / MIB
            rows.append(dict(id=key,name=name,description=description,port=port,color=color,
                pids=sorted(members),state=status,state_kind=kind,online=online,
                cpu_pct=sum(valid_cpu) if not ownership_unknown and len(valid_cpu)==len(members) else None,
                rss_mib=sum(memory) if not ownership_unknown and len(memory)==len(members) else None,
                private_mib=sum(private) if not ownership_unknown and len(private)==len(members) else None,
                gpu_pct=None if ownership_unknown else gpu_pct,vram_mib=None if ownership_unknown else vram,
                models=model_names,health_rtt_ms=detail.get('rtt_ms'),
                uptime_seconds=max((time.time()-(value['birth']-11644473600) for value in values),default=None),
                sampled_pids=len(values),process_count=len(members)))
        total_cpu = None
        if self.last_system and self.last_system['total_cpu'] is not None and system['total_cpu'] is not None:
            total = system['total_cpu'] - self.last_system['total_cpu']
            idle = system['idle'] - self.last_system['idle']
            if total > 0:
                total_cpu = max(0.0,min(100.0,(total-idle)/total*100))
        self.previous={pid:value for pid,value in usages.items() if value}
        self.last_at=now;self.last_system=system
        # Strict whitelist. No full health bodies, request IDs or commands leave the sampler.
        nvidia=nvidia_future.result(timeout=1.3)
        group_for_pid = {pid: key for key, members in groups.items() for pid in members}
        utilization, dedicated = process_gpu(gpu)
        inventory = []
        for pid, info in processes.items():
            usage = usages.get(pid) or {}
            inventory.append(dict(pid=pid, ppid=info['ppid'], name=info['name'], threads=info['threads'],
                                  role=group_for_pid.get(pid, ''), cpu_pct=cpu_by_pid.get(pid),
                                  birth=usage.get('birth'), rss_mib=usage.get('rss_mib'), private_mib=usage.get('private_mib'),
                                  gpu_pct=utilization.get(pid, 0.) if gpu.get('engines') is not None else None,
                                  vram_mib=dedicated.get(pid, 0.) if gpu.get('memory') is not None else None))
        return dict(schema=2,local_time=dt.datetime.now().astimezone().isoformat(),monotonic=now,
            sample_ms=round((time.monotonic()-began)*1000,1),logical_cpus=os.cpu_count(),tasks=rows,
            processes=inventory, model_detail=model,
            services=self.commands.get('services'),
            system_cpu_pct=total_cpu,ram_total_mib=system['ram_total_mib'],ram_used_mib=system['ram_used_mib'],
            nvidia=nvidia,wddm_available=gpu.get('engines') is not None,
            wddm_memory_available=gpu.get('memory') is not None,command_probe_available=self.commands['available'],
            pending=telemetry['pending'],active=telemetry['active'],counters=telemetry['counters'],
            gpu_active=telemetry['gpu_active'],gpu_queued=telemetry['gpu_queued'],
            gpu_last_wait_ms=telemetry['gpu_last_wait_ms'],model_health_available=telemetry['available'],
            legacy_ports=[port for port in (8791,8792,8795) if port in listeners],
            monitor_rss_mib=monitor['rss_mib'] if monitor else None,
            privacy='process and model metadata only; no prompt/audio/database; last-minute RAM history')

    def close(self):
        self.gpu.close();self.pool.shutdown(wait=False,cancel_futures=True)


def fmt(value,suffix='',digits=1):
    return '—' if value is None else f'{value:,.{digits}f}{suffix}'


def memory_text(value):
    if value is None:return '—'
    return f'{value/1024:.2f} GiB' if value>=1024 else f'{value:.0f} MiB'


def capture_window(root,path):
    """Capture only this application's own HWND, never the whole desktop."""
    from PIL import Image
    root.update_idletasks()
    user=C.WinDLL('user32');gdi=C.WinDLL('gdi32')
    user.GetAncestor.argtypes=[W.HWND,W.UINT];user.GetAncestor.restype=W.HWND
    user.GetWindowRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
    user.GetWindowDC.argtypes=[W.HWND];user.GetWindowDC.restype=W.HDC
    user.ReleaseDC.argtypes=[W.HWND,W.HDC]
    gdi.CreateCompatibleDC.argtypes=[W.HDC];gdi.CreateCompatibleDC.restype=W.HDC
    gdi.CreateCompatibleBitmap.argtypes=[W.HDC,C.c_int,C.c_int];gdi.CreateCompatibleBitmap.restype=W.HBITMAP
    gdi.SelectObject.argtypes=[W.HDC,W.HGDIOBJ];gdi.SelectObject.restype=W.HGDIOBJ
    gdi.DeleteObject.argtypes=[W.HGDIOBJ];gdi.DeleteDC.argtypes=[W.HDC]
    user.PrintWindow.argtypes=[W.HWND,W.HDC,W.UINT]
    gdi.GetDIBits.argtypes=[W.HDC,W.HBITMAP,W.UINT,W.UINT,C.c_void_p,C.c_void_p,W.UINT]
    hwnd=user.GetAncestor(root.winfo_id(),2);rect=W.RECT();user.GetWindowRect(hwnd,C.byref(rect))
    width,height=rect.right-rect.left,rect.bottom-rect.top
    dc=user.GetWindowDC(hwnd);mem=gdi.CreateCompatibleDC(dc);bmp=gdi.CreateCompatibleBitmap(dc,width,height)
    old=gdi.SelectObject(mem,bmp)
    try:
        if not user.PrintWindow(hwnd,mem,2):raise OSError('Own-window capture unavailable')
        header=C.create_string_buffer(40);C.cast(header,C.POINTER(W.DWORD))[0]=40
        C.cast(header,C.POINTER(C.c_long))[1]=width;C.cast(header,C.POINTER(C.c_long))[2]=-height
        C.cast(C.addressof(header)+12,C.POINTER(W.WORD))[0]=1
        C.cast(C.addressof(header)+14,C.POINTER(W.WORD))[0]=32
        raw=C.create_string_buffer(width*height*4)
        if not gdi.GetDIBits(mem,bmp,0,height,raw,header,0):raise OSError('Own-window pixels unavailable')
        target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
        Image.frombytes('RGB',(width,height),raw.raw,'raw','BGRX').save(target)
    finally:
        gdi.SelectObject(mem,old);gdi.DeleteObject(bmp);gdi.DeleteDC(mem);user.ReleaseDC(hwnd,dc)



def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,help='Write a sanitized 3-sample real counter proof; no GUI')
    parser.add_argument('--screenshot',type=Path,help='Save this own GUI window after 3 real samples')
    parser.add_argument('--close-after',type=float,default=0,help='Bound a GUI verification run in seconds')
    parser.add_argument('--view', choices=('overview', 'windows', 'board', 'inventory'), default='overview')
    args=parser.parse_args(argv)
    if args.close_after and not 4<=args.close_after<=3600:parser.error('Use 4–3600 seconds for bounded GUI verification')
    if args.snapshot:
        from runtime_board_monitor import BoardSampler
        sampler=Sampler();board=BoardSampler();values=[]
        try:
            for _ in range(3):
                began=time.monotonic()
                value=sampler.sample()
                value['board']=board.sample()
                values.append(value)
                time.sleep(max(0,INTERVAL-(time.monotonic()-began)))
        finally:
            board.close()
            sampler.close()
        args.snapshot.parent.mkdir(parents=True,exist_ok=True)
        args.snapshot.write_text(json.dumps(dict(status='ACTUAL_READ_ONLY_COUNTERS',samples=values),ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(dict(output=str(args.snapshot),samples=len(values))))
        return
    import tkinter as tk
    from runtime_dashboard_ui import Dashboard
    user=C.WinDLL('user32')
    try:user.SetProcessDPIAware()
    except AttributeError:pass
    kernel=C.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=[C.c_void_p,W.BOOL,W.LPCWSTR];kernel.CreateMutexW.restype=W.HANDLE
    kernel.CloseHandle.argtypes=[W.HANDLE]
    C.set_last_error(0)
    preview = bool(args.screenshot and args.close_after)
    lock_name = r'Local\AuraModelRuntimeDashboard-v1' + (f'-preview-{os.getpid()}' if preview else '')
    mutex=kernel.CreateMutexW(None,False,lock_name)
    if not mutex:raise OSError(C.get_last_error(),'Dashboard single-instance lock unavailable')
    existing=C.get_last_error()==183
    try:
        if existing:
            user.FindWindowW.argtypes=[W.LPCWSTR,W.LPCWSTR];user.FindWindowW.restype=W.HWND
            user.ShowWindow.argtypes=[W.HWND,C.c_int];user.SetForegroundWindow.argtypes=[W.HWND]
            hwnd=user.FindWindowW(None,TITLE)
            if hwnd:user.ShowWindow(hwnd,9);user.SetForegroundWindow(hwnd)
            return
        root=tk.Tk()
        Dashboard(root,args,Sampler,capture_window,TITLE + (' · 预览' if preview else ''))
        root.mainloop()
    finally:kernel.CloseHandle(mutex)


if __name__=='__main__':main()
