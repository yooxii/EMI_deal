# -*- coding: utf-8 -*-
import os
import sys
import logging
from logging import Filter, LogRecord
from pathlib import Path
import traceback
from datetime import datetime
from functools import wraps


class UserContextFilter(Filter):
    """
    自定义日志过滤器，用于在日志中添加用户信息
    """

    def __init__(self):
        super().__init__()
        self.current_user = "Unknown"  # 默认用户为未知

    def filter(self, record: LogRecord) -> bool:
        # 给每条日志记录添加当前用户信息
        record.user = getattr(self, "current_user", "Unknown")
        return True


user_context_filter = UserContextFilter()


class UserContextFormatter(logging.Formatter):
    """
    自定义日志格式器，能够在日志中添加当前用户信息
    """

    def format(self, record):
        # 动态添加用户信息到日志记录中
        if hasattr(user_context_filter, "current_user"):
            record.user = user_context_filter.current_user
        else:
            record.user = "Unknown"

        # 使用带有用户信息的格式
        self._style._fmt = (
            "%(asctime)s - %(name)s - %(levelname)s - [User: %(user)s] - %(message)s"
        )
        return super().format(record)


def setup_logging(log_level=logging.INFO, log_dir="logs", log_filename="app.log"):
    """
    配置全局日志：同时输出到控制台和文件
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    full_log_path = log_path / log_filename

    # 创建格式器
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 创建处理器：控制台
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # 创建处理器：文件（带轮转更佳，这里先用基础版）
    file_handler = logging.FileHandler(full_log_path, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # 获取根 logger 并设置级别
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 避免重复添加 handler（重要！）
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        root_logger.addFilter(user_context_filter)


"""
Enhanced error logging system for crash detection and debugging
"""


class ErrorLogger:
    """Enhanced error logger for crash detection"""

    def __init__(self, error_log_path="error.log"):
        self.error_log_path = error_log_path
        self.setup_error_logging()

    def setup_error_logging(self):
        """Setup dedicated error logging"""
        # Create error logger
        self.error_logger = logging.getLogger("error_logger")
        self.error_logger.setLevel(logging.ERROR)

        # Create file handler for error log
        error_handler = logging.FileHandler(self.error_log_path, encoding="utf-8")
        error_handler.setLevel(logging.ERROR)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        error_handler.setFormatter(formatter)

        # Add handler to logger
        if not self.error_logger.handlers:
            self.error_logger.addHandler(error_handler)

    def log_error(self, error_msg, exc_info=None, context=""):
        """Log error with full context"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Build error message
            full_msg = f"\n{'='*80}\n"
            full_msg += f"CRASH/ERROR DETECTED at {timestamp}\n"
            full_msg += f"Context: {context}\n"
            full_msg += f"Error: {error_msg}\n"

            if exc_info:
                full_msg += f"Exception Type: {type(exc_info).__name__}\n"
                full_msg += f"Exception Details: {str(exc_info)}\n"
                full_msg += f"Traceback:\n{traceback.format_exc()}\n"

            full_msg += f"{'='*80}\n"

            # Log to error file
            self.error_logger.error(full_msg)

            # Also log to main logger
            main_logger = logging.getLogger(__name__)
            main_logger.error(f"ERROR in {context}: {error_msg}")

        except Exception as e:
            # Fallback logging if error logger fails
            print(f"CRITICAL: Error logger failed: {e}")
            print(f"Original error: {error_msg}")


# Global error logger instance
_error_logger = None


def get_error_logger():
    """Get or create global error logger instance"""
    global _error_logger
    if _error_logger is None:
        _error_logger = ErrorLogger()
    return _error_logger


def safe_execute(context="", show_error_dialog=False):
    """
    Decorator to safely execute functions with comprehensive error logging

    Args:
        context: Description of what the function does
        show_error_dialog: Whether to show error dialog to user
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            error_logger = get_error_logger()
            func_name = func.__name__
            full_context = f"{context} - {func_name}" if context else func_name

            try:
                # Log function entry
                main_logger = logging.getLogger(__name__)
                main_logger.info(f"ENTERING: {full_context}")

                # Execute function
                result = func(*args, **kwargs)

                # Log successful completion
                main_logger.info(f"COMPLETED: {full_context}")
                return result

            except Exception as e:
                # Log the error
                error_logger.log_error(
                    f"Exception in {func_name}", exc_info=e, context=full_context
                )

                # Show error dialog if requested
                if show_error_dialog:
                    try:
                        from PySide6.QtWidgets import QMessageBox

                        QMessageBox.critical(
                            None,
                            "错误",
                            f"操作失败: {full_context}\n\n错误信息: {str(e)}\n\n详细信息已记录到 error.log",
                        )
                    except:
                        pass

                # Re-raise or return None based on context
                raise

        return wrapper

    return decorator


def log_checkpoint(message, context=""):
    """Log a checkpoint for debugging"""
    logger = logging.getLogger(__name__)
    error_logger = get_error_logger()

    checkpoint_msg = f"CHECKPOINT: {context} - {message}"
    logger.info(checkpoint_msg)

    # Also write to error log for complete trace
    with open(error_logger.error_log_path, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {checkpoint_msg}\n")
