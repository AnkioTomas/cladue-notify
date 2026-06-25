#!/usr/bin/env python3
"""将 Cursor notify hooks 写入 ~/.cursor/hooks.json"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOOK_SCRIPT = PROJECT_ROOT / "notify_hook.sh"
HOOKS_PATH = Path.home() / ".cursor" / "hooks.json"

# 只挂观察型事件：fire-and-forget 或输出可选，不会阻塞 agent loop
NOTIFY_HOOK_EVENTS = [
    "stop",
    "sessionStart",
    "sessionEnd",
    "subagentStop",
    "preCompact",
]


def merge_event(existing: list, handler: dict) -> list:
    """幂等：移除已指向本脚本的旧条目，保留用户在同事件上的其它 hook"""
    kept = [h for h in existing if h.get("command") != handler["command"]]
    return kept + [handler]


def main() -> int:
    if not HOOK_SCRIPT.exists():
        print(f"错误: hook 脚本不存在 {HOOK_SCRIPT}", file=sys.stderr)
        return 1

    HOOK_SCRIPT.chmod(HOOK_SCRIPT.stat().st_mode | 0o111)

    config: dict = {"version": 1, "hooks": {}}
    if HOOKS_PATH.exists():
        with open(HOOKS_PATH, encoding="utf-8") as f:
            config = json.load(f)
    config.setdefault("version", 1)
    hooks = config.setdefault("hooks", {})

    handler = {"command": str(HOOK_SCRIPT), "timeout": 15}
    for event in NOTIFY_HOOK_EVENTS:
        hooks[event] = merge_event(hooks.get(event, []), handler)

    HOOKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HOOKS_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"已写入 {len(NOTIFY_HOOK_EVENTS)} 个 Cursor 事件 hook 到 {HOOKS_PATH}")
    for event in NOTIFY_HOOK_EVENTS:
        print(f"  - {event}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
