"""配置管理模块"""
import json
import sys
from pathlib import Path
from typing import Optional


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        project_root = Path(__file__).parent.parent
        self.config_path = Path(config_path) if config_path else project_root / "notify.json"
        self._config: dict = {}
        self._load_config()

    def _load_config(self) -> None:
        if not self.config_path.exists():
            print(f"警告: 配置文件不存在 {self.config_path}", file=sys.stderr)
            self._config = {}
            return

        try:
            with open(self.config_path, encoding="utf-8") as f:
                self._config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"警告: 配置文件格式错误 {e}", file=sys.stderr)
            self._config = {}

    @property
    def webhook(self) -> str:
        return self._config.get("webhook", "")

    @property
    def timeout(self) -> int:
        return self._config.get("timeout", 10)


def load_config() -> ConfigManager:
    return ConfigManager()
