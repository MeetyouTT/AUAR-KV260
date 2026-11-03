"""Read-only Windows model/process dashboard. No third-party dependencies.

Only local process counters, listening sockets, GPU counters and GET health /
Ollama residency metadata are observed. Prompt text, audio and databases are
never read. The last minute of metric samples lives only in this process RAM.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
import ctypes as C
from ctypes import wintypes as W
from dataclasses import dataclass
import datetime as dt
import http.client
import json
import math
import os
from pathlib import Path
import queue
import re
import socket
import subprocess
import sys
import threading
import time

TITLE = 'AURA · 模型运行观测台'
PROJECT = Path(__file__).resolve().parents[2]
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
                 if value['ppid'] in selected and pid not in selected}
        if not added:
            return selected
        selected.update(added)


def exclusive_groups(roots, processes):
    """Specific model groups own children before the orchestration group."""
    result, claimed = {}, set()
    for name in ('llm', 'tts', 'other', 'portrait', 'host', 'legacy'):
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
                values[int(row.th32ProcessID)] = dict(ppid=int(row.th32ParentProcessID), name=row.szExeFile)
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
@(Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'pythonw.exe'" |
 ForEach-Object { [pscustomobject]@{pid=[int]$_.ProcessId;command=$_.CommandLine} }) |
 ConvertTo-Json -Depth 2 -Compress'''
    roots = dict(tts=set(), host=set())
    try:
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
            capture_output=True, timeout=2.5, creationflags=NO_WINDOW)
        if result.returncode or len(result.stdout) > MIB:
            raise ValueError()
        value = json.loads(result.stdout.decode('utf-8-sig'))
        rows = value if isinstance(value, list) else [value]
        project_name = str(project).replace('\\', '/').casefold()
        for row in rows:
            text = str(row.get('command') or '').replace('\\', '/').casefold()
            if project_name not in text or type(row.get('pid')) is not int:
                continue
            if re.search(r'/omnivoice_voice\.py(?:\s|\")', text):
                roots['tts'].add(row['pid'])
            if re.search(r'/(?:model_candidate_runner|model_inference_host)\.py(?:\s|\")', text):
                roots['host'].add(row['pid'])
        return dict(available=True, roots=roots)
    except (OSError, ValueError, subprocess.SubprocessError, TypeError):
        return dict(available=False, roots=roots)


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
]


class Sampler:
    def __init__(self):
        self.reader = WindowsReader(); self.gpu = GpuCounters()
        self.previous = {}; self.last_system = None; self.last_at = None
        self.command_at = -math.inf; self.commands = dict(available=False, roots={})
        self.pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='read-only-metadata')

    def sample(self):
        began = time.monotonic()
        processes = self.reader.processes(); listeners = self.reader.listeners()
        if began - self.command_at >= 10:
            self.commands = command_task_roots(); self.command_at = began
        roots = {key:set(values) for key,values in self.commands['roots'].items()}
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
        usages = {pid:self.reader.process_usage(pid) for group in groups.values() for pid in group}
        monitor = self.reader.process_usage(os.getpid())
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
        rows = []
        for key, name, description, port, color in TASKS:
            members = groups[key]
            values = [usages[pid] for pid in members if usages.get(pid)]
            online = bool(listeners.get(port)) if port else bool(members)
            status, kind = ('运行中', 'online') if members else ('未运行', 'offline')
            detail = health.get(key, {})
            model_names = []
            if key in ('llm','other') and detail.get('ok'):
                model_names = [str(row.get('name',''))[:96] for row in detail['data'].get('models',())
                               if isinstance(row,dict)]
                status = '模型已驻留' if model_names else '在线 · 模型未驻留'
                kind = 'ready' if model_names else 'online'
            elif key == 'host' and detail.get('ok'):
                status,kind = '在线 · 状态未提供','online'
            elif key == 'host' and detail.get('status') == 403:
                status, kind = '在线 · 遥测受限', 'limited'
            elif online and port:
                status = '监听中' if not detail else '监听中 · 检查未通过'
            if key == 'tts' and members:
                if telemetry['tts_ready'] is True:
                    status,kind = '模型就绪','ready'
                else:
                    status,kind = '进程运行 · 就绪未知','online'
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
                cpu_pct=sum(valid_cpu) if len(valid_cpu)==len(members) else None,
                rss_mib=sum(memory) if len(memory)==len(members) else None,
                private_mib=sum(private) if len(private)==len(members) else None,
                gpu_pct=gpu_pct,vram_mib=vram,models=model_names,health_rtt_ms=detail.get('rtt_ms'),
                uptime_seconds=max((time.time()-(value['birth']-11644473600) for value in values),default=None),
                sampled_pids=len(values),process_count=len(members)))
        total_cpu = None
        if self.last_system and system['total_cpu'] is not None:
            total = system['total_cpu'] - self.last_system['total_cpu']
            idle = system['idle'] - self.last_system['idle']
            if total > 0:
                total_cpu = max(0.0,min(100.0,(total-idle)/total*100))
        self.previous={pid:value for pid,value in usages.items() if value}
        self.last_at=now;self.last_system=system
        # Strict whitelist. No full health bodies, request IDs or commands leave the sampler.
        nvidia=nvidia_future.result(timeout=1.3)
        return dict(schema=1,local_time=dt.datetime.now().astimezone().isoformat(),monotonic=now,
            sample_ms=round((time.monotonic()-began)*1000,1),logical_cpus=os.cpu_count(),tasks=rows,
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
    return f'{value/1024:.2f} GB' if value>=1024 else f'{value:.0f} MB'


class Dashboard:
    BG='#0b1220'; PANEL='#121d2e'; LINE='#243249'; TEXT='#e8eef8'; MUTED='#8a9bb5'
    def __init__(self,root,args):
        import tkinter as tk
        self.tk=tk;self.root=root;self.args=args
        root.title(TITLE);root.configure(bg=self.BG);root.geometry('1370x870');root.minsize(1160,760)
        self.canvas=tk.Canvas(root,bg=self.BG,highlightthickness=0);self.canvas.pack(fill='both',expand=True)
        self.history=deque();self.data=None;self.error='';self.paused=False;self.fullscreen=False
        self.samples=queue.Queue(maxsize=1);self.stop=threading.Event();self.selected='llm'
        self.started=time.monotonic();self.last_paint=0.;self.rects={}
        self.canvas.bind('<Configure>',lambda _:self.paint())
        self.canvas.bind('<Button-1>',self.click)
        root.bind('<F11>',lambda _:self.toggle_fullscreen());root.bind('<Escape>',lambda _:self.leave_fullscreen())
        root.protocol('WM_DELETE_WINDOW',self.close)
        self.worker=threading.Thread(target=self.collect,name='windows-model-observer',daemon=True);self.worker.start()
        self.root.after(100,self.tick)
        if args.close_after:self.root.after(int(args.close_after*1000),self.close)
        root.after(200,root.deiconify)

    def collect(self):
        sampler=None
        try:
            sampler=Sampler()
            while not self.stop.is_set():
                began=time.monotonic()
                try:value=dict(data=sampler.sample(),error='')
                except Exception as error:value=dict(data=None,error=type(error).__name__+'：'+str(error)[:100])
                try:self.samples.get_nowait()
                except queue.Empty:pass
                self.samples.put_nowait(value)
                self.stop.wait(max(.1,INTERVAL-(time.monotonic()-began)))
        finally:
            if sampler:sampler.close()

    def tick(self):
        try:
            item=self.samples.get_nowait();self.error=item['error']
            if item['data']:
                if not self.paused:
                    self.data=item['data'];self.history.append(self.data)
                    while self.history and self.data['monotonic']-self.history[0]['monotonic']>60:self.history.popleft()
            self.paint()
        except queue.Empty:pass
        if self.args.screenshot and self.data and len(self.history)>=3:
            target=self.args.screenshot;self.args.screenshot=None
            self.root.after(200,lambda:self.screenshot(target))
        if not self.stop.is_set():self.root.after(150,self.tick)

    def text(self,x,y,text,size=11,color=None,weight='normal',anchor='nw',**kw):
        return self.canvas.create_text(x,y,text=text,anchor=anchor,fill=color or self.TEXT,
            font=('Microsoft YaHei UI',size,weight),**kw)

    def box(self,x,y,w,h,fill=None,outline=None):
        return self.canvas.create_rectangle(x,y,x+w,y+h,fill=fill or self.PANEL,outline=outline or fill or self.PANEL)

    def pill(self,x,y,label,color,bg=None):
        width=max(64,len(label)*12+24);self.box(x,y,width,26,bg or '#1b2b3e')
        self.text(x+12,y+4,label,9,color);return width

    def metric(self,x,y,w,label,value,detail,color,ratio=None):
        self.box(x,y,w,112);self.text(x+20,y+16,label,10,self.MUTED)
        self.text(x+20,y+39,value,26,self.TEXT,'bold');self.text(x+20,y+84,detail,9,self.MUTED)
        self.box(x+20,y+104,w-40,3,'#24324a')
        if ratio is not None:self.box(x+20,y+104,max(0,min(1,ratio))*(w-40),3,color)

    def paint(self):
        c=self.canvas;c.delete('all');width=max(1160,c.winfo_width());height=max(760,c.winfo_height())
        self.rects={};nav=148;left=nav+30;right=width-30;content=right-left
        self.box(0,0,nav,height,'#0e192a');self.text(25,28,'AURA',22,'#eef3ff','bold')
        self.text(27,65,'RUNTIME / WINDOWS',7,'#6781a4')
        self.box(16,118,116,40,'#203147');self.text(32,128,'◉  运行总览',11,'#a9c9ff')
        self.text(32,183,'ⓘ  指标说明',10,self.MUTED);self.rects['help']=(16,172,132,211)
        self.text(25,height-108,'只读观测',10,'#6bd6b6');self.text(25,height-80,'不启动推理\n不改变模型状态',8,self.MUTED)
        self.text(left,27,'模型运行观测台',22,weight='bold');self.text(left,66,'查看 Windows 后台任务与实时性能占用',10,self.MUTED)
        self.pill(right-295,29,'暂停显示' if self.paused else 'LIVE · 2 秒','#7ee0bf' if not self.paused else '#e3b978')
        self.rects['pause']=(right-295,29,right-185,55)
        self.pill(right-155,29,'退出全屏' if self.fullscreen else '全屏 F11','#a4b9da');self.rects['full']=(right-155,29,right,55)
        data=self.data;tasks=data['tasks'] if data else []
        running=sum(bool(row['pids']) for row in tasks)
        cpu=data.get('system_cpu_pct') if data else None
        cards=data.get('nvidia',{}).get('cards',[]) if data else []
        card=cards[0] if cards else {};gpu=card.get('gpu_pct')
        ram=data.get('ram_used_mib') if data else None;total=data.get('ram_total_mib') if data else None
        vram=card.get('memory_used_mib');vtotal=card.get('memory_total_mib')
        gap=14;cw=(content-3*gap)/4;y=106
        self.metric(left,y,cw,'正在运行的任务',f'{running} / {len(TASKS)}','按实际进程及监听端口识别','#8b9dff',running/len(TASKS))
        self.metric(left+cw+gap,y,cw,'整机 CPU',fmt(cpu,'%',1),f'{data["logical_cpus"] if data else "—"} 个逻辑处理器 · 总容量 100%','#6fb9ff',cpu/100 if cpu is not None else None)
        self.metric(left+2*(cw+gap),y,cw,'整卡 GPU',fmt(gpu,'%',0),str(card.get('name','NVIDIA 指标暂不可用')).replace('NVIDIA GeForce ','')[:31],'#79ddc1',gpu/100 if gpu is not None else None)
        self.metric(left+3*(cw+gap),y,cw,'整卡显存',memory_text(vram),f'总计 {memory_text(vtotal)} · NVIDIA 采样','#b49aff',vram/vtotal if vram is not None and vtotal else None)
        table_y=244;table_w=content*.73;side_x=left+table_w+18;side_w=right-side_x
        self.text(left,table_y,'后台任务',13,weight='bold');self.text(left+110,table_y+3,'点击任务查看详情',9,self.MUTED)
        self.text(left+table_w,table_y+3,'CPU 为整机归一化占比',9,self.MUTED,anchor='ne')
        hy=table_y+38;self.box(left,hy,table_w,34,'#162236')
        columns=[('任务 / 模型',14),('CPU',.48*table_w),('内存',.61*table_w),('GPU',.74*table_w),('显存',.87*table_w)]
        for label,dx in columns:self.text(left+dx,hy+8,label,9,self.MUTED)
        row_h=max(60,min(83,(height-455)/5))
        for index,(key,name,desc,port,color) in enumerate(TASKS):
            row=next((r for r in tasks if r['id']==key),dict(pids=[],state='等待采样',state_kind='offline',cpu_pct=None,rss_mib=None,gpu_pct=None,vram_mib=None))
            ry=hy+34+index*row_h;chosen=self.selected==key
            self.box(left,ry,table_w,row_h-2,'#19283d' if chosen else self.PANEL)
            if chosen:self.box(left,ry,3,row_h-2,color)
            self.box(left+15,ry+20,7,7,color);self.text(left+31,ry+13,name,11,weight='bold')
            state_color={'busy':'#e7bc7c','ready':'#7bd9b9','online':'#91b6e8','limited':'#e0b77a','offline':'#687b96'}.get(row['state_kind'],self.MUTED)
            self.text(left+31,ry+43,row['state'],9,state_color)
            self.text(left+.48*table_w,ry+16,fmt(row['cpu_pct'],'%'),12)
            self.box(left+.48*table_w,ry+49,table_w*.09,3,'#2b3b53')
            if row['cpu_pct'] is not None:self.box(left+.48*table_w,ry+49,table_w*.09*min(1,row['cpu_pct']/100),3,color)
            self.text(left+.61*table_w,ry+18,memory_text(row['rss_mib']),10)
            self.text(left+.74*table_w,ry+18,fmt(row['gpu_pct'],'%'),10)
            self.text(left+.87*table_w,ry+18,memory_text(row['vram_mib']),10)
            self.rects['task:'+key]=(left,ry,left+table_w,ry+row_h-2)
        bottom=hy+34+len(TASKS)*row_h+15
        selected=next((r for r in tasks if r['id']==self.selected),None)
        if selected:
            self.box(left,bottom,table_w,80)
            self.text(left+16,bottom+12,selected['name']+'  /  '+selected['description'],10)
            pids=', '.join(map(str,selected['pids'])) or '未检测到对应进程'
            self.text(left+16,bottom+39,'PID  '+pids,9,self.MUTED)
            port='进程白名单识别' if selected['port'] is None else '端口  '+str(selected['port'])
            self.text(left+table_w-16,bottom+39,port,9,self.MUTED,anchor='ne')
            if selected['models']:self.text(left+16,bottom+60,'驻留：'+', '.join(selected['models'])[:91],8,'#a8b8d0')
            else:
                uptime=selected.get('uptime_seconds')
                runtime='—' if uptime is None else f'{int(uptime)//3600} 小时 {int(uptime)%3600//60} 分钟'
                self.text(left+16,bottom+60,'运行 '+runtime+'   ·   私有内存 '+memory_text(selected.get('private_mib'))+
                    '   ·   健康检查 '+fmt(selected.get('health_rtt_ms'),' ms'),8,'#a8b8d0')
        self.box(side_x,table_y,side_w,254)
        self.text(side_x+17,table_y+16,'最近 60 秒',12,weight='bold');self.text(side_x+17,table_y+44,'整机 CPU / 整卡 GPU',9,self.MUTED)
        gx,gy,gw,gh=side_x+18,table_y+87,side_w-36,124
        for value in (0,50,100):
            yy=gy+gh*(1-value/100);c.create_line(gx,yy,gx+gw,yy,fill=self.LINE)
            self.text(gx+gw,yy-15,str(value)+'%',7,'#5f7492',anchor='ne')
        if len(self.history)>1:
            latest=self.history[-1]['monotonic']
            for key,color in (('cpu','#70baff'),('gpu','#7cdbbd')):
                points=[]
                for item in self.history:
                    value=item['system_cpu_pct'] if key=='cpu' else next(iter(item.get('nvidia',{}).get('cards',[])),{}).get('gpu_pct')
                    if value is not None:
                        points.extend([gx+gw*max(0,1-(latest-item['monotonic'])/60),gy+gh*(1-value/100)])
                if len(points)>=4:c.create_line(*points,fill=color,width=2)
        self.text(gx,gy+gh+15,'— CPU',9,'#70baff');self.text(gx+76,gy+gh+15,'— GPU',9,'#7cdbbd')
        sy=table_y+272;self.box(side_x,sy,side_w,min(220,height-sy-38))
        self.text(side_x+17,sy+16,'运行摘要',12,weight='bold')
        pending=data.get('pending') if data else None
        active=data.get('active') if data else None
        state,state_kind=phase_summary(data or {})
        self.text(side_x+17,sy+51,state,11,'#e9be83' if state_kind=='busy' else '#a7bddb')
        self.text(side_x+17,sy+80,'排队请求',9,self.MUTED);self.text(side_x+side_w-17,sy+80,fmt(pending,'',0),11,anchor='ne')
        counters=data.get('counters',{}) if data else {}
        self.text(side_x+17,sy+106,'完成请求',9,self.MUTED);self.text(side_x+side_w-17,sy+106,fmt(counters.get('completed'),'',0),11,anchor='ne')
        self.text(side_x+17,sy+132,'GPU 资源排队',9,self.MUTED)
        self.text(side_x+side_w-17,sy+132,fmt(data.get('gpu_queued') if data else None,'',0),11,anchor='ne')
        self.text(side_x+17,sy+158,'上次 GPU 资源等待',9,self.MUTED)
        self.text(side_x+side_w-17,sy+158,fmt(data.get('gpu_last_wait_ms') if data else None,' ms',0),10,anchor='ne')
        self.text(side_x+17,sy+188,'内存  '+memory_text(ram)+' / '+memory_text(total),10)
        footer=max(bottom+95,height-51)
        if self.error:self.text(left,footer,self.error,9,'#e5ad79')
        else:
            stamp=data['local_time'][11:19] if data else '等待首轮采样'
            self.text(left,footer,('显示已暂停 · ' if self.paused else '●  ')+stamp+'    仅观测本机 · 最近一分钟保存在内存',9,self.MUTED)
        if data:self.text(right,footer,f'采样 {data["sample_ms"]:.0f} ms · 看板 {memory_text(data["monitor_rss_mib"])}',8,self.MUTED,anchor='ne')

    def click(self,event):
        for key,(x1,y1,x2,y2) in self.rects.items():
            if x1<=event.x<=x2 and y1<=event.y<=y2:
                if key=='pause':self.paused=not self.paused;self.paint()
                elif key=='full':self.toggle_fullscreen()
                elif key=='help':self.help()
                elif key.startswith('task:'):self.selected=key[5:];self.paint()
                break

    def toggle_fullscreen(self):
        self.fullscreen=not self.fullscreen;self.root.attributes('-fullscreen',self.fullscreen);self.paint()

    def leave_fullscreen(self):
        self.fullscreen=False;self.root.attributes('-fullscreen',False);self.paint()

    def help(self):
        from tkinter import messagebox
        messagebox.showinfo('指标说明',
            '任务 CPU：该任务进程组的 CPU 时间增量 ÷ 时间间隔 ÷ 逻辑处理器数。100% 代表整机全部 CPU。\n\n'
            '内存：进程组工作集之和；共享页面可能重复计入。任务进程按监听端口及子进程动态识别，组间不重复计数。\n\n'
            '任务 GPU：WDDM 各物理引擎内先合计本任务上下文，取最忙引擎。任务显存：WDDM 专用显存，可能包含共享分摊。整卡 GPU/显存另由 NVIDIA 采样，两个口径不可相加。\n\n'
            '模型已驻留来自 Ollama /api/ps。LLM 推理中 / TTS 合成中来自已验证的 GPU 资源租约计数。调度正在处理、但没有模型租约时显示处理 / 等待资源。仅监听或进程存在不能证明正在推理。\n\n'
            '排队、完成数和 GPU 资源等待只取模型服务 /health 的白名单标量。健康接口的空计数字典表示尚无完成请求；接口不可用仍显示未知。GPU 上次等待不是模型推理耗时。403 时显示遥测受限。\n\n'
            '— 表示接口或计数器未提供；首轮 CPU 需等待第二次采样。刷新 2 秒，进程命令元数据每 10 秒检查一次。看板不发起生成、加载、卸载、启停请求。',parent=self.root)

    def screenshot(self,path):
        """Capture only this application's own HWND, never the whole desktop."""
        from PIL import Image
        self.root.update_idletasks()
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
        hwnd=user.GetAncestor(self.root.winfo_id(),2);rect=W.RECT();user.GetWindowRect(hwnd,C.byref(rect))
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

    def close(self):
        self.stop.set();self.root.destroy()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,help='Write a sanitized 3-sample real counter proof; no GUI')
    parser.add_argument('--screenshot',type=Path,help='Save this own GUI window after 3 real samples')
    parser.add_argument('--close-after',type=float,default=0,help='Bound a GUI verification run in seconds')
    args=parser.parse_args(argv)
    if args.close_after and not 4<=args.close_after<=3600:parser.error('Use 4–3600 seconds for bounded GUI verification')
    if args.snapshot:
        sampler=Sampler();values=[]
        try:
            for _ in range(3):
                began=time.monotonic();values.append(sampler.sample());time.sleep(max(0,INTERVAL-(time.monotonic()-began)))
        finally:sampler.close()
        args.snapshot.parent.mkdir(parents=True,exist_ok=True)
        args.snapshot.write_text(json.dumps(dict(status='ACTUAL_READ_ONLY_COUNTERS',samples=values),ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(dict(output=str(args.snapshot),samples=len(values))))
        return
    import tkinter as tk
    user=C.WinDLL('user32')
    try:user.SetProcessDPIAware()
    except AttributeError:pass
    kernel=C.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=[C.c_void_p,W.BOOL,W.LPCWSTR];kernel.CreateMutexW.restype=W.HANDLE
    kernel.CloseHandle.argtypes=[W.HANDLE]
    C.set_last_error(0)
    mutex=kernel.CreateMutexW(None,False,r'Local\AuraModelRuntimeDashboard-v1')
    if not mutex:raise OSError(C.get_last_error(),'Dashboard single-instance lock unavailable')
    existing=C.get_last_error()==183
    try:
        if existing:
            user.FindWindowW.argtypes=[W.LPCWSTR,W.LPCWSTR];user.FindWindowW.restype=W.HWND
            user.ShowWindow.argtypes=[W.HWND,C.c_int];user.SetForegroundWindow.argtypes=[W.HWND]
            hwnd=user.FindWindowW(None,TITLE)
            if hwnd:user.ShowWindow(hwnd,9);user.SetForegroundWindow(hwnd)
            return
        root=tk.Tk();Dashboard(root,args);root.mainloop()
    finally:kernel.CloseHandle(mutex)


if __name__=='__main__':main()
