# Claude Code 飞书通知

将 Claude Code 的 Hook 事件推送到飞书（Lark/Feishu）。

## 简介

当你在使用 Claude Code 时，这个系统会在关键事件发生时（如需要批准、会话结束、出错等）向飞书发送通知。

```
┌─────────────────────────────────────────────────────────┐
│ Claude Code 触发 Hook 事件                               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ ~/.claude/settings.json 中的 hook 配置                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ notify_hook.sh → main.py                                 │
│  - 读取 notify.json                                      │
│  - 格式化飞书消息                                        │
│  - POST 到 webhook                                       │
└─────────────────────────────────────────────────────────┘
```

**设计哲学**：只推送需要用户关注的事件，不推送高频工具调用通知。

## 环境要求

- macOS / Linux
- Python 3.10+（仅标准库）
- [Claude Code CLI](https://code.claude.com/docs/en/setup)

## 快速开始

### 1. 配置 webhook

复制示例配置并填入你的飞书 webhook 地址：

```bash
cp notify.json.example notify.json
```

编辑 `notify.json`（**必须放在项目根目录**）：

```json
{
  "webhook": "https://your-notify-server.example/claude?type=feishu&authorization=YOUR_TOKEN",
  "timeout": 10
}
```

| 字段 | 说明 | 默认 |
|------|------|------|
| `webhook` | 飞书 webhook 地址 | 必填 |
| `timeout` | HTTP 超时（秒） | 10 |

### 2. 安装 Hooks

```bash
python3 scripts/install_hooks.py
```

这会将 14 个事件的 hook 写入 `~/.claude/settings.json`（异步执行，不阻塞）。

安装后重启 Claude Code 或新开 session。

### 3. 验证

```bash
# 列出支持的事件
python3 main.py --list-events

# 测试格式化（不发送）
python3 main.py --dry-run --test-file test_event.json

# 从 stdin 测试
echo '{"hook_event_name":"Stop","cwd":"/tmp","session_id":"abc"}' | python3 main.py --dry-run
```

## 支持的事件

默认注册的 14 个事件：

| 事件 | 触发场景 | 说明 |
|------|----------|------|
| `Notification` | 需要批准、等待输入、认证成功 | 重要状态通知 |
| `Stop` | 完成一轮回复 | 正常结束 |
| `StopFailure` | API 错误 | 速率限制、认证失败等 |
| `PermissionRequest` | 权限请求 | 需要用户确认 |
| `PermissionDenied` | 权限被拒 | 自动模式拒绝 |
| `Elicitation` | MCP 表单待填写 | 等待用户输入 |
| `ElicitationResult` | MCP 表单已提交 | 输入完成 |
| `SessionStart` | 会话开始 | 新会话/恢复/清空 |
| `SessionEnd` | 会话结束 | 切换/退出/清空 |
| `SubagentStart` | 子代理启动 | 启动独立代理 |
| `SubagentStop` | 子代理完成 | 代理工作结束 |
| `TeammateIdle` | 队友空闲 | 队友等待指令 |
| `TaskCreated` | 任务创建 | 新任务开始 |
| `TaskCompleted` | 任务完成 | 任务标记完成 |

### 高频事件（默认不注册）

以下事件支持格式化但默认不注册（频率太高）：

- `UserPromptSubmit` - 用户提交指令
- `PreToolUse` - 工具调用前
- `PostToolUse` - 工具调用后

如需启用，编辑 `scripts/install_hooks.py` 中的 `NOTIFY_HOOK_EVENTS` 列表。

## 项目结构

```
cladue-notify/
├── notify.json              # 推送配置（根目录，含敏感信息）
├── notify.json.example      # 配置示例
├── main.py                  # 主入口：事件读取、格式化、发送
├── notify_hook.sh           # Hook 入口脚本（bash）
├── scripts/
│   └── install_hooks.py     # 安装 Claude Code hooks
├── src/
│   ├── __init__.py
│   ├── config.py            # 配置加载
│   ├── lark.py              # 飞书消息格式化
│   └── webhook.py           # HTTP 请求发送
└── test_events/             # 测试事件 JSON
```

## 飞书 webhook 配置

你需要一个中转服务来接收 Claude Code 的通知并转发到飞书。示例实现：

```python
# 伪代码示例
from fastapi import FastAPI, Request
import requests

app = FastAPI()

@app.post("/claude")
async def receive_claude_notification(request: Request):
    data = await request.json()
    # 验证 authorization token
    
    # 转发到飞书 webhook
    feishu_webhook = "https://open.feishu.cn/open-apis/bot/v2/hook/XXX"
    requests.post(feishu_webhook, json={
        "msg_type": "text",
        "content": {"text": data["message"]}
    })
```

## 故障排查

### Hook 没触发

1. 检查 `~/.claude/settings.json` 中 `hooks` 是对象而非数组
2. 运行 `python3 scripts/install_hooks.py` 重装
3. 在 Claude Code 中执行 `/hooks` 查看已安装 hooks

### 没收到飞书消息

1. 检查根目录 `notify.json` 的 `webhook` 是否正确
2. 用 `--dry-run` 确认格式化正常
3. 检查中转服务日志

### 权限问题

```bash
chmod +x notify_hook.sh
# 或重新运行
python3 scripts/install_hooks.py
```

## 参考

- [Claude Code Hooks](https://code.claude.com/docs/en/hooks)
- [飞书机器人文档](https://open.feishu.cn/document/server-docs/chat-robot/overview)