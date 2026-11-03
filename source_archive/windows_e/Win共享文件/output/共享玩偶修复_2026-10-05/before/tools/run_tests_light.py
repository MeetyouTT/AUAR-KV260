# -*- coding: utf-8 -*-
"""**轻量测试 runner**：在**没有 pytest** 的环境里跑 `tests/` 中"不需要 fixture"的用例。

背景（2026-10-04）：本机 `.venv` **刻意未装 pytest**（见 `requirements.txt`），但外部审查报
`tests/` 有 5 个**真实失败**（完整对话流程 / 重复定义测试辅助函数 / 引用未定义变量）。
为了能**本机复现 + 验证修复**，这里做一个小 runner：

  · 收集 `tests/test_*.py` 里所有 `test_*` 函数；
  · **跳过需要 fixture 的**（形参非空 → `SKIP`，例如 `tmp_path` / `qapp`）；
  · 逐个调用并捕获异常 → 输出 `PASS / FAIL / SKIP` 统计 + 失败摘要。

⚠ 这是**辅助**手段，不替代 pytest：正式 CI 仍应 `pip install pytest` 后跑 `pytest tests/`。

用法：
    "<AURA>\\.venv\\Scripts\\python.exe" -s tools\\run_tests_light.py [--only test_fsm] [--max-fail 10]
输出：控制台 + %TEMP%\\aura_tests_light.txt（UTF-8）
"""
import argparse
import importlib.util
import inspect
import os
import sys
import traceback
from pathlib import Path

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

TESTS = AURA / "tests"
OUT = Path(os.environ.get("TEMP", ".")) / "aura_tests_light.txt"
LOG = []
PASS = []
FAIL = []
SKIP = []


def log(s):
    LOG.append(str(s))
    print(s, flush=True)


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("lt_" + path.stem, str(path))
    if spec is None or spec.loader is None:
        raise ImportError("无法加载 %s" % path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)          # 收集期错误（import/语法）在此抛出
    return module


def positional_params(fn):
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return []
    kinds = (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    return [p for p in sig.parameters.values() if p.kind in kinds]


def main():
    ap = argparse.ArgumentParser(description="轻量测试 runner（无 pytest）")
    ap.add_argument("--only", default="", help="只跑文件名含该子串的测试模块")
    ap.add_argument("--max-fail", type=int, default=10, help="最多打印多少条失败摘要")
    args = ap.parse_args()

    log("=== 轻量测试 runner（无 pytest；跳过需要 fixture 的用例）===")
    log("")
    modules = sorted(TESTS.glob("test_*.py"))
    if args.only:
        modules = [p for p in modules if args.only in p.stem]
    for path in modules:
        try:
            module = load_module(path)
        except ModuleNotFoundError as exc:
            # 缺第三方依赖（如 pytest / opencv）**不等于用例失败** → 记 SKIP 并说明缺什么
            SKIP.append("%s（缺 %s）" % (path.name, exc.name))
            log("[SKIP] %-34s 缺依赖：%s（本机未装；见 requirements.txt）"
                % (path.name, exc.name))
            continue
        except Exception:
            FAIL.append("%s（模块导入失败）" % path.name)
            log("[FAIL] %-34s 模块导入失败：%s"
                % (path.name, traceback.format_exc(limit=1).strip().splitlines()[-1]))
            continue
        for name in sorted(dir(module)):
            if not name.startswith("test_"):
                continue
            fn = getattr(module, name)
            if not callable(fn):
                continue
            tag = "%s::%s" % (path.stem, name)
            if positional_params(fn):
                SKIP.append(tag)
                continue
            try:
                fn()
                PASS.append(tag)
            except Exception as exc:
                FAIL.append(tag)
                LOG.append("[FAIL] %s" % tag)
                LOG.append("       %s: %s" % (type(exc).__name__, exc))
                log("[FAIL] %s" % tag)
                if len(FAIL) <= args.max_fail:
                    log("       %s: %s" % (type(exc).__name__, exc))
    log("")
    log("结果：PASS %d ／ FAIL %d ／ SKIP %d（跳过 = 需要 fixture，本 runner 不提供）"
        % (len(PASS), len(FAIL), len(SKIP)))
    if FAIL:
        log("")
        log("失败清单：")
        for tag in FAIL:
            log("  - %s" % tag)
    if SKIP:
        log("")
        log("跳过清单（%d 条，需 pytest fixture）：%s%s"
            % (len(SKIP), ", ".join(SKIP[:8]), " …" if len(SKIP) > 8 else ""))
    log("")
    log("RESULT: %s" % ("OK" if not FAIL else "FAIL"))
    OUT.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("日志：%s" % OUT)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
