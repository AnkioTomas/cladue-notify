#!/usr/bin/env python3
"""Claude Code hooks 事件监听和飞书通知入口"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config
from src.lark import SUPPORTED_EVENTS, format_claude_event_to_lark
from src.webhook import WebhookSender


def log(message: str) -> None:
    print(message, file=sys.stderr)


def read_event_data(args: argparse.Namespace) -> dict:
    """Claude Code hook 从 stdin 传入 JSON；保留 argv/环境变量用于本地测试"""
    if args.test_file:
        with open(args.test_file, encoding="utf-8") as f:
            return json.load(f)

    if not sys.stdin.isatty():
        return json.load(sys.stdin)

    if args.event_json:
        return json.loads(args.event_json)

    event_json = os.environ.get("ClaudeHookEvent")
    if event_json:
        return json.loads(event_json)

    raise ValueError("未提供事件数据")


def handle_event(event_data: dict, *, dry_run: bool = False) -> int:
    config = load_config()
    event_name = event_data.get("hook_event_name", "unknown")
    log(f"收到事件: {event_name}")

    if dry_run:
        print(format_claude_event_to_lark(event_data).content["text"])
        return 0

    if not config.webhook:
        log("警告: notify.json 未配置 webhook，跳过发送")
        return 0

    result = WebhookSender(config.webhook, config.timeout).send(event_data)
    if result["success"]:
        log(f"✓ 已发送，状态码 {result.get('status_code', 'N/A')}")
        return 0

    log(f"✗ 发送失败: {result.get('error', '未知错误')}")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Claude Code hook 飞书通知")
    parser.add_argument("event_json", nargs="?", help="事件 JSON 字符串（本地测试）")
    parser.add_argument("--test-file", help="从 JSON 文件读取事件")
    parser.add_argument("--dry-run", action="store_true", help="只格式化消息，不发送 webhook")
    parser.add_argument("--list-events", action="store_true", help="列出支持格式化的事件")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_events:
        for name in SUPPORTED_EVENTS:
            print(name)
        return

    try:
        event_data = read_event_data(args)
    except (json.JSONDecodeError, ValueError) as e:
        log(f"事件数据错误: {e}")
        log("用法:")
        log("  echo '<json>' | python3 main.py")
        log("  python3 main.py --test-file test_event.json")
        log("  python3 main.py --dry-run --test-file test_event.json")
        sys.exit(1)

    sys.exit(handle_event(event_data, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
