"""飞书（Lark/Feishu）消息格式支持"""
from __future__ import annotations

from typing import Callable

EventFormatter = Callable[[dict], tuple[str, list[str]]]


class LarkMessage:
    """飞书消息格式"""

    def __init__(self, msg_type: str = "text", content: dict | None = None):
        self.msg_type = msg_type
        self.content = content or {}

    def to_dict(self) -> dict:
        return {
            "msg_type": self.msg_type,
            "content": self.content,
        }


class LarkTextMessage(LarkMessage):
    """飞书文本消息"""

    def __init__(self, text: str):
        super().__init__("text", {"text": text})


NOTIFICATION_LABELS = {
    "permission_prompt": "Claude Code 需要批准",
    "idle_prompt": "Claude Code 等待输入",
    "auth_success": "Claude Code 认证成功",
    "elicitation_dialog": "Claude Code MCP 表单待填写",
    "elicitation_complete": "Claude Code MCP 表单已提交",
    "elicitation_response": "Claude Code MCP 表单已响应",
}

SESSION_SOURCE_LABELS = {
    "startup": "新会话",
    "resume": "恢复会话",
    "clear": "清空后重启",
    "compact": "压缩上下文后",
}

SESSION_END_LABELS = {
    "clear": "清空会话",
    "resume": "切换会话",
    "logout": "退出登录",
    "prompt_input_exit": "退出输入",
    "bypass_permissions_disabled": "关闭 bypass 权限",
    "other": "其他原因",
}

STOP_FAILURE_LABELS = {
    "rate_limit": "速率限制",
    "overloaded": "服务过载",
    "authentication_failed": "认证失败",
    "oauth_org_not_allowed": "组织 OAuth 不允许",
    "billing_error": "账单错误",
    "invalid_request": "无效请求",
    "model_not_found": "模型不存在",
    "server_error": "服务器错误",
    "max_output_tokens": "输出 token 超限",
    "unknown": "未知错误",
}


def _truncate(text: str | None, max_len: int = 200) -> str:
    if not text:
        return ""
    text = str(text).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _tool_line(event_data: dict) -> str | None:
    tool_name = event_data.get("tool_name")
    if not tool_name:
        return None
    tool_input = event_data.get("tool_input") or {}
    if tool_name == "Bash":
        command = tool_input.get("command")
        if command:
            return f"工具: Bash — {_truncate(command, 120)}"
    return f"工具: {tool_name}"


def _append_context(body_lines: list[str], event_data: dict) -> None:
    roots = event_data.get("workspace_roots") or []
    cwd = event_data.get("cwd") or (roots[0] if roots else "")
    sid = event_data.get("session_id") or event_data.get("conversation_id") or ""
    if cwd:
        body_lines.append(f"项目: {cwd}")
    if sid:
        body_lines.append(f"会话: {sid[:8]}")


def _fmt_notification(event_data: dict) -> tuple[str, list[str]]:
    notification_type = event_data.get("notification_type", "unknown")
    title = NOTIFICATION_LABELS.get(
        notification_type,
        f"Claude Code 通知 ({notification_type})",
    )
    body_lines = [_notification_body(notification_type, event_data)]
    message = event_data.get("message")
    if message:
        body_lines.append(_truncate(message))
    return title, body_lines


def _fmt_stop(event_data: dict) -> tuple[str, list[str]]:
    title = "Claude Code 本轮回复结束"
    body_lines = ["Claude 已完成当前回复。"]
    if event_data.get("stop_hook_active"):
        body_lines.append("Stop hook 续跑中。")
    summary = _truncate(event_data.get("last_assistant_message"))
    if summary:
        body_lines.append(f"摘要: {summary}")
    bg_tasks = event_data.get("background_tasks") or []
    crons = event_data.get("session_crons") or []
    if bg_tasks:
        body_lines.append(f"后台任务: {len(bg_tasks)} 个进行中")
    if crons:
        body_lines.append(f"定时任务: {len(crons)} 个已调度")
    return title, body_lines


def _fmt_permission_request(event_data: dict) -> tuple[str, list[str]]:
    body_lines = ["请在终端确认是否允许该操作。"]
    tool_line = _tool_line(event_data)
    if tool_line:
        body_lines.insert(0, tool_line)
    return "Claude Code 权限请求", body_lines


def _fmt_permission_denied(event_data: dict) -> tuple[str, list[str]]:
    body_lines = []
    tool_line = _tool_line(event_data)
    if tool_line:
        body_lines.append(tool_line)
    reason = event_data.get("reason")
    if reason:
        body_lines.append(f"原因: {_truncate(reason)}")
    if not body_lines:
        body_lines.append("自动模式拒绝了工具调用。")
    return "Claude Code 权限被拒绝", body_lines


def _fmt_stop_failure(event_data: dict) -> tuple[str, list[str]]:
    error = event_data.get("error", "unknown")
    label = STOP_FAILURE_LABELS.get(error, error)
    body_lines = [f"错误类型: {label}"]
    details = event_data.get("error_details")
    if details:
        body_lines.append(f"详情: {_truncate(str(details))}")
    message = event_data.get("last_assistant_message")
    if message:
        body_lines.append(f"消息: {_truncate(message)}")
    return "Claude Code 回复失败", body_lines


def _fmt_session_start(event_data: dict) -> tuple[str, list[str]]:
    source = event_data.get("source", "unknown")
    label = SESSION_SOURCE_LABELS.get(source, source)
    body_lines = [f"触发: {label}"]
    model = event_data.get("model")
    if model:
        body_lines.append(f"模型: {model}")
    agent_type = event_data.get("agent_type")
    if agent_type:
        body_lines.append(f"代理: {agent_type}")
    return "Claude Code 会话开始", body_lines


def _fmt_session_end(event_data: dict) -> tuple[str, list[str]]:
    reason = event_data.get("reason", "unknown")
    label = SESSION_END_LABELS.get(reason, reason)
    return "Claude Code 会话结束", [f"原因: {label}"]


def _fmt_subagent_start(event_data: dict) -> tuple[str, list[str]]:
    agent_type = event_data.get("agent_type", "unknown")
    return "Claude Code 子代理启动", [f"类型: {agent_type}"]


def _fmt_subagent_stop(event_data: dict) -> tuple[str, list[str]]:
    agent_type = event_data.get("agent_type", "unknown")
    body_lines = [f"类型: {agent_type}"]
    summary = _truncate(event_data.get("last_assistant_message"))
    if summary:
        body_lines.append(f"摘要: {summary}")
    return "Claude Code 子代理完成", body_lines


def _fmt_elicitation(event_data: dict) -> tuple[str, list[str]]:
    server = event_data.get("mcp_server_name", "unknown")
    body_lines = [f"MCP 服务: {server}"]
    message = event_data.get("message")
    if message:
        body_lines.append(_truncate(message))
    mode = event_data.get("mode")
    if mode == "url" and event_data.get("url"):
        body_lines.append(f"链接: {event_data['url']}")
    return "Claude Code MCP 需要输入", body_lines


def _fmt_elicitation_result(event_data: dict) -> tuple[str, list[str]]:
    server = event_data.get("mcp_server_name", "unknown")
    return "Claude Code MCP 表单已响应", [f"MCP 服务: {server}"]


def _fmt_teammate_idle(event_data: dict) -> tuple[str, list[str]]:
    teammate = event_data.get("teammate_name") or event_data.get("agent_type")
    body_lines = ["队友即将进入空闲状态。"]
    if teammate:
        body_lines.insert(0, f"队友: {teammate}")
    return "Claude Code 队友空闲", body_lines


def _fmt_task_created(event_data: dict) -> tuple[str, list[str]]:
    subject = event_data.get("subject") or event_data.get("description")
    body_lines = ["新任务已创建。"]
    if subject:
        body_lines.append(_truncate(subject))
    return "Claude Code 任务创建", body_lines


def _fmt_task_completed(event_data: dict) -> tuple[str, list[str]]:
    subject = event_data.get("subject") or event_data.get("description")
    body_lines = ["任务已标记完成。"]
    if subject:
        body_lines.append(_truncate(subject))
    return "Claude Code 任务完成", body_lines


def _fmt_user_prompt_submit(event_data: dict) -> tuple[str, list[str]]:
    prompt = _truncate(event_data.get("prompt"))
    body_lines = [prompt] if prompt else ["用户提交了新的指令。"]
    return "Claude Code 收到指令", body_lines


def _fmt_post_tool_use(event_data: dict) -> tuple[str, list[str]]:
    body_lines = []
    tool_line = _tool_line(event_data)
    if tool_line:
        body_lines.append(tool_line)
    if not body_lines:
        body_lines.append("工具调用已完成。")
    return "Claude Code 工具完成", body_lines


def _fmt_pre_tool_use(event_data: dict) -> tuple[str, list[str]]:
    body_lines = []
    tool_line = _tool_line(event_data)
    if tool_line:
        body_lines.append(tool_line)
    if not body_lines:
        body_lines.append("即将执行工具调用。")
    return "Claude Code 工具调用", body_lines


CURSOR_STATUS_LABELS = {
    "completed": "已完成",
    "aborted": "已中止",
    "error": "出错",
}

CURSOR_SESSION_END_LABELS = {
    "completed": "正常完成",
    "aborted": "已中止",
    "error": "出错",
    "window_close": "窗口关闭",
    "user_close": "用户关闭",
}


def _fmt_cursor_stop(event_data: dict) -> tuple[str, list[str]]:
    status = event_data.get("status", "completed")
    label = CURSOR_STATUS_LABELS.get(status, status)
    return "Cursor 本轮结束", [f"状态: {label}"]


def _fmt_cursor_session_start(event_data: dict) -> tuple[str, list[str]]:
    body_lines = []
    mode = event_data.get("composer_mode")
    if mode:
        body_lines.append(f"模式: {mode}")
    if event_data.get("is_background_agent"):
        body_lines.append("后台代理会话")
    return "Cursor 会话开始", body_lines or ["新会话已创建。"]


def _fmt_cursor_session_end(event_data: dict) -> tuple[str, list[str]]:
    reason = event_data.get("reason", "completed")
    label = CURSOR_SESSION_END_LABELS.get(reason, reason)
    body_lines = [f"原因: {label}"]
    error = event_data.get("error_message")
    if error:
        body_lines.append(f"错误: {_truncate(error)}")
    return "Cursor 会话结束", body_lines


def _fmt_cursor_subagent_stop(event_data: dict) -> tuple[str, list[str]]:
    subagent_type = event_data.get("subagent_type", "unknown")
    status = event_data.get("status", "completed")
    label = CURSOR_STATUS_LABELS.get(status, status)
    body_lines = [f"类型: {subagent_type}", f"状态: {label}"]
    summary = _truncate(event_data.get("summary"))
    if summary:
        body_lines.append(f"摘要: {summary}")
    return "Cursor 子代理完成", body_lines


def _fmt_cursor_pre_compact(event_data: dict) -> tuple[str, list[str]]:
    trigger = "自动" if event_data.get("trigger", "auto") == "auto" else "手动"
    body_lines = [f"触发: {trigger}"]
    pct = event_data.get("context_usage_percent")
    if pct is not None:
        body_lines.append(f"上下文占用: {pct}%")
    return "Cursor 上下文压缩", body_lines


def _fmt_generic(event_data: dict) -> tuple[str, list[str]]:
    event_name = event_data.get("hook_event_name", "unknown")
    body_lines = ["收到 Claude Code hook 事件。"]
    for key in ("message", "reason", "tool_name", "agent_type", "error"):
        value = event_data.get(key)
        if value:
            body_lines.append(f"{key}: {_truncate(str(value))}")
    return f"Claude Code 事件: {event_name}", body_lines


EVENT_FORMATTERS: dict[str, EventFormatter] = {
    "Notification": _fmt_notification,
    "Stop": _fmt_stop,
    "StopFailure": _fmt_stop_failure,
    "PermissionRequest": _fmt_permission_request,
    "PermissionDenied": _fmt_permission_denied,
    "SessionStart": _fmt_session_start,
    "SessionEnd": _fmt_session_end,
    "SubagentStart": _fmt_subagent_start,
    "SubagentStop": _fmt_subagent_stop,
    "Elicitation": _fmt_elicitation,
    "ElicitationResult": _fmt_elicitation_result,
    "TeammateIdle": _fmt_teammate_idle,
    "TaskCreated": _fmt_task_created,
    "TaskCompleted": _fmt_task_completed,
    "UserPromptSubmit": _fmt_user_prompt_submit,
    "PostToolUse": _fmt_post_tool_use,
    "PreToolUse": _fmt_pre_tool_use,
    "stop": _fmt_cursor_stop,
    "sessionStart": _fmt_cursor_session_start,
    "sessionEnd": _fmt_cursor_session_end,
    "subagentStop": _fmt_cursor_subagent_stop,
    "preCompact": _fmt_cursor_pre_compact,
}

SUPPORTED_EVENTS = list(EVENT_FORMATTERS.keys())


def format_claude_event_to_lark(event_data: dict) -> LarkTextMessage:
    """将 Claude Code hook 事件格式化为飞书 text 消息（首行作为 title）"""
    event_name = event_data.get("hook_event_name", "unknown")
    formatter = EVENT_FORMATTERS.get(event_name, _fmt_generic)
    title, body_lines = formatter(event_data)
    _append_context(body_lines, event_data)
    text = title if not body_lines else title + "\n" + "\n".join(body_lines)
    return LarkTextMessage(text)


def _notification_body(notification_type: str, event_data: dict) -> str:
    if notification_type == "permission_prompt":
        return "Claude 需要你批准一项操作，请回到终端处理。"
    if notification_type == "idle_prompt":
        return "Claude 已完成当前任务，等待你的下一步指令。"
    if notification_type == "auth_success":
        return "Claude Code 认证已完成。"
    if notification_type.startswith("elicitation"):
        return "Claude Code 正在等待 MCP 表单交互。"
    return f"通知类型: {notification_type}"
