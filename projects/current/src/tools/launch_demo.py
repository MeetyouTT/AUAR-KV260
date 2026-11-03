# -*- coding: utf-8 -*-
"""一键管理玩偶演示环境（对话主机 + 演示台）——**正式入口**。

为什么需要它
------------
1. **进程必须脱离终端**：Cline/终端里换命令会连带终止上一条命令的进程树，
   `start /b` 的子进程也保不住 → 这里用 `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`
   让 host / stage 完全脱离父进程，父进程退出后仍存活。
2. **清理**：演示会反复重启，残留进程会抢 8765 端口、桌面上出现多个窗口 →
   提供 `--stop`（只清理）与 `--restart`（先清理再启动）。
3. **临时文件清理**：`--clean-temp` 只删**本工具族**在 %TEMP% 产生的探测脚本与日志
   （模式白名单 + 逐条打印；不递归、不删目录、不碰其它文件）。

用法（本机无系统 Python，用便携解释器或 venv 解释器都行）：
    "<PY>" -s tools\\launch_demo.py                 # 启动（若已在跑则提示）
    "<PY>" -s tools\\launch_demo.py --restart       # 先清理再启动
    "<PY>" -s tools\\launch_demo.py --stop          # 只清理进程
    "<PY>" -s tools\\launch_demo.py --clean-temp    # 清理 %TEMP% 临时产物
    "<PY>" -s tools\\launch_demo.py --backend mock  # 不依赖 LLM（联调用）
默认解释器 = `aura/.venv/Scripts/python.exe`（TTS/ASR 依赖都在 venv 内）。
"""
import argparse
import glob
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

AURA = Path(__file__).resolve().parents[1]
TEMP = os.environ.get("TEMP", ".")
DEFAULT_PY = str(AURA / ".venv" / "Scripts" / "python.exe")
DEFAULT_PYW = str(AURA / ".venv" / "Scripts" / "pythonw.exe")
FALLBACK_PY = (r"D:\sd-webui-aki-v4.11.1-cu128\ComfyUI_Windows_portable_cu130.7z"
               r"\ComfyUI_Windows_portable\python_standalone\python.exe")
#: ⚠ `0x08000000 = CREATE_NO_WINDOW` **必须加**：venv 的 `python.exe` 是**控制台子系统**程序，
#: 只给 `DETACHED_PROCESS` 时 Windows 仍会给它挂一个**可见的控制台窗口**，而那个窗口会盖在
#: Tk 主窗口上**吃掉全部点击/键盘**（实测 2026-10-04：表现为"动画在跑、HUD 在变，但按钮点不动，
#: 事件日志一条都没有"）。两重保险：本标志 + 优先用 `pythonw.exe`（GUI 子系统，根本不建控制台）。
CREATE_NO_WINDOW = 0x08000000
DETACH = 0x00000008 | 0x00000200 | CREATE_NO_WINDOW   # DETACHED | NEW_GROUP | NO_WINDOW
HOST_SCRIPT = str(AURA / "tools" / "dialogue_host_ollama.py")
STAGE_SCRIPT = str(AURA / "tools" / "demo_stage.py")
PORT = 8765

#: 只清理这些**模式**在 %TEMP% 的产物（本次工作产生的探测脚本 / 日志 / 自检输出）
TEMP_PATTERNS = (
    "aura_*", "p01_out*.txt", "p02_*.txt", "e2e_*.txt", "host_*.txt",
    "host_e2e_all_host.log", "ollama_*.txt", "ollama_*.json",
    "x1.txt", "x2.txt", "x3.txt", "x4.txt", "x5.txt",
    "tk_check*.txt", "netprobe*.txt", "net_check.txt", "probe2.txt", "probe_wait.txt",
    "wait2.txt", "wait3.txt", "gh_*.txt", "hf_probe*.txt", "dl_*.txt", "dl_asr.*",
    "venv_*.txt", "bat_crlf*.txt", "launch_*.txt", "restart_*.txt", "kill_*.txt",
    "final*.txt", "count_ok.txt", "gui_*.txt", "png_check.txt", "stage_*.txt",
    "audio_*.txt", "audio_chain_*.txt", "mic_*.txt", "pip_ver.txt", "sherpa_check.txt",
    "p_dolls.txt", "p15855387.txt", "dev_list.txt", "ws_list.txt", "find_doll*.txt",
    "plan_*.txt", "fsm_*.txt", "live_check.txt", "old_procs.txt", "kws_sig.txt",
    "aura_tts_sample.wav",
)
#: 启动/清理工具本身保留（不删）
TEMP_KEEP = ("launch_demo.py", "restart_clean.py", "restart_demo.py")


def ps(command: str) -> str:
    """跑一段 PowerShell（零依赖），返回 stdout。"""
    return subprocess.run(["powershell", "-NoProfile", "-Command", command],
                          capture_output=True, text=True).stdout.strip()


def alive_pids() -> dict:
    """列出本演示环境的 host / stage PID（拼接 pattern，避免匹配到查询进程自身）。"""
    out = ps("$h=@(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like ('*dialogue_' + 'host*') });"
             "$g=@(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like ('*demo_' + 'stage*') });"
             "(($h | ForEach-Object { $_.ProcessId }) -join ',') + '|' + "
             "(($g | ForEach-Object { $_.ProcessId }) -join ',')")
    parts = out.split("|")
    host = [p for p in (parts[0].split(",") if parts else []) if p.strip()]
    stage = [p for p in (parts[1].split(",") if len(parts) > 1 else []) if p.strip()]
    return {"host": host, "stage": stage}


def stop_all() -> None:
    """停止 host / stage（幂等）。"""
    killed = ps("Get-CimInstance Win32_Process | "
                "Where-Object { $_.CommandLine -like ('*dialogue_' + 'host*') -or "
                "$_.CommandLine -like ('*demo_' + 'stage*') } | "
                "ForEach-Object { 'KILLED ' + $_.ProcessId; Stop-Process -Id $_.ProcessId -Force }")
    print("[stop] %s" % (killed.replace("\n", " | ") or "(无进程)"), flush=True)
    time.sleep(1.0)


def clean_temp() -> None:
    """删除本工具族在 %TEMP% 的临时产物（逐条打印；不递归、不删目录）。"""
    removed, kept = [], []
    for pattern in TEMP_PATTERNS:
        for path in glob.glob(os.path.join(TEMP, pattern)):
            if not os.path.isfile(path):
                continue
            if os.path.basename(path) in TEMP_KEEP:
                kept.append(path)
                continue
            try:
                os.remove(path)
                removed.append(os.path.basename(path))
            except OSError as exc:
                print("[clean_temp] 删除失败 %s：%s" % (path, exc), flush=True)
    print("[clean_temp] 删除 %d 个临时文件：%s"
          % (len(removed), ", ".join(sorted(removed)) or "(无)"), flush=True)
    if kept:
        print("[clean_temp] 保留：%s"
              % ", ".join(sorted(os.path.basename(k) for k in kept)), flush=True)


def wait_port(port: int, timeout: float = 60.0) -> bool:
    """轮询端口是否可连（Bash/CMD 里 sleep 不可靠，用连接探测代替）。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
            return True
        except OSError:
            time.sleep(0.5)
    return False


def spawn(args, log_name: str, python: str):
    """脱离进程启动脚本，输出写 `%TEMP%\\<log_name>`。"""
    return subprocess.Popen([python, "-s"] + args,
                            stdout=open(os.path.join(TEMP, log_name), "wb"),
                            stderr=subprocess.STDOUT,
                            creationflags=DETACH, cwd=str(AURA))


def python_exe() -> str:
    """优先 `pythonw.exe`（GUI 子系统，**不会**分配控制台窗口，避免盖住 Tk 主窗口），
    其次 `python.exe`，最后便携解释器。"""
    for cand in (DEFAULT_PYW, DEFAULT_PY, FALLBACK_PY):
        if os.path.isfile(cand):
            return cand
    return "python"


def start(backend: str, tts_engine: str = "sapi", tts_sid: int = 0,
          tts_model: str = "") -> int:
    """启动 host + stage 并验证存活。"""
    python = python_exe()
    print("[start] 解释器：%s" % python, flush=True)
    print("[start] TTS：engine=%s sid=%d model=%s"
          % (tts_engine, tts_sid, tts_model or "(自动挑，VITS 优先)"), flush=True)
    host = spawn([HOST_SCRIPT, "--backend", backend], "aura_host.log", python)
    if not wait_port(PORT):
        print("[start] 主机未就绪（看 %TEMP%\\aura_host.log）", flush=True)
        return 1
    print("[start] 主机就绪 pid=%s（backend=%s）" % (host.pid, backend), flush=True)
    stage_args = [STAGE_SCRIPT, "--host", "127.0.0.1", "--port", str(PORT),
                  "--tts-engine", tts_engine, "--tts-sid", str(tts_sid)]
    if tts_model:
        stage_args += ["--tts-model", tts_model]
    stage = spawn(stage_args, "aura_stage.log", python)
    time.sleep(8)
    pids = alive_pids()
    host_ok = host.poll() is None
    stage_ok = stage.poll() is None
    port_ok = wait_port(PORT, 2.0)
    print("[start] 主机存活=%s 演示台存活=%s(pid=%s) 端口=%s"
          % (host_ok, stage_ok, stage.pid, port_ok), flush=True)
    print("[start] 进程：host=%s stage=%s（venv 下每个脚本会显示 launcher+解释器两个 PID，属同一组）"
          % (pids["host"], pids["stage"]), flush=True)
    return 0 if (host_ok and stage_ok and port_ok) else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="玩偶演示环境管理（对话主机 + 演示台）")
    parser.add_argument("--backend", choices=("ollama", "mock"), default="ollama")
    parser.add_argument("--stop", action="store_true", help="只清理进程")
    parser.add_argument("--restart", action="store_true", help="先清理再启动")
    parser.add_argument("--clean-temp", action="store_true", help="清理 TEMP 目录里的临时产物")
    # TTS 透传给演示台（不传 = 演示台默认 sapi）
    parser.add_argument("--tts-engine", default="sapi",
                        choices=("sapi", "scripted", "vits"),
                        help="TTS 后端（vits=本地离线神经 TTS，见 docs\\本地神经TTS接入…）")
    parser.add_argument("--tts-sid", type=int, default=0,
                        help="神经 TTS 说话人 ID（Kokoro 3-57 中文女 / 58-102 中文男）")
    parser.add_argument("--tts-model", default="",
                        help="神经 TTS 模型目录名或绝对路径（留空 = models/tts 下自动挑，VITS 优先）")
    args = parser.parse_args(argv)

    if args.stop:
        stop_all()
        return 0
    if args.clean_temp:
        stop_all()
        clean_temp()
        return 0
    if args.restart:
        stop_all()
        clean_temp()
    else:
        pids = alive_pids()
        if pids["host"] or pids["stage"]:
            print("[main] 已在运行：host=%s stage=%s（要重启用 --restart）"
                  % (pids["host"], pids["stage"]), flush=True)
            return 0
    return start(args.backend, args.tts_engine, args.tts_sid, args.tts_model)


if __name__ == "__main__":
    sys.exit(main())
