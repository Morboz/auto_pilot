import logging
import sys

from .config import settings

# 定义日志格式
# 包含时间、模块名、日志级别、消息
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class CustomFormatter(logging.Formatter):
    """自定义 Formatter，可以添加颜色等（如果需要）"""

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_str = LOG_FORMAT

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: grey + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt=DATE_FORMAT)
        return formatter.format(record)


def setup_logging():
    """配置全局日志系统"""
    log_level = settings.log_level.upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    # 使用自定义格式（带颜色）
    # 如果是在非 TTY 环境（如文件重定向），可能需要去掉颜色，这里简单起见默认带颜色
    console_handler.setFormatter(CustomFormatter())

    # 配置根 Logger
    # 注意：我们不直接使用 logging.basicConfig，因为它会配置 root logger
    # 我们主要关心 auto_pilot 命名空间下的日志
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # 清除现有的 handlers (避免重复)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.addHandler(console_handler)

    # 专门配置 auto_pilot 的 logger
    app_logger = logging.getLogger("auto_pilot")
    app_logger.setLevel(numeric_level)
    app_logger.propagate = True  # 让它冒泡到 root logger 处理

    # 调整第三方库的日志
    # 比如屏蔽一些过于啰嗦的库
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    app_logger.info("Logging initialized with level: %s", log_level)


def get_logger(name: str) -> logging.Logger:
    """
    获取 logger 实例
    使用方法: logger = get_logger(__name__)
    """
    return logging.getLogger(name)
