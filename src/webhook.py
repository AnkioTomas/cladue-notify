"""Webhook 发送模块（适配飞书格式）"""
import json
import urllib.error
import urllib.request

from .lark import format_claude_event_to_lark


class WebhookSender:
    """Webhook 发送器（飞书专用）"""

    def __init__(self, url: str, timeout: int = 10):
        self.url = url
        self.timeout = timeout

    def send(self, event_data: dict) -> dict:
        message = format_claude_event_to_lark(event_data)
        data = json.dumps(message.to_dict(), ensure_ascii=False).encode("utf-8")
        result = {"url": self.url, "success": False, "error": None}

        try:
            req = urllib.request.Request(
                self.url,
                data=data,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result["success"] = True
                result["status_code"] = response.status
                result["response"] = response.read().decode("utf-8")
        except urllib.error.URLError as e:
            result["error"] = str(e.reason)
        except Exception as e:
            result["error"] = str(e)

        return result
