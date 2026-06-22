#!/usr/bin/env python3
"""将 Claude Code notify hooks 写入 ~/.claude/settings.json"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOOK_SCRIPT = PROJECT_ROOT / "notify_hook.sh"
SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

# 需要用户关注或状态变化的事件；工具类高频事件默认不注册
NOTIFY_HOOK_EVENTS = [
    "Notification",
    "Stop",
    "StopFailure",
    "PermissionRequest",
    "PermissionDenied",
    "Elicitation",
    "ElicitationResult",
    "SessionStart",
    "SessionEnd",
    "SubagentStart",
    "SubagentStop",
    "TeammateIdle",
    "TaskCreated",
    "TaskCompleted",
]

# 这些事件支持 matcher 过滤
MATCHER_EVENTS = {
    "PermissionRequest": "*",
    "PermissionDenied": "*",
    "SessionStart": "*",
    "StopFailure": "*",
}


def build_hook_entry(event_name: str) -> list[dict]:
    handler = {
        "type": "command",
        "command": str(HOOK_SCRIPT),
        "async": True,
        "timeout": 15,
    }

    group: dict = {"hooks": [handler]}
    matcher = MATCHER_EVENTS.get(event_name)
    if matcher:
        group["matcher"] = matcher
    return [group]


def build_hooks_config() -> dict:
    return {event: build_hook_entry(event) for event in NOTIFY_HOOK_EVENTS}


def merge_settings(existing: dict, hooks: dict) -> dict:
    merged = dict(existing)
    merged["hooks"] = hooks
    return merged


def main() -> int:
    if not HOOK_SCRIPT.exists():
        print(f"错误: hook 脚本不存在 {HOOK_SCRIPT}", file=sys.stderr)
        return 1

    HOOK_SCRIPT.chmod(HOOK_SCRIPT.stat().st_mode | 0o111)

    settings: dict = {}
    if SETTINGS_PATH.exists():
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            settings = json.load(f)

    hooks = build_hooks_config()
    merged = merge_settings(settings, hooks)

    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"已写入 {len(hooks)} 个事件 hook 到 {SETTINGS_PATH}")
    for event in NOTIFY_HOOK_EVENTS:
        print(f"  - {event}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
