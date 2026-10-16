"""EMI 报告自动化主程序。

把 EMI PDF 报告解析成测量数据，按模板写入 Excel，并按需生成 / 嵌入原始 PDF 压缩包。
"""

from __future__ import annotations

import logging
import os
import re
import sys
import time
import zipfile
from io import BytesIO
from typing import Any, Callable, NamedTuple, Sequence

import openpyxl as xl
import pdfplumber
import win32com.client as win32
from openpyxl.drawing import image
from PIL import Image as PImage
from PySide6 import __version__ as pyside_version
from PySide6.QtCore import QDate, QSize, QStandardPaths, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.app_state import (
    KEY_IMAGE_PATH,
    KEY_LOAD_QTY,
    KEY_MODEL_PATH,
    KEY_REV,
    KEY_SETTINGS,
    KEY_TEMPLATE_PATH,
    KEY_TEST_DATE,
    KEY_TEST_DETAIL,
    KEY_WEEK,
    KEY_WORKNO,
    AppState,
)
from gui.mainWin import MainWindow
from gui.ui_docx2pdf import Docx2PdfWindow
from gui.ui_wordreplace import WordReplace
from logger import get_error_logger, log_checkpoint, setup_logging
from naming import collect_name_tokens

# --------------------------------------------------------------------------- #
# 常量与配置
# --------------------------------------------------------------------------- #

LOG_FILENAME = "EMIRper.log"
APP_TITLE = "EMI-Report"  # 窗口标题前缀（后面跟随数据路径的文件夹名）
APP_VERSION = "2.1"
STATE_SAVE_DELAY_MS = 300  # 输入变化后延迟落盘的防抖时间
SERIAL_REFRESH_DELAY_MS = 500  # 数据路径变化后延迟刷新序列号的防抖时间
REPORT_FILE_SUFFIX = ".pdf"  # 提取序列号时依据的报告文件后缀
VOLTAGE_KINDS = 2  # 模板中每个机种的电压档数（220V / 110V）
PHASE_KINDS = 2  # 每档负载下的相线行数（Line / Neutral）
MAX_NOTICE_ITEMS = 8  # 提示框内最多列出的条件条数
TEMPLATE_DIR = "template"
TEMPLATE_COUNT_PATTERN = r"_(\d+)\.xlsx$"  # 模板名里的数量后缀，如 _3.xlsx / _10.xlsx
DEFAULT_LOAD_QTY = 3
MAX_UUT_COUNT = 5  # 模板支持的最大机种（负载类型）数量
ROWS_PER_UUT_UNIT = 4  # 每个机种每档负载占用 4 行
ROWS_PER_LOAD_STEP = 2  # 同一机种内每档负载间隔 2 行
REPORT_TAIL_ROWS = 4  # 报告表格尾部的行数（计算数据结束行时扣除）
EMPTY_MARK = "-"  # 数据行中固定填 "-" 的列
LINE_LABELS = {"L1": "Line", "N": "Neutral"}
PHASE_FILE_TOKENS = {label: token for token, label in LINE_LABELS.items()}

# PDF 文本解析位置（行、列均从 0 起算）
PDF_HEADER_LINE_LIMIT = 20  # Serial / Power / Load 出现在前若干行内
PDF_DATA_START_LINE = 15  # 测量数据表起始行
PDF_DATA_MIN_COLUMNS = 10  # 视为数据行所需的最小列数
PDF_PK_COLUMN = 4  # PK 值所在列
PDF_AVG_COLUMN = 7  # AVG 值所在列
PDF_LINE_COLUMN = 9  # L1 / N 标识所在列

# 报告模板中的锚点
SETUP_SHEET_NAME = "Setup"
REPORT_SHEET_NAME = "Conducted EMI"
SETUP_ANCHOR_COLUMN = 2  # Setup 表的 B 列存放锚点数值
SETUP_ANCHOR_ROWS = {  # 属性名 -> Setup 表行号
    "row_sn_": 1,
    "col_sn_": 2,
    "col_vol_": 3,
    "col_line_": 4,
    "col_load_": 5,
    "row_end_": 7,
    "col_end_": 8,
}
DEFAULT_ANCHORS = {  # 未读到模板时使用的兜底锚点
    "row_sn_": 44,
    "col_sn_": 4,
    "col_vol_": 11,
    "col_line_": 13,
    "col_load_": 14,
    "row_end_": 103,
    "col_end_": 27,
}
HEADER_CELL_MODEL = "F5"  # 单体型号
HEADER_CELL_DATE = "F6"  # 测试日期
HEADER_CELL_DETAIL = "F8"  # 测试细节
HEADER_CELL_WORKNO = "F44"  # 工令
HEADER_CELL_REV = "H44"  # 版本
HEADER_CELL_WEEK = "I44"  # 周期 / D/C
IMAGE_ANCHOR_CELL = "C27"  # 测试图片插入位置
IMAGE_HEIGHT_PIXELS = 250  # 图片按高度等比缩放
IMAGE_JPEG_QUALITY = 100
# 数据列偏移 -> PDF 数据行的字段下标（None 表示固定写 EMPTY_MARK）
MEASUREMENT_CELL_SOURCES: tuple[tuple[int, int | None], ...] = (
    (1, 0),
    (2, 1),
    (3, 3),
    (4, 6),
    (5, None),
    (6, 2),
    (7, 5),
)


def template_path_for(load_qty: int) -> str:
    """按负载数量拼出 ``template/`` 下对应的模板路径（如 ``..._10.xlsx``）。"""
    return os.path.join(TEMPLATE_DIR, f"2.1 Conducted EMI Measurement_{load_qty}.xlsx")


class SettingItem(NamedTuple):
    """一条布尔型设置项的定义。"""

    key: str
    label: str
    tooltip: str
    default: bool


SETTING_ITEMS = (
    SettingItem(
        "NeedZip", "生成压缩包:", "是否生成压缩包，压缩包中包含原始PDF文件。", True
    ),
    SettingItem("AddZip", "嵌入压缩包:", "是否嵌入压缩包到excel文件。", True),
    SettingItem(
        "CloseExcel",
        "执行完毕关闭Excel程序:",
        "是否在处理完毕后关闭excel程序，默认保留。",
        False,
    ),
)

# 「帮助 → 使用文档」窗口显示的正文（v + 版本号）
HELP_DOCUMENT = (
    "EMI-Report 使用文档（v" + APP_VERSION + "）\n"
    "\n"
    "一、准备\n"
    "  1. 用 ELEKTRA 导出 EMI 报告 PDF，文件名保持「序列号-输入电压-负载-线性.pdf」。\n"
    "  2. 把同一机种的报告放进同一个文件夹（建议文件夹名也用「序列号-机种」）。\n"
    "  3. 本机需安装 Microsoft Word 与 Excel（转 PDF、嵌入压缩包时使用）。\n"
    "\n"
    "二、主界面操作\n"
    "  1. 模版路径：可留空。留空时按「负载数量」自动选用\n"
    "     template/2.1 Conducted EMI Measurement_{N}.xlsx（现有 _1 / _3 / _4 / _10）。\n"
    "  2. 数据路径：选择存放 EMI PDF 的文件夹。选好后窗口标题会跟随该文件夹名，\n"
    "     「序列号」区会自动列出文件名中「-」之前的序列号（去重），点击该区标签可刷新。\n"
    "  3. 负载数量：需与模板档数一致（程序以模板文件名中的数字为准）。\n"
    "  4. 测试日期 / 工令 / 版本 / 周期：写入报告表头。\n"
    "  5. 测试图片：可选，鼠标悬停在输入框上可预览。\n"
    "  6. 测试细节：点「点击此处获取」从模板读取，也可手工修改。\n"
    "  7. 点「开始」：解析 PDF → 写入 Excel → 按设置生成 / 嵌入压缩包 → 弹出完成提示。\n"
    "\n"
    "三、数据完整性检查（写入后自动执行）\n"
    "  按 (电压, 负载, 相线) 逐个条件检查数据行：\n"
    "  · 某条件在所有序列号中都没有数据 → 视为未安排该测试：自动删除这些空行并提示；\n"
    "  · 只有部分序列号缺数据，或某行只写了一部分 → 视为异常：程序会检查对应报告文件\n"
    "    （缺失 / 存在但取不到数据）并警告，请补齐报告后重新运行。\n"
    "\n"
    "四、设置（选项 → 设置，Ctrl+I）\n"
    "  · 生成压缩包：把数据目录下的 PDF 打成 zip；\n"
    "  · 嵌入压缩包：把 zip 作为对象插入 Excel 报告；\n"
    "  · 执行完毕关闭 Excel：默认不关闭，便于继续编辑。\n"
    "\n"
    "五、工具\n"
    "  · docx转pdf（Ctrl+T）：选择目录或单个文件批量转 PDF，窗口会预览序列号与文件数量；\n"
    "  · word替换（Ctrl+G）：点「原字符串集」标签可从源路径文件名提取序列号，\n"
    "    点「目标字符串集」标签可把格式控制符整理为单个换行，随后按名称配对替换。\n"
    "\n"
    "六、日志与状态\n"
    "  · 工具 → 查看日志（Ctrl+J）：可更新 / 清空 / 导出日志，出问题先看这里；\n"
    "  · 输入内容与设置会自动保存，程序异常退出后重开自动恢复。\n"
    "\n"
    "七、输出与收尾\n"
    "  · 报告与 zip 生成在「数据路径的上一级目录」，报告名为\n"
    "    2.1 Conducted EMI Measurement_{型号}.xlsx；\n"
    "  · 报告仍需人工补充：日期与测试者、限值标准（默认 Class B）、\n"
    "    插入测试图片与压缩包、整理多余的表格项。\n"
)

# --------------------------------------------------------------------------- #
# 日志
# --------------------------------------------------------------------------- #

setup_logging(log_dir=".", log_filename=LOG_FILENAME)
logger = logging.getLogger(__name__)
error_logger = get_error_logger()


# --------------------------------------------------------------------------- #
# 工作线程
# --------------------------------------------------------------------------- #


class ProcessPdfThread(QThread):
    """遍历目录中的 PDF 报告并解析出测量数据。"""

    progress_updated = Signal(int)  # 已处理文件数
    processing_finished = Signal(dict)  # {文件名: 解析结果}
    processing_error = Signal(str)  # 整体失败信息

    def __init__(self, directory: str) -> None:
        super().__init__()
        self.directory = directory

    def run(self) -> None:
        try:
            result = self.deal_dirs(self.directory)
        except Exception as exc:
            logger.exception("解析 PDF 目录失败: %s", exc)
            self.processing_error.emit(str(exc))
            return
        logger.info("PDF 解析线程结束")
        self.processing_finished.emit(result)

    def open_pdf(self, path_pdf: str) -> dict[str, Any]:
        """读取 PDF 前两页文本并解析成该报告的测量数据。"""
        with pdfplumber.open(path_pdf) as pdf:
            pages = pdf.pages[:2]
            # 部分报告只有一页，取前两页并容忍空文本
            text = "\n".join(page.extract_text() or "" for page in pages)
            logger.debug(
                "%s: 共 %d 页，读取前 %d 页，提取文本 %d 字符",
                os.path.basename(path_pdf),
                len(pdf.pages),
                len(pages),
                len(text),
            )
        return self.deal_datas([line for line in text.split("\n") if line])

    def deal_datas(self, lines: Sequence[str]) -> dict[str, Any]:
        """从 PDF 文本行中提取序号/电压/负载与测量数据行。"""
        result: dict[str, Any] = {}
        for line in lines[:PDF_HEADER_LINE_LIMIT]:
            parts = line.split(" ")
            if parts[0] == "Serial":
                result["Serial"] = parts[-1]
            elif parts[0] == "Power":
                result["Power"] = parts[-1]
            elif parts[0] == "Load":
                result["Load"] = parts[-1]

        missing = [key for key in ("Serial", "Power", "Load") if key not in result]
        if missing:
            logger.warning("PDF 头部字段缺失，可能不是标准报告: %s", ", ".join(missing))

        rows: list[list[str]] = []
        for line in lines[PDF_DATA_START_LINE:]:
            columns = line.split(" ")
            if len(columns) > PDF_DATA_MIN_COLUMNS:
                rows.append(columns)
        if not rows:
            raise ValueError("未从 PDF 中解析到测量数据行")
        for index, row in enumerate(rows, start=1):
            row[0] = str(index)  # 第 1 列重编号为行号

        # 分别按 AVG、PK 升序排序，取两者最小值更小的那份作为报告数据
        rows_by_avg = sorted(rows, key=lambda row: float(row[PDF_AVG_COLUMN]))
        rows_by_pk = sorted(rows, key=lambda row: float(row[PDF_PK_COLUMN]))
        use_avg = float(rows_by_avg[0][PDF_AVG_COLUMN]) <= float(
            rows_by_pk[0][PDF_PK_COLUMN]
        )
        result["datas"] = rows_by_avg if use_avg else rows_by_pk
        logger.debug(
            "解析到 %d 行数据: Serial=%s, Power=%s, Load=%s, 取 %s 排序的首行",
            len(rows),
            result.get("Serial"),
            result.get("Power"),
            result.get("Load"),
            "AVG" if use_avg else "PK",
        )
        return result

    def deal_dirs(self, modeldir: str) -> dict[str, dict[str, Any]]:
        """解析目录内所有 PDF；单个文件失败只记日志并继续。"""
        results: dict[str, dict[str, Any]] = {}
        source_files = [name for name in os.listdir(modeldir) if name.endswith(".pdf")]
        logger.info("开始解析目录 %s，共 %d 个 PDF 文件", modeldir, len(source_files))
        if not source_files:
            logger.warning("目录内没有 PDF 文件: %s", modeldir)

        for index, source_file in enumerate(source_files):
            logger.info("解析 PDF: %s", source_file)
            try:
                results[source_file] = self.open_pdf(
                    os.path.join(modeldir, source_file)
                )
            except Exception as exc:
                logger.exception("解析 PDF 失败 %s: %s", source_file, exc)
                continue
            self.progress_updated.emit(index + 1)

        logger.info(
            "目录解析完成: 成功 %d / 共 %d（失败 %d）",
            len(results),
            len(source_files),
            len(source_files) - len(results),
        )
        return results


class ZipThread(QThread):
    """把目录下所有 PDF 打包成 zip（LZMA 压缩）。"""

    progress_updated = Signal(int)  # 已压缩文件数
    zip_finished = Signal(str)  # 压缩包名（不含扩展名）
    zip_error = Signal(str)  # 压缩失败信息

    def __init__(self, directory: str, zipname: str) -> None:
        super().__init__()
        self.directory = directory
        self.zipname = zipname

    def run(self) -> None:
        try:
            self.zip_folder()
        except Exception as exc:
            logger.exception("压缩失败: %s", exc)
            self.zip_error.emit(str(exc))

    def zip_folder(self) -> None:
        pdf_files: list[tuple] = []
        for root_path, _dirs, files in os.walk(self.directory):
            pdf_files.extend(
                (root_path, name) for name in files if name.endswith(".pdf")
            )

        logger.info("开始压缩 %d 个文件...", len(pdf_files))
        if not pdf_files:
            logger.warning("目录内没有可压缩的 PDF 文件: %s", self.directory)

        zip_path = os.path.abspath(f"{self.zipname}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_LZMA) as archive:
            for index, (root_path, name) in enumerate(pdf_files, start=1):
                file_path = os.path.join(root_path, name)
                archive.write(
                    file_path, arcname=os.path.relpath(file_path, self.directory)
                )
                self.progress_updated.emit(index)

        logger.info(
            "压缩完成: %s (%.2f MB)",
            zip_path,
            os.path.getsize(zip_path) / (1024 * 1024),
        )
        self.zip_finished.emit(self.zipname)


# --------------------------------------------------------------------------- #
# 主窗口
# --------------------------------------------------------------------------- #


class EMIWindow(MainWindow):
    """主窗口：协调 PDF 解析、Excel 写入、压缩与嵌入。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__()

        self.init_var()
        self.load_state()  # 先恢复上次输入（此时尚未连接信号，不会触发回写）
        self.init_connect()
        self.bind_state_tracking()
        self.bind_serial_tracking()
        self.refresh_serial_numbers()  # 按已恢复的数据路径显示一次序列号
        self.install_exception_hook()
        logger.info("主窗口初始化完成，状态文件: %s", self.app_state.path)

    # ---- 初始化 ---------------------------------------------------------- #

    def init_var(self) -> None:
        self.getpdf_running = False

        # Excel 锚点：先给默认值，成功打开模板后由 Setup 表覆盖
        self.row_sn_ = DEFAULT_ANCHORS["row_sn_"]  # 序列号起始行
        self.col_sn_ = DEFAULT_ANCHORS["col_sn_"]  # 序列号列
        self.col_vol_ = DEFAULT_ANCHORS["col_vol_"]  # 输入电压列
        self.col_line_ = DEFAULT_ANCHORS["col_line_"]  # 线性（L1/N）列
        self.col_load_ = DEFAULT_ANCHORS["col_load_"]  # 负载列
        self.row_end_ = DEFAULT_ANCHORS["row_end_"]  # 数据结束行
        self.col_end_ = DEFAULT_ANCHORS["col_end_"]  # 数据结束列

        self.rootpath: str | None = None  # 上次使用的目录
        self.file_count = 0
        self.settings_value = {item.key: item.default for item in SETTING_ITEMS}
        self.settings: dict[str, QCheckBox] = {}  # 设置窗口中的勾选框
        self.windows: list[QWidget] = []  # 已打开的窗口，退出时统一关闭
        self.log_path: str | None = os.path.join(os.getcwd(), LOG_FILENAME)
        self.save_file_name: str | None = None
        self.report_data: dict[str, dict[str, Any]] = {}
        self.Text_log: QTextEdit | None = None
        self.progressBar: QProgressBar | None = None
        self.zip_progressBar: QProgressBar | None = None

        # 界面状态持久化：异常退出后重新打开可自动恢复输入内容
        self.app_state = AppState()
        self.state_timer = QTimer(self)
        self.state_timer.setSingleShot(True)
        self.state_timer.setInterval(STATE_SAVE_DELAY_MS)
        self.state_timer.timeout.connect(self.save_state)

        # 数据路径变化后自动刷新序列号显示
        self.serial_timer = QTimer(self)
        self.serial_timer.setSingleShot(True)
        self.serial_timer.setInterval(SERIAL_REFRESH_DELAY_MS)
        self.serial_timer.timeout.connect(self.refresh_serial_numbers)

    def init_connect(self) -> None:
        self.btn_exit.clicked.connect(self.close)
        self.btn_start.clicked.connect(self.getpdfdatas)
        self.btnfile_template.clicked.connect(self.select_templatepath)
        self.btnfile_model.clicked.connect(self.select_modelpath)
        self.btnfile_img.clicked.connect(self.select_imgpath)
        self.btn_getdetail.clicked.connect(self.get_testdetail)
        self.label_serial.clicked.connect(self.refresh_serial_numbers)
        self.action_exit.triggered.connect(self.close)
        self.action_sets.triggered.connect(self.show_setting)
        self.action_about.triggered.connect(self.show_about)
        self.action_doc.triggered.connect(self.show_helpdoc)
        self.action_log.triggered.connect(self.show_log)
        self.action_topdf.triggered.connect(self.show_docx2pdf)
        self.action_wordreplace.triggered.connect(self.show_wordreplace)

    # ---- 界面状态持久化 -------------------------------------------------- #

    def load_state(self) -> None:
        """恢复上次的输入内容与设置开关（不存在或损坏时退回默认值）。"""
        state = self.app_state

        self.lineEdit_template.setText(str(state.get(KEY_TEMPLATE_PATH, "")))
        self.lineEdit_model.setText(str(state.get(KEY_MODEL_PATH, "")))
        self.lineEdit_week.setText(str(state.get(KEY_WEEK, "")))
        self.lineEdit_rev.setText(str(state.get(KEY_REV, "")))
        self.lineEdit_workerno.setText(str(state.get(KEY_WORKNO, "")))
        self.lineEdit_img.setText(str(state.get(KEY_IMAGE_PATH, "")))
        self.text_detail.setPlainText(str(state.get(KEY_TEST_DETAIL, "")))

        self.spin_qty.setValue(self._as_int(state.get(KEY_LOAD_QTY), DEFAULT_LOAD_QTY))

        saved_date = QDate.fromString(str(state.get(KEY_TEST_DATE, "")), Qt.ISODate)
        if saved_date.isValid():
            self.date_test.setDate(saved_date)

        saved_settings = state.get(KEY_SETTINGS, {})
        if isinstance(saved_settings, dict):
            for item in SETTING_ITEMS:
                self.settings_value[item.key] = bool(
                    saved_settings.get(item.key, item.default)
                )

        logger.info("界面状态已恢复: %s", self.app_state.path)

    @staticmethod
    def _as_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def save_state(self) -> None:
        """把当前输入内容与设置开关写入状态文件（原子写，异常退出也不会丢）。"""
        self.app_state.update(
            {
                KEY_TEMPLATE_PATH: self.lineEdit_template.text(),
                KEY_MODEL_PATH: self.lineEdit_model.text(),
                KEY_LOAD_QTY: self.spin_qty.value(),
                KEY_WEEK: self.lineEdit_week.text(),
                KEY_REV: self.lineEdit_rev.text(),
                KEY_WORKNO: self.lineEdit_workerno.text(),
                KEY_IMAGE_PATH: self.lineEdit_img.text(),
                KEY_TEST_DETAIL: self.text_detail.toPlainText(),
                KEY_TEST_DATE: self.date_test.date().toString(Qt.ISODate),
                KEY_SETTINGS: dict(self.settings_value),
            }
        )

    def _schedule_state_save(self, *_args: Any) -> None:
        """输入变化后延迟落盘，避免每个字符都写一次磁盘。"""
        self.state_timer.start()

    def bind_state_tracking(self) -> None:
        """所有输入控件的变化都触发一次延迟保存。"""
        for line_edit in (
            self.lineEdit_template,
            self.lineEdit_model,
            self.lineEdit_week,
            self.lineEdit_rev,
            self.lineEdit_workerno,
            self.lineEdit_img,
        ):
            line_edit.textChanged.connect(self._schedule_state_save)
        self.text_detail.textChanged.connect(self._schedule_state_save)
        self.spin_qty.valueChanged.connect(self._schedule_state_save)
        self.date_test.dateChanged.connect(self._schedule_state_save)

    # ---- 序列号 ---------------------------------------------------------- #

    def bind_serial_tracking(self) -> None:
        """数据路径变化后延迟刷新序列号显示。"""
        self.lineEdit_model.textChanged.connect(self._schedule_serial_refresh)

    def _schedule_serial_refresh(self, *_args: Any) -> None:
        self.serial_timer.start()

    def refresh_serial_numbers(self, *_args: Any) -> None:
        """从数据路径下的报告文件名中提取序列号并显示（「-」前第一段，去重）。"""
        directory = self.lineEdit_model.text().strip()
        serials = collect_name_tokens(directory, REPORT_FILE_SUFFIX)
        self.text_serial.setPlainText("\n".join(serials))
        if serials:
            logger.info("序列号刷新: %d 个（%s）", len(serials), directory)
        else:
            logger.debug("序列号刷新: 未提取到序列号（%s）", directory)
        self.update_window_title()

    def update_window_title(self) -> None:
        """窗口标题跟随数据路径最后一级文件夹名称。"""
        directory = self.lineEdit_model.text().strip().rstrip("\\/")
        folder_name = os.path.basename(directory) if directory else ""
        title = f"{APP_TITLE} - {folder_name}" if folder_name else APP_TITLE
        if title != self.windowTitle():
            self.setWindowTitle(title)
            logger.debug("窗口标题更新为: %s", title)

    def install_exception_hook(self) -> None:
        """未捕获异常时先落盘再走默认处理，保证异常退出也不丢输入。"""
        sys.excepthook = self._on_uncaught_exception

    def _on_uncaught_exception(
        self, exc_type: type, exc_value: BaseException, exc_tb: Any
    ) -> None:
        error_logger.log_error(
            "未捕获异常", exc_info=exc_value, context="uncaught exception"
        )
        try:
            self.save_state()
        except Exception:
            logger.exception("异常退出时保存界面状态失败")
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    # ---- 路径选择 -------------------------------------------------------- #

    def _start_directory(self) -> str:
        """文件对话框的默认目录。"""
        if self.rootpath and os.path.exists(self.rootpath):
            return self.rootpath
        return QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )

    def select_modelpath(self) -> None:
        """选择存放 EMI PDF 报告的机种目录。"""
        log_checkpoint("Before opening directory dialog", "select_modelpath")
        try:
            path = QFileDialog.getExistingDirectory(
                self, self.tr("选择测试数据所在目录"), dir=self._start_directory()
            )
            log_checkpoint("After directory dialog closed", "select_modelpath")
            if path:
                self.rootpath = os.path.split(path)[0]
                self.lineEdit_model.setText(path)
                logger.info("已选择数据目录: %s", path)
        except Exception as exc:
            error_logger.log_error(
                "Failed to select model path", exc_info=exc, context="select_modelpath"
            )
            QMessageBox.critical(
                self, "错误", f"选择目录失败: {exc}\n详细信息已记录到 error.log"
            )

    def select_templatepath(self) -> str | None:
        """选择 Excel 模板，返回所选路径（取消时返回 None）。"""
        log_checkpoint("Before opening file dialog", "select_templatepath")
        try:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "选择模板",
                filter="Excel文件 (*.xlsx)",
                dir=self._start_directory(),
            )
            log_checkpoint("After file dialog closed", "select_templatepath")
            if path:
                self.rootpath = os.path.split(os.path.dirname(path))[0]
                self.lineEdit_template.setText(path)
                logger.info("已选择模板: %s", path)
                return path
        except Exception as exc:
            error_logger.log_error(
                "Failed to select template path",
                exc_info=exc,
                context="select_templatepath",
            )
            QMessageBox.critical(
                self, "错误", f"选择模板失败: {exc}\n详细信息已记录到 error.log"
            )
        return None

    def select_imgpath(self) -> None:
        """选择要插入报告的测试图片。"""
        log_checkpoint("Before opening image dialog", "select_imgpath")
        try:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "选择图片",
                filter="Image Files (*.png *.jpg *.jpeg *.bmp)",
                dir=QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.PicturesLocation
                ),
            )
            log_checkpoint("After image dialog closed", "select_imgpath")
            if path:
                self.lineEdit_img.setText(path)
                logger.info("已选择测试图片: %s", path)
        except Exception as exc:
            error_logger.log_error(
                "Failed to select image path", exc_info=exc, context="select_imgpath"
            )
            QMessageBox.critical(
                self, "错误", f"选择图片失败: {exc}\n详细信息已记录到 error.log"
            )

    # ---- 窗口管理 -------------------------------------------------------- #

    def closeEvent(self, event) -> None:
        """退出时先落盘输入内容，再关闭所有由主窗口打开的窗口。"""
        self.save_state()
        logger.info("程序退出，界面状态已保存: %s", self.app_state.path)
        for window in self.windows:
            window.close()
        super().closeEvent(event)

    def _focus_or_create(
        self, attr_name: str, factory: Callable[[], QWidget]
    ) -> QWidget:
        """已存在的窗口置前复用，否则创建并登记到关闭列表。"""
        window = getattr(self, attr_name, None)
        if window is None:
            window = factory()
            setattr(self, attr_name, window)
            self.windows.append(window)
            logger.debug("已创建窗口: %s", attr_name)
        window.show()
        window.activateWindow()
        return window

    def show_docx2pdf(self) -> None:
        self._focus_or_create(
            "docx2pdf_win", lambda: Docx2PdfWindow(rootpath=self.lineEdit_model.text())
        )

    def show_wordreplace(self) -> None:
        self._focus_or_create(
            "wordreplace_win", lambda: WordReplace(rootpath=self.rootpath)
        )

    def show_setting(self) -> None:
        self._focus_or_create("setting_win", self._build_setting_window)

    def _build_setting_window(self) -> QWidget:
        window = QWidget()
        window.setWindowTitle("设置")
        window.setWindowIcon(QIcon(":/emipdf/acbel -1.jpg"))
        window.resize(300, 300)
        window.setStyleSheet("QLabel { font-size: 15px; }")

        layout = QVBoxLayout()
        self.settings.clear()
        for item in SETTING_ITEMS:
            row = QHBoxLayout()
            label = QLabel(text=item.label, alignment=Qt.AlignRight | Qt.AlignVCenter)
            label.setToolTip(item.tooltip)
            row.addWidget(label)

            checkbox = QCheckBox()
            checkbox.setChecked(self.settings_value[item.key])
            row.addWidget(checkbox)
            self.settings[item.key] = checkbox

            layout.addLayout(row)

        buttons = QHBoxLayout()
        save_button = QPushButton(text="保存")
        save_button.clicked.connect(self.update_Setting)
        save_button.clicked.connect(window.close)
        buttons.addWidget(save_button)

        cancel_button = QPushButton(text="取消")
        cancel_button.clicked.connect(window.close)
        buttons.addWidget(cancel_button)

        layout.addLayout(buttons)
        window.setLayout(layout)
        return window

    def show_log(self) -> None:
        self._focus_or_create("log_win", self._build_log_window)
        self.update_log()

    def _build_log_window(self) -> QDialog:
        window = QDialog()
        window.setWindowTitle("日志")
        icon = QIcon()
        icon.addFile(":/emipdf/acbel -1.jpg", QSize(), QIcon.Normal, QIcon.Off)
        window.setWindowIcon(icon)
        window.resize(800, 600)
        window.setStyleSheet("QLabel { font-size: 15px; }")
        window.setLayout(QVBoxLayout())

        self.Text_log = QTextEdit(alignment=Qt.AlignLeft, readOnly=True)
        self.Text_log.setLineWrapMode(QTextEdit.WidgetWidth)
        window.layout().addWidget(self.Text_log)

        buttons = QHBoxLayout()
        update_button = QPushButton(text="更 新 日 志")
        update_button.clicked.connect(self.update_log)
        buttons.addWidget(update_button)

        clear_button = QPushButton(text="清 空 日 志")
        clear_button.clicked.connect(self.clear_log)
        buttons.addWidget(clear_button)

        export_button = QPushButton(text="导 出 日 志")
        export_button.clicked.connect(self.export_log)
        buttons.addWidget(export_button)

        window.layout().addLayout(buttons)
        return window

    def show_about(self) -> None:
        self._focus_or_create("about_win", self._build_about_window)

    def _build_about_window(self) -> QWidget:
        window = QWidget()
        window.setWindowTitle("关于")
        icon = QIcon()
        icon.addFile(":/emipdf/acbel -1.jpg", QSize(), QIcon.Normal, QIcon.Off)
        window.setWindowIcon(icon)
        window.resize(300, 200)
        window.setStyleSheet("QLabel { font-size: 15px; }")
        window.setLayout(QVBoxLayout())

        label = QLabel(
            text=(
                f"{APP_TITLE}\n\n版本：{APP_VERSION}\n\n"
                "作者：Lucas Li\n\n邮箱：Lucas_Li@acbel.com"
            ),
            alignment=Qt.AlignCenter,
        )
        label.setWordWrap(True)
        window.layout().addWidget(label)
        return window

    def show_helpdoc(self) -> None:
        self._focus_or_create("helpdoc_win", self._build_helpdoc_window)

    def _build_helpdoc_window(self) -> QWidget:
        window = QWidget()
        window.setWindowTitle("使用文档")
        icon = QIcon()
        icon.addFile(":/emipdf/acbel -1.jpg", QSize(), QIcon.Normal, QIcon.Off)
        window.setWindowIcon(icon)
        window.resize(820, 620)

        layout = QVBoxLayout(window)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(HELP_DOCUMENT)
        layout.addWidget(text)

        close_button = QPushButton("关闭")
        close_button.clicked.connect(window.close)
        layout.addWidget(close_button)
        return window

    def show_done(self, save_file: str | None) -> None:
        self._focus_or_create("done_win", lambda: self._build_done_window(save_file))

    def _build_done_window(self, save_file: str | None) -> QWidget:
        window = QWidget()
        window.setWindowTitle("完成!")
        window.setWindowIcon(QIcon(":/emipdf/acbel -1.jpg"))
        window.resize(600, 200)
        window.setLayout(QVBoxLayout())

        saved_label = QLabel(
            f'文件已保存为 "{os.path.abspath(save_file or "")}"', alignment=Qt.AlignLeft
        )
        window.layout().addWidget(saved_label)

        todo_label = QLabel(
            text=(
                "您还需要进行下列步骤以完成报告：\n"
                "\t1. 填入日期，测试者等表头信息，注意是MP还是MVT.\n"
                "\t2. 千万注意限值标准是否对应，默认Class B.\n"
                "\t3. 插入测试图片和压缩包.\n"
                "\t4. 整理表格，如果有多余项请按需求删除."
            ),
            alignment=Qt.AlignLeft,
        )
        todo_label.setWordWrap(True)
        window.layout().addWidget(todo_label)

        confirm_label = QLabel(
            "---------------请确认以上步骤都已完成，按OK退出。---------------",
            alignment=Qt.AlignLeft,
        )
        window.layout().addWidget(confirm_label)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(window.close)
        window.layout().addWidget(ok_button)
        return window

    # ---- 日志窗口 -------------------------------------------------------- #

    def update_Setting(self) -> None:
        for key, checkbox in self.settings.items():
            self.settings_value[key] = checkbox.isChecked()
        logger.info("设置已更新: %s", self.settings_value)
        self.save_state()

    def update_log(self) -> None:
        if self.Text_log is None:
            return
        if self.log_path is None:
            self.log_path = os.path.join(os.getcwd(), LOG_FILENAME)
        if not os.path.exists(self.log_path):
            open(self.log_path, "w", encoding="utf-8").close()
        with open(self.log_path, encoding="utf-8") as fp:
            self.Text_log.setText(fp.read())

    def export_log(self) -> None:
        export_path, _ = QFileDialog.getSaveFileName(
            self, "导出日志", filter="Log Files (*.log)"
        )
        if not export_path or self.log_path is None:
            logger.debug("导出日志已取消。")
            return
        with open(self.log_path, encoding="utf-8") as source:
            content = source.read()
        with open(export_path, "w", encoding="utf-8") as target:
            target.write(content)
        logger.info("日志已导出: %s", export_path)

    def clear_log(self) -> None:
        if self.log_path is None:
            return
        with open(self.log_path, "w", encoding="utf-8"):
            pass
        if self.Text_log is not None:
            self.Text_log.clear()
        logger.info("日志已清空。")

    # ---- 模板 ------------------------------------------------------------ #

    def open_template(self) -> Any | None:
        """打开报告模板并同步到界面；失败或取消时返回 None。"""
        template_file = self.lineEdit_template.text()
        load_qty = self.spin_qty.value()

        if not template_file:
            template_file = template_path_for(load_qty)
            if not os.path.exists(template_file):
                logger.warning(
                    "未找到 %s 个负载对应的模板(%s)，回落到 %s 个负载的模板。",
                    load_qty,
                    template_file,
                    DEFAULT_LOAD_QTY,
                )
                template_file = template_path_for(DEFAULT_LOAD_QTY)

        if not os.path.exists(template_file):
            logger.warning("未找到模板文件: %s", template_file)
            selected = self.select_templatepath()
            if not selected:
                return None
            template_file = selected

        # 记录最终使用的模板路径（main_func 依赖它推导输出文件名与负载数量）
        self.lineEdit_template.setText(os.path.abspath(template_file))

        try:
            return xl.load_workbook(template_file)
        except FileNotFoundError:
            logger.warning("未找到模板文件: %s", template_file)
            QMessageBox.warning(
                self, "Warning", f"No template file found: {template_file}"
            )
        except Exception as exc:
            logger.exception("打开模板文件失败: %s", exc)
            QMessageBox.warning(self, "Error", f"Error opening template file: {exc}")
        return None

    def template_load_qty(self, template_file: str) -> int:
        """模板文件名中的数量后缀优先（``_10.xlsx`` → 10），否则用界面上的负载数量。

        这样即使自动选模板时发生了回落，行数换算也与实际使用的模板一致。
        """
        match = re.search(TEMPLATE_COUNT_PATTERN, os.path.basename(template_file))
        if match:
            return int(match.group(1))
        return self.spin_qty.value()

    def get_testdetail(self) -> None:
        """从模板的测试细节单元格读取内容填入界面。"""
        workbook = self.open_template()
        if workbook is None:
            return
        sheet = workbook[REPORT_SHEET_NAME]
        detail = sheet[HEADER_CELL_DETAIL].value or ""
        self.text_detail.setText(detail)
        workbook.close()
        logger.info("已从模板读取测试细节: %d 字符", len(detail))

    def _load_anchors(self, setup_sheet) -> None:
        """用模板 Setup 表中的数值覆盖行列锚点。"""
        for attr_name, row in SETUP_ANCHOR_ROWS.items():
            value = setup_sheet.cell(row=row, column=SETUP_ANCHOR_COLUMN).value
            if value is not None:
                setattr(self, attr_name, value)

    # ---- 主流程 ---------------------------------------------------------- #

    def main_func(self, report_data: dict[str, dict[str, Any]]) -> None:
        """把解析结果写入模板并保存，随后按设置压缩、嵌入压缩包。"""
        started_at = time.perf_counter()
        model_dir = self.lineEdit_model.text()

        workbook = self.open_template()
        if workbook is None:
            return
        template_file = self.lineEdit_template.text()
        # 负载数量以模板文件名为准（如 _10 → 10），避免与模板行结构不符
        load_qty = self.template_load_qty(template_file)

        self._load_anchors(workbook[SETUP_SHEET_NAME])
        sheet = workbook[REPORT_SHEET_NAME]

        if not os.path.exists(model_dir):
            logger.warning("数据目录不存在: %s", model_dir)
            QMessageBox.warning(self, "Warning", f"No such directory: {model_dir}")
            return

        if not report_data:
            logger.warning("没有可写入的报告数据，已取消生成: %s", model_dir)
            QMessageBox.warning(
                self,
                "Warning",
                f"没有可写入的数据，请确认目录内有 EMI PDF 报告:\n{model_dir}",
            )
            return

        model_dir = os.path.realpath(model_dir)
        root_dir = os.path.dirname(model_dir)
        model_dir_name = os.path.basename(model_dir)
        os.chdir(root_dir)  # 后续相对路径（输出文件、zip）均基于该目录
        logger.info(
            "开始生成报告: 数据目录=%s, 模板=%s, 负载数量=%s, 报告数=%d, 设置=%s",
            model_dir,
            template_file,
            load_qty,
            len(report_data),
            self.settings_value,
        )

        uut_name = self._write_header(sheet, model_dir_name)
        self._insert_test_image(sheet)

        uut_count = len({name.split("-")[0] for name in report_data})
        if uut_count > MAX_UUT_COUNT:
            logger.warning(
                "负载类型过多: %s（模板最多支持 %d 种）", uut_count, MAX_UUT_COUNT
            )
            QMessageBox.warning(
                self, "Warning", f"Number of Load is too many! {uut_count}"
            )
            return

        self._resize_report_rows(sheet, load_qty, uut_count)
        self._write_measurements(sheet, report_data, load_qty)
        self._check_measurement_gaps(sheet, load_qty, uut_count, model_dir_name)

        save_file = re.sub(
            TEMPLATE_COUNT_PATTERN, f"_{uut_name}.xlsx", os.path.basename(template_file)
        )
        workbook.remove(workbook[SETUP_SHEET_NAME])
        workbook.save(save_file)
        self.save_file_name = save_file
        logger.info(
            "报告已保存: %s（写入 %d 份测量数据，用时 %.1f 秒）",
            os.path.abspath(save_file),
            len(report_data),
            time.perf_counter() - started_at,
        )

        if self.settings_value["NeedZip"]:
            try:
                self.zip_folder(model_dir_name, uut_name)
            except Exception as exc:
                logger.exception("Error during zipping or embedding: %s", exc)
                QMessageBox.critical(
                    self, "Error", f"Error during zipping or embedding: {exc}"
                )

    def _write_header(self, sheet, model_dir_name: str) -> str:
        """写入表头信息，返回单体型号名。"""
        parts = model_dir_name.split("-")
        uut_name = "-".join(parts[:2]) if len(parts) > 1 else model_dir_name
        test_date = self.date_test.date().toString("yyyy/MM/dd")
        workno = self.lineEdit_workerno.text()
        revision = self.lineEdit_rev.text()
        week = self.lineEdit_week.text()
        detail = self.text_detail.toPlainText()

        sheet[HEADER_CELL_MODEL] = uut_name
        sheet[HEADER_CELL_DATE] = test_date
        sheet[HEADER_CELL_WORKNO] = workno
        sheet[HEADER_CELL_REV] = revision
        sheet[HEADER_CELL_WEEK] = week
        sheet[HEADER_CELL_DETAIL] = detail

        logger.info(
            "表头写入: 型号=%s, 日期=%s, 工令=%s, 版本=%s, 周期=%s, 测试细节 %d 字符",
            uut_name,
            test_date,
            workno,
            revision,
            week,
            len(detail),
        )
        return uut_name

    def _insert_test_image(self, sheet) -> None:
        """把测试图片等比缩放后插入模板的指定位置。"""
        image_path = self.lineEdit_img.text()
        if not image_path:
            logger.info("未选择测试图片，跳过图片插入。")
            return
        if not os.path.exists(image_path):
            logger.warning("测试图片不存在，已跳过图片插入: %s", image_path)
            return

        try:
            with PImage.open(os.path.realpath(image_path)) as source:
                picture = (
                    source.convert("RGB") if source.mode in ("RGBA", "P") else source
                )
                ratio = IMAGE_HEIGHT_PIXELS / picture.height
                picture = picture.resize(
                    (int(picture.width * ratio), int(picture.height * ratio)),
                    PImage.Resampling.LANCZOS,
                )
                buffer = BytesIO()
                picture.save(
                    buffer, format="JPEG", quality=IMAGE_JPEG_QUALITY, optimize=True
                )
                buffer.seek(0)
                new_size = picture.size

            sheet.add_image(image.Image(buffer), IMAGE_ANCHOR_CELL)
            logger.info(
                "已插入测试图片: %s -> %s（缩放为 %dx%d）",
                image_path,
                IMAGE_ANCHOR_CELL,
                new_size[0],
                new_size[1],
            )
        except Exception:
            logger.exception("插入测试图片失败，已跳过: %s", image_path)

    def _resize_report_rows(self, sheet, load_qty: int, uut_count: int) -> None:
        """按实际机种数量删除模板中多余的机种区段。"""
        block_rows = load_qty * ROWS_PER_UUT_UNIT
        first_spare_row = self.row_sn_ + block_rows * uut_count

        for cell_range in list(sheet.merged_cells):
            if cell_range.min_row == first_spare_row:
                sheet.unmerge_cells(cell_range.coord)

        sheet.delete_rows(first_spare_row, block_rows * (MAX_UUT_COUNT - uut_count))
        self.row_end_ = sheet.max_row - REPORT_TAIL_ROWS
        logger.info(
            "报告行调整: 机种数=%d, 每机种行数=%d, 自第 %d 行起删除 %d 行, 数据结束行=%d",
            uut_count,
            block_rows,
            first_spare_row,
            block_rows * (MAX_UUT_COUNT - uut_count),
            self.row_end_,
        )

    def _write_measurements(
        self, sheet, report_data: dict[str, dict[str, Any]], load_qty: int
    ) -> None:
        """逐份报告定位到对应行并写入测量数据。"""
        for datas in report_data.values():
            row_sn = self.row_sn_
            while (
                sheet.cell(row=row_sn, column=self.col_sn_).value is not None
                and sheet.cell(row=row_sn, column=self.col_sn_).value != datas["Serial"]
            ):
                row_sn += load_qty * ROWS_PER_UUT_UNIT
            if sheet.cell(row=row_sn, column=self.col_sn_).value is None:
                sheet.cell(row=row_sn, column=self.col_sn_).value = datas["Serial"]

            row_vol = row_sn + (
                load_qty * ROWS_PER_LOAD_STEP
                if sheet.cell(row=row_sn, column=self.col_vol_).value
                != int(re.match(r"\d+", datas["Power"]).group())
                else 0
            )
            row_load = row_vol
            try:
                while row_load < row_vol + (load_qty * ROWS_PER_LOAD_STEP) and int(
                    sheet.cell(row=row_load, column=self.col_load_).value * 100
                ) != int(re.match(r"\d+", datas["Load"]).group()):
                    row_load += ROWS_PER_LOAD_STEP
            except Exception:
                message = self.tr("负载数量与模板不符！")
                logger.exception(message)
                QMessageBox.information(self, "错误", message)
                return

            measurement = datas["datas"][0]
            row_line = (
                row_load + 1
                if sheet.cell(row=row_load, column=self.col_line_).value
                != LINE_LABELS.get(measurement[PDF_LINE_COLUMN], "Unknown")
                else row_load
            )
            for offset, source_index in MEASUREMENT_CELL_SOURCES:
                value = (
                    EMPTY_MARK if source_index is None else measurement[source_index]
                )
                sheet.cell(row=row_line, column=self.col_load_ + offset).value = value

            logger.debug(
                "写入 %s: 序号行=%d, 电压行=%d, 负载行=%d, 数据行=%d",
                datas.get("Serial"),
                row_sn,
                row_vol,
                row_load,
                row_line,
            )

        logger.info("测量数据写入完成: 共 %d 份", len(report_data))

    # ---- 数据完整性检查 -------------------------------------------------- #

    def _collect_conditions(
        self, sheet, load_qty: int, uut_count: int
    ) -> list[tuple[tuple[int, int, int], tuple[Any, Any, Any], dict[str, int]]]:
        """按 (电压档, 负载档, 相线) 条件枚举各序列号对应的数据行。

        :return: ``[(条件键, (电压值, 负载值, 相线名), {序列号: 行号})]``
        """
        block_rows = load_qty * ROWS_PER_UUT_UNIT
        conditions: dict[tuple[int, int, int], dict[str, int]] = {}
        labels: dict[tuple[int, int, int], tuple[Any, Any, Any]] = {}

        for sn_index in range(uut_count):
            base_row = self.row_sn_ + sn_index * block_rows
            serial_value = sheet.cell(row=base_row, column=self.col_sn_).value
            serial = (
                str(serial_value) if serial_value else f"第 {sn_index + 1} 个序列号"
            )

            for vol_index in range(VOLTAGE_KINDS):
                vol_start = base_row + vol_index * load_qty * ROWS_PER_LOAD_STEP
                for load_index in range(load_qty):
                    load_row = vol_start + load_index * ROWS_PER_LOAD_STEP
                    for phase_offset in range(PHASE_KINDS):
                        row = load_row + phase_offset
                        key = (vol_index, load_index, phase_offset)
                        conditions.setdefault(key, {})[serial] = row
                        labels.setdefault(
                            key,
                            (
                                sheet.cell(row=vol_start, column=self.col_vol_).value,
                                sheet.cell(row=load_row, column=self.col_load_).value,
                                sheet.cell(row=row, column=self.col_line_).value,
                            ),
                        )

        return [(key, labels[key], conditions[key]) for key in conditions]

    def _row_state(self, sheet, row: int) -> str:
        """数据行的填写状态：``empty``（未写入）/ ``full``（写满）/ ``partial``（只写了一部分）。

        模板中固定填 ``-`` 的那一列不参与判断（它本来就预填了 ``-``）。
        """
        filled = 0
        expected = 0
        for offset, source_index in MEASUREMENT_CELL_SOURCES:
            if source_index is None:
                continue
            expected += 1
            if sheet.cell(row=row, column=self.col_load_ + offset).value is not None:
                filled += 1

        if filled == 0:
            return "empty"
        if filled == expected:
            return "full"
        return "partial"

    @staticmethod
    def _condition_text(voltage: Any, load: Any, phase: Any) -> str:
        """把条件值格式化成便于阅读的文本，如 ``220V / 50% / Neutral``。"""
        parts = []
        if voltage is not None:
            parts.append(f"{int(float(voltage))}V")
        if load is not None:
            parts.append(f"{int(round(float(load) * 100))}%")
        if phase is not None:
            parts.append(str(phase))
        return " / ".join(parts) or "（未知条件）"

    @staticmethod
    def _format_notice(items: list[str]) -> str:
        """拼提示文本，最多列 MAX_NOTICE_ITEMS 条。"""
        shown = items[:MAX_NOTICE_ITEMS]
        text = "\n".join(f"· {item}" for item in shown)
        if len(items) > len(shown):
            text += f"\n……等共 {len(items)} 项"
        return text

    @staticmethod
    def _expected_report_tokens(
        voltage: Any, load: Any, phase: Any
    ) -> tuple[str, str, str]:
        """把模板中的电压 / 负载 / 相线值换算成报告文件名里的片段。"""
        voltage_token = f"{int(float(voltage))}V" if voltage is not None else ""
        load_token = f"{int(round(float(load) * 100))}%" if load is not None else ""
        phase_token = PHASE_FILE_TOKENS.get(str(phase), str(phase))
        return voltage_token, load_token, phase_token

    def _diagnose_missing_report(
        self, model_dir: str, serial: str, voltage: Any, load: Any, phase: Any
    ) -> str:
        """缺失条件时，检查数据目录里对应报告文件的情况。"""
        if not os.path.isdir(model_dir):
            return f"数据目录不存在（{model_dir}）"
        try:
            names = os.listdir(model_dir)
        except OSError as exc:
            return f"无法读取数据目录（{exc}）"

        pdfs = [name for name in names if name.lower().endswith(REPORT_FILE_SUFFIX)]
        serial_pdfs = [name for name in pdfs if name.startswith(f"{serial}-")]
        if not serial_pdfs:
            return "数据目录里没有以该序列号开头的报告文件"

        voltage_token, load_token, phase_token = self._expected_report_tokens(
            voltage, load, phase
        )
        matched = [
            name
            for name in serial_pdfs
            if voltage_token in name and load_token in name and phase_token in name
        ]
        if matched:
            return f"报告文件存在（{matched[0]}）但未能取到数据，可能是内容解析失败"
        return (
            f"缺少对应报告文件（该序列号已有 {len(serial_pdfs)} 份报告，"
            f"未找到含 {voltage_token}/{load_token}/{phase_token} 的文件）"
        )

    def _cleanup_orphan_merges(self, sheet) -> None:
        """清理落在表格之外的残留合并区域（删行后模板可能遗留）。"""
        limit = self.row_end_ + REPORT_TAIL_ROWS
        orphans = [rng.coord for rng in sheet.merged_cells if rng.min_row > limit]
        for coord in orphans:
            try:
                sheet.unmerge_cells(coord)
            except KeyError:
                # 该区域的单元格已随删行消失，合并记录已移除即可
                logger.debug("跳过已失效的合并区域: %s", coord)

    def _check_measurement_gaps(
        self, sheet, load_qty: int, uut_count: int, model_dir: str
    ) -> None:
        """检查数据填入区域的空条件。

        - 某个 (电压, 负载, 相线) 条件在所有序列号中都没有数据：视为未安排该测试的正常情况，
          删除这些空行并简要提示；
        - 只有部分序列号缺数据、或某行只写了一部分列：视为异常，检查数据目录中对应的
          报告文件情况并告警。
        """
        conditions = self._collect_conditions(sheet, load_qty, uut_count)
        removable_rows: list[int] = []
        normal_conditions: list[str] = []
        abnormal_items: list[str] = []

        for _key, (voltage, load, phase), rows_by_serial in conditions:
            states = {
                serial: self._row_state(sheet, row)
                for serial, row in rows_by_serial.items()
            }
            condition_text = self._condition_text(voltage, load, phase)
            empty_serials = [s for s, state in states.items() if state == "empty"]
            partial_serials = [s for s, state in states.items() if state == "partial"]

            if partial_serials:
                abnormal_items.append(
                    f"{condition_text}：{', '.join(partial_serials)} 的数据不完整"
                )
            elif not empty_serials:
                continue
            elif len(empty_serials) == len(states):
                normal_conditions.append(condition_text)
                removable_rows.extend(rows_by_serial.values())
            else:
                for serial in empty_serials:
                    reason = self._diagnose_missing_report(
                        model_dir, serial, voltage, load, phase
                    )
                    abnormal_items.append(
                        f"{condition_text}：{serial} 缺少数据（{reason}）"
                    )

        if normal_conditions:
            logger.info(
                "以下条件在所有序列号中都没有数据，视为未测试并删除对应行: %s",
                normal_conditions,
            )
        for item in abnormal_items:
            logger.warning("数据缺失: %s", item)

        if removable_rows:
            for row in sorted(removable_rows, reverse=True):
                sheet.delete_rows(row, 1)
            self.row_end_ = sheet.max_row - REPORT_TAIL_ROWS
            self._cleanup_orphan_merges(sheet)
            logger.info(
                "已删除 %d 个空条件行，数据结束行更新为 %s",
                len(removable_rows),
                self.row_end_,
            )

        if normal_conditions:
            QMessageBox.information(
                self,
                self.tr("提示"),
                "以下条件在所有序列号中都没有数据（视为未测试），已删除对应行：\n"
                + self._format_notice(normal_conditions),
            )
        if abnormal_items:
            QMessageBox.warning(
                self,
                self.tr("数据缺失警告"),
                "以下条件的数据不完整，请检查对应报告：\n"
                + self._format_notice(abnormal_items),
            )

    # ---- PDF 解析调度 ---------------------------------------------------- #

    def getpdfdatas(self) -> None:
        """启动 PDF 解析线程，并在状态栏显示进度。"""
        if self.getpdf_running:
            logger.warning("PDF 解析正在进行，忽略重复启动。")
            return

        directory = self.lineEdit_model.text()
        if not os.path.isdir(directory):
            logger.warning("数据目录不存在，无法开始处理: %s", directory)
            QMessageBox.warning(self, "Warning", f"数据目录不存在: {directory}")
            return

        source_files = [name for name in os.listdir(directory) if name.endswith(".pdf")]
        if not source_files:
            logger.warning("目录内没有 PDF 文件: %s", directory)
            QMessageBox.warning(self, "Warning", f"目录内没有 PDF 文件: {directory}")
            return

        self.getpdf_running = True
        self.file_count = len(source_files)
        logger.info("开始处理: 目录=%s, PDF 数量=%d", directory, self.file_count)

        self.statusBar().showMessage("正在处理文件...")
        self.progressBar = QProgressBar(self.statusBar_main)
        self.progressBar.setMaximumHeight(15)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(self.file_count)
        self.progressBar.setValue(0)
        self.statusBar().addPermanentWidget(self.progressBar)

        self.process_thread = ProcessPdfThread(directory)
        self.process_thread.progress_updated.connect(self.updateProgressBar)
        self.process_thread.processing_finished.connect(self.onProcessingFinished)
        self.process_thread.processing_error.connect(self.onProcessingError)
        self.process_thread.start()

    def onProcessingFinished(self, result: dict[str, dict[str, Any]]) -> None:
        self.report_data = result
        self._remove_progress_bar()
        logger.info("解析结果已就绪: %d 份报告", len(result))
        self.main_func(self.report_data)
        self.getpdf_running = False

    def onProcessingError(self, error_msg: str) -> None:
        logger.exception("PDF 解析出错: %s", error_msg)
        QMessageBox.critical(self, "Error", f"Pdf Processing error: {error_msg}")
        self._remove_progress_bar()
        self.getpdf_running = False

    def updateProgressBar(self) -> None:
        if self.progressBar is None:
            return
        value = self.progressBar.value() + 1
        self.progressBar.setValue(value)
        self.statusBar().showMessage(f"正在处理文件...{value}/{self.file_count}")

    def _remove_progress_bar(self) -> None:
        if self.progressBar is not None:
            self.statusBar().removeWidget(self.progressBar)
            self.progressBar = None

    # ---- 压缩与嵌入 ------------------------------------------------------ #

    def zip_folder(self, directory: str, zipname: str) -> None:
        """启动压缩线程，并在状态栏显示进度。"""
        file_count = sum(
            1
            for _root, _dirs, files in os.walk(directory)
            for name in files
            if name.endswith(".pdf")
        )
        logger.info(
            "开始压缩: 目录=%s, 文件数=%d, 输出=%s.zip", directory, file_count, zipname
        )
        self.zip_progressBar = QProgressBar(self.statusBar_main)
        self.zip_progressBar.setMaximumHeight(15)
        self.zip_progressBar.setMaximum(file_count)
        self.zip_progressBar.setMinimum(0)
        self.zip_progressBar.setValue(0)

        self.statusBar().showMessage("正在压缩文件...")
        self.statusBar().addPermanentWidget(self.zip_progressBar)

        self.zip_thread = ZipThread(directory, zipname)
        self.zip_thread.progress_updated.connect(self.updateZipProgressBar)
        self.zip_thread.zip_finished.connect(self.onZipFinished)
        self.zip_thread.zip_error.connect(self.onZipError)
        self.zip_thread.start()

    def updateZipProgressBar(self, value: int) -> None:
        if self.zip_progressBar is None:
            return
        self.zip_progressBar.setValue(value)
        self.statusBar().showMessage(
            f"正在压缩文件...{value}/{self.zip_progressBar.maximum()}"
        )

    def onZipFinished(self, zipname: str) -> None:
        if self.zip_progressBar is not None:
            self.statusBar().removeWidget(self.zip_progressBar)
            self.zip_progressBar = None
            self.statusBar().showMessage("压缩完成！")

        if self.save_file_name and self.settings_value["AddZip"]:
            self.add_zip_to_excel(zipname, self.save_file_name)

        logger.info("压缩流程结束: %s", zipname)
        self.show_done(self.save_file_name)

    def onZipError(self, error_msg: str) -> None:
        logger.error("压缩出错: %s", error_msg)
        if self.zip_progressBar is not None:
            self.statusBar().removeWidget(self.zip_progressBar)
            self.zip_progressBar = None
        QMessageBox.critical(self, "Error", f"Error zipping folder: {error_msg}")

    def open_excel(self):
        """取得 Excel COM 对象；创建失败时询问用户是否重试（放弃则返回 None）。"""
        while True:
            try:
                excel = win32.Dispatch("Excel.Application")
            except Exception:
                logger.exception(
                    "无法启动 Excel，请确认已安装 Microsoft Excel 2010 或更高版本。"
                )
                reply = QMessageBox.information(
                    self,
                    self.tr("Excel打开失败"),
                    self.tr("请安装 Microsoft Excel 2010或更新的版本。是否重试？"),
                    QMessageBox.StandardButton.Yes,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.No:
                    logger.warning("用户放弃启动 Excel，跳过压缩包嵌入。")
                    return None
                continue
            excel.Visible = True
            logger.debug("Excel 已启动。")
            return excel

    def add_zip_to_excel(self, zipname: str, save_file: str) -> None:
        """把压缩包作为 OLE 对象嵌入报告的最后一页并补齐边框。"""
        excel = self.open_excel()
        if excel is None:
            return
        logger.info("开始嵌入压缩包: %s.zip -> %s", zipname, save_file)
        try:
            workbook = excel.Workbooks.Open(os.path.abspath(save_file))
            sheet = workbook.Worksheets(REPORT_SHEET_NAME)
            if sheet.ProtectContents:
                logger.info("工作表处于保护状态，已取消保护: %s", REPORT_SHEET_NAME)
                sheet.Unprotect()

            sheet.Cells(self.row_sn_, self.col_end_ - 2).Select()
            sheet.OLEObjects().Add(
                ClassType=None,
                Filename=os.path.abspath(f"{zipname}.zip"),
                Link=False,
                DisplayAsIcon=True,
            )

            # xlEdgeBottom = 9; xlMedium = -4138; xlContinuous = 1
            border_range = sheet.Range(
                sheet.Cells(self.row_end_, 2),
                sheet.Cells(self.row_end_, self.col_end_ - 1),
            )
            border_range.Select()
            border_range.Borders(9).LineStyle = 1
            border_range.Borders(9).Weight = -4138

            workbook.Save()
            logger.info("压缩包已嵌入并保存: %s", os.path.abspath(save_file))
            if self.settings_value["CloseExcel"]:
                excel.Quit()
                logger.info("已按设置关闭 Excel。")
        except Exception as exc:
            logger.exception("嵌入压缩包到 Excel 失败: %s", exc)
            QMessageBox.critical(self, "Error", f"Error adding zip to Excel: {exc}")


if __name__ == "__main__":
    app = QApplication()
    # 组织名 / 应用名决定界面状态文件的存放位置（用户配置目录）
    app.setOrganizationName("Acbel")
    app.setApplicationName("EMI-Report")

    logger.info(
        "EMI-Report 启动: Python %s, PySide6 %s, 工作目录=%s, 日志文件=%s",
        sys.version.split()[0],
        pyside_version,
        os.getcwd(),
        os.path.join(os.getcwd(), LOG_FILENAME),
    )

    win = EMIWindow()

    # 主题已改用 Qt 默认样式：apply_stylesheet(app, theme="dark_teal.xml")
    win.show()
    sys.exit(app.exec())

    # win.add_zip_to_excel("FSC048-4C0G", "2.1 Conducted EMI Measurement.xlsx")
