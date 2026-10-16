"""日志基础设施。

- ``setup_logging()``：配置 root logger（控制台 + 文件双输出）
- ``get_error_logger()``：独立的 ``error.log``，完整记录崩溃与 traceback
- ``safe_execute()`` / ``log_checkpoint()``：可选的函数级埋点工具
"""

from __future__ import annotations

import logging
import traceback
from datetime import datetime
from functools import wraps
from logging import Filter, LogRecord
from pathlib import Path
from typing import Callable

DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
USER_LOG_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - [User: %(user)s] - %(message)s"
)
ERROR_LOG_FORMAT = (
    "%(asctime)s - %(levelname)s - "
    "[%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s"
)
ERROR_LOG_FILENAME = "error.log"
SEPARATOR = "=" * 80


class UserContextFilter(Filter):
    """给每条日志记录补充当前用户信息（预留多用户场景）。"""

    def __init__(self, current_user: str = "Unknown") -> None:
        super().__init__()
        self.current_user = current_user

    def filter(self, record: LogRecord) -> bool:
        record.user = self.current_user
        return True


user_context_filter = UserContextFilter()


class UserContextFormatter(logging.Formatter):
    """带 ``[User: xxx]`` 字段的格式器，与 :data:`user_context_filter` 搭配使用。"""

    def __init__(self, fmt: str | None = None, datefmt: str | None = None) -> None:
        super().__init__(fmt or USER_LOG_FORMAT, datefmt or DEFAULT_DATE_FORMAT)

    def format(self, record: LogRecord) -> str:
        if not hasattr(record, "user"):
            record.user = user_context_filter.current_user
        return super().format(record)


def setup_logging(
    log_level: int = logging.INFO,
    log_dir: str = "logs",
    log_filename: str = "app.log",
) -> None:
    """配置全局日志：同时输出到控制台和文件（UTF-8）。重复调用不会重复挂 handler。"""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    full_log_path = log_path / log_filename

    formatter = logging.Formatter(fmt=DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(full_log_path, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        root_logger.addFilter(user_context_filter)


class ErrorLogger:
    """把崩溃/异常连同 traceback 写入独立错误日志，便于事后定位。"""

    def __init__(self, error_log_path: str = ERROR_LOG_FILENAME) -> None:
        self.error_log_path = error_log_path
        self.error_logger = logging.getLogger("error_logger")
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        self.error_logger.setLevel(logging.ERROR)
        if self.error_logger.handlers:
            return
        error_handler = logging.FileHandler(self.error_log_path, encoding="utf-8")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(
            logging.Formatter(ERROR_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
        )
        self.error_logger.addHandler(error_handler)

    def log_error(
        self,
        error_msg: str,
        exc_info: BaseException | None = None,
        context: str = "",
    ) -> None:
        """记录一条带上下文的错误；传入异常对象时会附带完整 traceback。"""
        try:
            timestamp = datetime.now().strftime(DEFAULT_DATE_FORMAT)
            lines = [
                f"\n{SEPARATOR}",
                f"CRASH/ERROR DETECTED at {timestamp}",
                f"Context: {context}",
                f"Error: {error_msg}",
            ]
            if exc_info is not None:
                lines.append(f"Exception Type: {type(exc_info).__name__}")
                lines.append(f"Exception Details: {exc_info}")
                lines.append(
                    "Traceback:\n"
                    + "".join(
                        traceback.format_exception(
                            type(exc_info), exc_info, exc_info.__traceback__
                        )
                    )
                )
            lines.append(f"{SEPARATOR}\n")
            self.error_logger.error("\n".join(lines))

            logging.getLogger(__name__).error("ERROR in %s: %s", context, error_msg)
        except Exception as exc:  # 错误日志自身异常时退化为控制台输出
            print(f"CRITICAL: Error logger failed: {exc}")
            print(f"Original error: {error_msg}")


_error_logger: ErrorLogger | None = None


def get_error_logger() -> ErrorLogger:
    """获取（或创建）全局错误日志实例。"""
    global _error_logger
    if _error_logger is None:
        _error_logger = ErrorLogger()
    return _error_logger


def _show_error_dialog(context: str, exc: BaseException) -> None:
    """尽力弹出一个 Qt 错误框；无 GUI 环境时静默跳过。"""
    try:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.critical(
            None,
            "错误",
            f"操作失败: {context}\n\n错误信息: {exc}\n\n详细信息已记录到 error.log",
        )
    except Exception:  # 无 Qt 环境属于预期情况
        logging.getLogger(__name__).debug("无法显示错误对话框", exc_info=True)


def safe_execute(context: str = "", show_error_dialog: bool = False) -> Callable:
    """装饰器：记录函数进入/完成，异常写入错误日志，可选弹框后重新抛出。

    :param context: 该函数所属的业务场景描述
    :param show_error_dialog: 是否在异常时弹出错误对话框
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            error_logger = get_error_logger()
            func_name = func.__name__
            full_context = f"{context} - {func_name}" if context else func_name
            main_logger = logging.getLogger(__name__)

            try:
                main_logger.info("ENTERING: %s", full_context)
                result = func(*args, **kwargs)
                main_logger.info("COMPLETED: %s", full_context)
                return result
            except Exception as exc:
                error_logger.log_error(
                    f"Exception in {func_name}", exc_info=exc, context=full_context
                )
                if show_error_dialog:
                    _show_error_dialog(full_context, exc)
                raise

        return wrapper

    return decorator


def log_checkpoint(message: str, context: str = "") -> None:
    """记录调试检查点：主日志一条，同时追加到 error.log，便于回溯崩溃前最后一步。"""
    checkpoint_msg = f"CHECKPOINT: {context} - {message}"
    logging.getLogger(__name__).info(checkpoint_msg)
    with open(get_error_logger().error_log_path, "a", encoding="utf-8") as fp:
        fp.write(f"{datetime.now().strftime(DEFAULT_DATE_FORMAT)} - {checkpoint_msg}\n")
