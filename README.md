# cladue-notify

将 [Claude Code](https://code.claude.com/) 的 Hook 事件推送到飞书（Lark）。

## 工作原理

```
Claude Code 触发已注册的事件
        │
        ▼
~/.claude/settings.json 中的 hook
        │
        ▼
notify_hook.sh → main.py
        │
        ├─ 读取 notify.json
        ├─ 格式化飞书 text 消息
        └─ POST 到 webhook
```

哪些事件会推送，完全由 `~/.claude/settings.json` 里注册了哪些 hook 决定。`main.py` 不做二次过滤。

## 环境要求

- macOS / Linux
- Python 3.10+（仅标准库）
- [Claude Code CLI](https://code.claude.com/docs/en/setup)

## 快速开始

### 1. 配置

复制示例配置并填入 webhook 地址：

```bash
cp notify.json.example notify.json
```

`notify.json` 放在**项目根目录**：

```json
{
  "webhook": "https://your-notify-server.example/claude?type=feishu&authorization=YOUR_TOKEN",
  "timeout": 10
}
```

| 字段 | 说明 |
|------|------|
| `webhook` | 飞书推送地址 |
| `timeout` | HTTP 超时（秒），默认 10 |

### 2. 安装 Hooks

```bash
python3 scripts/install_hooks.py
```

将默认 14 个事件的 hook 写入 `~/.claude/settings.json`（异步执行，不阻塞 Claude）。

安装后重启 Claude Code 或新开 session。

### 3. 验证

```bash
python3 main.py --dry-run --test-file test_event.json
```

## 支持的事件

默认在 `scripts/install_hooks.py` 中注册：

| 事件 | 场景 |
|------|------|
| `Notification` | 需要批准、等待输入、认证成功 |
| `Stop` | 完成一轮回复 |
| `StopFailure` | API 错误 |
| `PermissionRequest` | 权限确认 |
| `PermissionDenied` | 自动模式拒绝 |
| `Elicitation` / `ElicitationResult` | MCP 表单交互 |
| `SessionStart` / `SessionEnd` | 会话开始/结束 |
| `SubagentStart` / `SubagentStop` | 子代理启停 |
| `TeammateIdle` | 队友空闲 |
| `TaskCreated` / `TaskCompleted` | 任务创建/完成 |

要增减推送的事件，编辑 `scripts/install_hooks.py` 里的 `NOTIFY_HOOK_EVENTS`，然后重新运行安装脚本。

`src/lark.py` 还支持 `UserPromptSubmit`、`PreToolUse`、`PostToolUse` 的格式化，但未默认注册（频率太高）。

## 命令行

```bash
python3 main.py --list-events
python3 main.py --dry-run --test-file test_events/stop_failure.json
echo '{"hook_event_name":"Stop","cwd":"/tmp","session_id":"abc"}' | python3 main.py --dry-run
```

## 项目结构

```
cladue-notify/
├── notify.json             # 推送配置（根目录）
├── notify.json.example     # 配置示例
├── main.py                 # 主入口
├── notify_hook.sh          # Hook 入口脚本
├── scripts/install_hooks.py
└── src/
    ├── config.py
    ├── lark.py
    └── webhook.py
```

## 故障排查

**Hook 没触发：** 确认 `~/.claude/settings.json` 中 `hooks` 是对象而非数组，运行 `python3 scripts/install_hooks.py` 重装，执行 `/hooks` 检查。

**没收到飞书消息：** 检查根目录 `notify.json` 的 `webhook` 是否正确，用 `--dry-run` 确认格式化正常。

**Permission denied：** `chmod +x notify_hook.sh` 或重新运行安装脚本。

## 参考

- [Claude Code Hooks](https://code.claude.com/docs/en/hooks)
