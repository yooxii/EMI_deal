"""从报告文件名中提取命名片段（如序列号）。

报告文件按 ``序列号-输入电压-负载-线性.pdf`` 命名，因此「按分隔符取第一段」
就能得到序列号。文件夹模式下同一序列号会出现多次，这里统一去重并保持顺序。
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_SEPARATOR = "-"


def name_token(filename: str, separator: str = DEFAULT_SEPARATOR) -> str:
    """取文件名（去掉扩展名）按分隔符切分后的第一段。"""
    stem = os.path.splitext(os.path.basename(filename))[0]
    return stem.split(separator)[0].strip()


def collect_name_tokens(
    path: str, suffix: str, separator: str = DEFAULT_SEPARATOR
) -> list[str]:
    """收集文件夹（或单个文件）内文件名首段，按出现顺序去重。

    :param path: 文件夹路径或单个文件路径
    :param suffix: 需要匹配的扩展名，例如 ``.pdf`` / ``.docx``（大小写不敏感）
    :param separator: 名称分隔符，默认为 ``-``
    :return: 去重后的名称首段列表；路径无效时返回空列表
    """
    if not path:
        return []

    if os.path.isfile(path):
        names = [os.path.basename(path)]
    elif os.path.isdir(path):
        names = sorted(
            name for name in os.listdir(path) if name.lower().endswith(suffix.lower())
        )
    else:
        logger.warning("路径不存在，无法提取名称: %s", path)
        return []

    if not names:
        logger.warning("路径下没有 %s 文件: %s", suffix, path)

    tokens: list[str] = []
    for name in names:
        token = name_token(name, separator)
        if token and token not in tokens:
            tokens.append(token)
    logger.debug("从 %s 提取到 %d 个名称片段: %s", path, len(tokens), tokens)
    return tokens
