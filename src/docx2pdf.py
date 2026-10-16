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


def convert_docx2pdf(docx_dir: str) -> None:
    """把目录下的 docx 逐份另存为 pdf（单份失败不影响其余文件）。"""
    try:
        word = win32.Dispatch("Word.Application")
        word.Visible = False
    except Exception as exc:
        logger.exception("未检测到 Microsoft Word 2010 或更高版本: %s", exc)
        return

    docx_files = [name for name in os.listdir(docx_dir) if name.endswith(".docx")]
    logger.info("开始转换: 目录=%s, docx 数量=%d", docx_dir, len(docx_files))
    if not docx_files:
        logger.warning("目录下没有 docx 文件: %s", docx_dir)

    converted = 0
    failed = 0
    for name in docx_files:
        docx_file = os.path.join(docx_dir, name)
        pdf_file = os.path.join(docx_dir, name.replace(".docx", ".pdf"))
        try:
            doc = word.Documents.Open(os.path.abspath(docx_file))
            doc.SaveAs(os.path.abspath(pdf_file), FileFormat=PDF_FILE_FORMAT)
            doc.Close(SaveChanges=0)  # 不保存退出
            converted += 1
        except Exception as exc:
            failed += 1
            logger.exception("转换失败 %s: %s", docx_file, exc)

    logger.info("转换完成: 成功 %d, 失败 %d", converted, failed)
    word.Quit()


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
