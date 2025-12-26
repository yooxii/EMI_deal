import logging
from pathlib import Path
from logging import Filter, LogRecord


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
