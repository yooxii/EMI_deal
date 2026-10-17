"""按机种名找测试图片。

图片目录里的命名约定：文件名第一段（下划线分隔）就是机种名，例如
``FSL028-EL2G_20250313_101559.png``；有些图片只写到前 6 位（``FSL028_...``），
只要前 6 位相同就算同一系列，可以给该系列下不同后缀的机种共用。

匹配优先级：机种名完全一致 > 前 6 位一致的「系列图」 > 同系列其它后缀的图；
同优先级里取文件名日期最新的那张。
"""

from __future__ import annotations

import os
import re

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".emf", ".wmf")
SERIES_LENGTH = 6  # 机种系列号长度（前 6 位）
DEFAULT_PIC_DIR = r"D:\Desktop_Li\WorkDir\PIC\EMI"

_DATE_IN_NAME = re.compile(r"(20\d{6})")


def series_of(model: str) -> str:
    """取机种系列号（前 6 位，大写）。"""
    return (model or "").strip().upper()[:SERIES_LENGTH]


def image_model_token(filename: str) -> str:
    """图片文件名里的机种名：下划线分隔的第一段（大写、去后缀）。"""
    stem = os.path.splitext(filename)[0]
    return stem.split("_")[0].strip().upper()


def _date_rank(filename: str) -> int:
    """文件名里的日期（20250313）用于挑最新的一张；没有日期就排最后。"""
    match = _DATE_IN_NAME.search(os.path.splitext(filename)[0])
    return int(match.group(1)) if match else 0


def iter_pictures(pic_dir: str):
    """遍历图片目录里的图片文件名（不递归子目录）。"""
    if not pic_dir or not os.path.isdir(pic_dir):
        return
    for name in os.listdir(pic_dir):
        if name.lower().endswith(IMAGE_SUFFIXES):
            yield name


def model_image_rank(model: str, filename: str) -> int | None:
    """``filename`` 作为 ``model`` 的配图有多合适：0 最好，None 表示不匹配。"""
    token = image_model_token(filename)
    target = (model or "").strip().upper()
    series = series_of(target)
    if not token or not series:
        return None
    if token == target:
        return 0
    if token == series:
        return 1
    if token[:SERIES_LENGTH] == series:
        return 2
    return None


def find_model_image(model: str, pic_dir: str = DEFAULT_PIC_DIR) -> str | None:
    """返回该机种（或同系列机种）对应的图片路径，找不到返回 None。"""
    target = (model or "").strip().upper()
    if not target:
        return None

    best_key: tuple[int, int, int, str] | None = None
    chosen: str | None = None
    for name in iter_pictures(pic_dir):
        rank = model_image_rank(target, name)
        if rank is None:
            continue
        # 排序键：优先级升序 > 日期新 > 名字长（信息更全）> 文件名
        key = (rank, -_date_rank(name), -len(name), name)
        if best_key is None or key < best_key:
            best_key = key
            chosen = name
    if chosen is None:
        return None
    return os.path.join(pic_dir, chosen)


def describe_match(model: str, path: str) -> str:
    """说明这张图是怎么匹配到的（写日志用）。"""
    token = image_model_token(os.path.basename(path))
    target = (model or "").strip().upper()
    if token == target:
        return "机种名一致"
    if token == series_of(target):
        return "同系列（前 %d 位一致）" % SERIES_LENGTH
    return "同系列其它后缀"
