"""命令行版 docx 转 pdf（保留给不启动 GUI 的批处理场景）。

用法：``python docx2pdf.py <docx_dir>``
"""

from __future__ import annotations

import logging
import os
import sys

import win32com.client as win32

logger = logging.getLogger(__name__)

PDF_FILE_FORMAT = 17  # Word 的 wdFormatPDF


def _attach_word():
    """取得 Word COM 对象，返回 ``(word, started_here)``。

    优先连接**已在运行**的 Word（GetActiveObject），这样转换结束后不会把用户
    自己打开的文档一起关掉；只有确实由本进程启动 Word 时才负责 Quit。
    """
    try:
        return win32.GetActiveObject("Word.Application"), False
    except Exception:
        word = win32.Dispatch("Word.Application")
        word.Visible = False
        return word, True


def convert_docx_files(docx_paths, retries: int = 3) -> tuple[int, int]:
    """把指定的 docx 逐个另存为同名 pdf，返回 ``(成功数, 失败数)``。

    单份失败时重新连接 Word 再试（最多 ``retries`` 次）——Word COM 在连续转换
    上百份文件时会偶发 ``RPC 服务器不可用``／``<unknown>.Open``，重连后通常即可恢复；
    全部结束后仅在本进程启动过 Word 时退出 Word。
    """
    import time

    docx_paths = [os.path.abspath(path) for path in docx_paths]
    if not docx_paths:
        return 0, 0

    try:
        word, started_here = _attach_word()
    except Exception as exc:
        logger.exception("未检测到 Microsoft Word 2010 或更高版本: %s", exc)
        raise

    converted = 0
    failed = 0
    for docx_file in docx_paths:
        pdf_file = os.path.splitext(docx_file)[0] + ".pdf"
        for attempt in range(1, retries + 1):
            try:
                doc = word.Documents.Open(docx_file)
                doc.SaveAs(pdf_file, FileFormat=PDF_FILE_FORMAT)
                doc.Close(SaveChanges=0)  # 不保存退出
                if os.path.exists(pdf_file):
                    converted += 1
                else:
                    raise RuntimeError("PDF 未生成")
                break
            except Exception as exc:
                if attempt >= retries:
                    failed += 1
                    logger.exception(
                        "转换失败（已重试 %d 次）%s: %s", retries, docx_file, exc
                    )
                    break
                logger.warning(
                    "转换失败，重连 Word 后重试(%d/%d) %s: %s",
                    attempt,
                    retries,
                    os.path.basename(docx_file),
                    exc,
                )
                time.sleep(2)
                try:
                    word, started = _attach_word()
                    started_here = started_here or started
                except Exception:  # noqa: BLE001 - 重连失败也继续重试
                    logger.exception("重新连接 Word 失败")

    if started_here:
        try:
            word.Quit()
        except Exception:  # noqa: BLE001 - Word 可能已自行退出
            logger.warning("退出 Word 失败（可能已自行退出）")
    return converted, failed


def convert_docx2pdf(docx_dir: str) -> None:
    """把目录下的 docx 逐份另存为 pdf（单份失败不影响其余文件）。"""
    docx_files = [name for name in os.listdir(docx_dir) if name.endswith(".docx")]
    logger.info("开始转换: 目录=%s, docx 数量=%d", docx_dir, len(docx_files))
    if not docx_files:
        logger.warning("目录下没有 docx 文件: %s", docx_dir)
        return

    converted, failed = convert_docx_files(
        [os.path.join(docx_dir, name) for name in docx_files]
    )
    logger.info("转换完成: 成功 %d, 失败 %d", converted, failed)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python docx2pdf.py <docx_dir>")
        return 1

    docx_dir = argv[1]
    if not os.path.exists(docx_dir):
        print("Error: docx_dir not exists.")
        return 1

    logging.basicConfig(level=logging.INFO)
    convert_docx2pdf(docx_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
