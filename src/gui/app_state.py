"""界面状态的持久化。

把主窗口的输入内容与设置开关保存到用户配置目录下的 JSON 文件，程序异常退出后
重新打开会自动恢复，避免重复输入。

设计要点：

- 写入采用「临时文件 + 原子替换」，即使写到一半崩溃也不会留下损坏文件；
- 每次输入变化即落盘（由调用方做防抖），不依赖正常退出流程。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

STATE_FILENAME = "ui_state.json"
FALLBACK_DIR_NAME = "EMI-Report"

# 状态键名
KEY_TEMPLATE_PATH = "template_path"
KEY_MODEL_PATH = "model_path"
KEY_LOAD_QTY = "load_qty"
KEY_WEEK = "week"
KEY_REV = "rev"
KEY_WORKNO = "workno"
KEY_IMAGE_PATH = "image_path"
KEY_TEST_DETAIL = "test_detail"
KEY_TEST_DATE = "test_date"
KEY_SETTINGS = "settings"


def state_directory() -> str:
    """状态文件目录：优先 Qt 应用配置目录，取不到时退回本地应用数据目录。"""
    app = QApplication.instance()
    if app is not None and app.applicationName():
        location = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppConfigLocation
        )
        if location:
            return location
    fallback = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(fallback, FALLBACK_DIR_NAME)


class AppState:
    """JSON 形式的界面状态存取。"""

    def __init__(self, path: str | None = None) -> None:
        self.path = path or os.path.join(state_directory(), STATE_FILENAME)
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            with open(self.path, encoding="utf-8") as fp:
                data = json.load(fp)
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as exc:
            logger.warning("读取界面状态失败(%s): %s", self.path, exc)
            return {}

        if not isinstance(data, dict):
            logger.warning("界面状态格式异常，已忽略: %s", self.path)
            return {}
        return data

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def update(self, values: dict[str, Any]) -> None:
        """合并若干键值并立即落盘。"""
        self._data.update(values)
        self.save()

    def save(self) -> None:
        """原子写入状态文件：先写临时文件，再整体替换。"""
        try:
            directory = os.path.dirname(self.path)
            if directory:
                os.makedirs(directory, exist_ok=True)

            tmp_path = f"{self.path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as fp:
                json.dump(self._data, fp, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.path)
            logger.debug("界面状态已保存: %s", self.path)
        except OSError as exc:
            logger.warning("保存界面状态失败(%s): %s", self.path, exc)
