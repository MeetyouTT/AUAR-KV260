#!/usr/bin/env bash
# 启动 AMD_Smart 项目专用 Codex；所有会话状态均保存在 .codex-home/。
set -euo pipefail

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export CODEX_HOME="$PROJECT_ROOT/.codex-home"
LOG_DIR="$PROJECT_ROOT/logs/codex"

mkdir -p "$CODEX_HOME" "$LOG_DIR"
cd "$PROJECT_ROOT"

# script 保留伪终端，因此 Codex TUI 可正常交互，同时把显示输出记录到项目日志。
LOG_FILE="$LOG_DIR/codex-$(date '+%Y-%m-%d_%H-%M-%S').log"
if command -v script >/dev/null 2>&1; then
  COMMAND_LINE="$(printf '%q ' codex "$@")"
  exec script --quiet --flush --append "$LOG_FILE" --command "$COMMAND_LINE" /dev/null
fi

# 极简环境中没有 script 时，仍可启动项目专用 Codex，只是不记录 TUI 输出。
exec codex "$@"
