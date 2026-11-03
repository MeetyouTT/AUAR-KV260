# -*- coding: utf-8 -*-
"""状态合同一致性校验（**改动 / 接手前先跑**）—— 防止"运行时 15 态 vs UI·板端 10 态"再次漂移。

背景（2026-10-04 外部审查实测）：运行时有 15 态，但 `avatar_fsm.AVATAR_MAP` 与
`ui/ui_state.schema.json` 只有 10 态 ⇒ `avatar_spec()` **静默回退 IDLE** ⇒
`SPEAKING_NEUTRAL` / `PUZZLED` / `ACK_NOD` / `DENY_SHAKE` / `AWAKE` 的 UI 标签显示成"待机"。

检查项：
  C1 `fsm.RuntimeState` ↔ `avatar_fsm.AVATAR_MAP` 键集合一致
  C2 ↔ `avatar_assets.STATE_ASSET` 一致
  C3 ↔ `ui/ui_state.schema.json` 的 `runtime_state.enum` 一致
  C4 `ui/avatar_board_manifest.json` 的 states（**WARN**：本机无 PySide6，需在别机重跑 board_export.py）
  C5 burst 一致性：`BURST_STATES` ↔ `BURST_ASSETS`，且 burst 素材**不得**有 segments.json
  C6 每个状态的素材可解析（`frames_dir` 非 None）
  C7 `DEFAULT_SPEAKING_STATE == "SPEAKING_NEUTRAL"`（中性为默认档）

用法：
    "<AURA>\\.venv\\Scripts\\python.exe" -s tools\\verify_state_contract.py
输出：控制台 + %TEMP%\\aura_state_contract.txt（UTF-8）
"""
import json
import os
import sys
from pathlib import Path

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))

from board.interaction import avatar_assets as aa       # noqa: E402
from board.interaction import avatar_fsm as af          # noqa: E402
from board.runtime import fsm as runtime_fsm            # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

OUT = Path(os.environ.get("TEMP", ".")) / "aura_state_contract.txt"
LOG = []
FAILED = []
WARNED = []


def log(s):
    LOG.append(str(s))
    print(s, flush=True)


def check(cond, code, msg, warn=False):
    tag = "OK " if cond else ("WARN" if warn else "FAIL")
    log("  [%s] %s %s" % (tag, code, msg))
    if not cond:
        (WARNED if warn else FAILED).append(code)
    return cond


def runtime_states():
    """`fsm.RuntimeState` 的 15 个值（字符串）。"""
    out = []
    for item in runtime_fsm.RuntimeState:
        out.append(item.value if hasattr(item, "value") else str(item))
    return sorted(out)


def _diff(missing, extra):
    text = ""
    if missing:
        text += "；缺 %s" % ",".join(missing)
    if extra:
        text += "；多 %s" % ",".join(extra)
    return text


def main():
    log("=== 状态合同一致性校验 ===")
    log("权威来源：board/runtime/fsm.RuntimeState")
    states = runtime_states()
    log("运行时状态：%d 个 → %s" % (len(states), ", ".join(states)))
    log("")

    spec_keys = sorted(af.AVATAR_MAP.keys())
    ok = set(spec_keys) == set(states)
    check(ok, "C1", "avatar_fsm.AVATAR_MAP（%d 个）%s"
          % (len(spec_keys), "" if ok else _diff(sorted(set(states) - set(spec_keys)),
                                                 sorted(set(spec_keys) - set(states)))))

    asset_keys = sorted(aa.STATE_ASSET.keys())
    ok = set(asset_keys) == set(states)
    check(ok, "C2", "avatar_assets.STATE_ASSET（%d 个）%s"
          % (len(asset_keys), "" if ok else _diff(sorted(set(states) - set(asset_keys)),
                                                  sorted(set(asset_keys) - set(states)))))

    enum = []
    schema_path = AURA / "ui" / "ui_state.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        enum = schema["properties"]["runtime_state"]["enum"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        log("      读取 schema 失败：%s" % exc)
    ok = set(enum) == set(states)
    check(ok, "C3", "ui_state.schema.json 的 runtime_state.enum（%d 个）%s"
          % (len(enum), "" if ok else _diff(sorted(set(states) - set(enum)),
                                            sorted(set(enum) - set(states)))))

    m_states = []
    manifest_path = AURA / "ui" / "avatar_board_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        m_states = sorted(str(s.get("state")) for s in manifest.get("states", []))
    except (OSError, ValueError, TypeError) as exc:
        log("      读取 manifest 失败：%s" % exc)
    ok = set(m_states) == set(states)
    check(ok, "C4", "avatar_board_manifest.json 的 states（%d 个）%s —— 不一致时重跑 scripts\\board_export.py"
          % (len(m_states), "" if ok else _diff(sorted(set(states) - set(m_states)), [])),
          warn=True)

    burst_from_states = {aa.asset_name(s) for s in aa.BURST_STATES}
    check(set(aa.BURST_ASSETS) == burst_from_states, "C5",
          "BURST_ASSETS 与 BURST_STATES 一致（%s）" % ", ".join(sorted(aa.BURST_ASSETS)))
    for name in sorted(aa.BURST_ASSETS):
        seg = aa.read_segments(aa.asset_dir(name))
        check(seg is None, "C5", "%s（burst）不得有 segments.json（应为整段播一次）" % name)

    for state in states:
        directory = aa.frames_dir(state)
        check(directory is not None, "C6", "%s → 素材可解析" % state,
              warn=(state == "CANCELLED"))

    default_speaking = getattr(runtime_fsm, "DEFAULT_SPEAKING_STATE", None)
    check(default_speaking == "SPEAKING_NEUTRAL", "C7",
          "DEFAULT_SPEAKING_STATE = %s（中性播报为默认档）" % default_speaking)

    log("")
    log("RESULT: %s（%d 项失败，%d 项警告）"
        % ("OK" if not FAILED else "FAIL", len(FAILED), len(WARNED)))
    if FAILED:
        log("失败项：%s" % ", ".join(sorted(set(FAILED))))
    if WARNED:
        log("警告项：%s（可在有 PySide6 的机器消除）" % ", ".join(sorted(set(WARNED))))
    OUT.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("日志：%s" % OUT)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
