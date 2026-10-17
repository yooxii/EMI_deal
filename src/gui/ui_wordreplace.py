"""Word 替换子窗口。

两个用途：
1. 在 docx 的 ``word/document.xml`` 文本层做字符串替换（不经过 Word，速度快）；
2. 按「原字符串集 -> 目标字符串集」批量重命名文件，并可对文档中的测量数值做
   小幅随机抖动，用于批量生成差异化的测试数据。
"""

from __future__ import annotations

import logging
import os
import random
import re
import sys
import tempfile
import time
import zipfile
from typing import Sequence

from PySide6.QtCore import QSize, QStandardPaths, Qt, QThread, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.widgets import ClickableLabel
from naming import collect_name_tokens

logger = logging.getLogger(__name__)

DOCUMENT_XML = os.path.join("word", "document.xml")
TEXT_EDIT_HEIGHT = 60
INTERRUPT_WAIT_MS = 5000
NUMBER_PATTERN = r"(?<=\>)\d+\.\d+(?=\<)"
RANDOM_SLOT_MODULUS = 8  # 每 8 个数值为一组
RANDOM_SLOT_OFFSETS = (1, 4)  # 组内参与抖动的下标
JITTER_DIVISOR = 2000  # 抖动幅度的分母
DOCX_SUFFIX = ".docx"
CONTROL_CHARS_PATTERN = re.compile(r"[\r\n\t\f\v]+")


def normalize_control_chars(text: str) -> str:
    """把格式控制符（``\\r``、``\\n``、``\\t`` 等）折叠为单个换行。

    连续多个控制符也只产生一个换行，并去掉每行首尾空白与空行。
    """
    folded = CONTROL_CHARS_PATTERN.sub("\n", text)
    lines = [line.strip() for line in folded.split("\n")]
    return "\n".join(line for line in lines if line)


def replace_text_in_docx(
    input_path: str,
    output_path: str,
    old_str: str | Sequence[str] | None,
    new_str: str | Sequence[str] | None,
    jitter: bool = True,
) -> None:
    """在 docx 的 XML 文本层做替换，并另存为新文件。

    :param old_str: 待替换的字符串；也可以是等长的字符串列表
    :param new_str: 替换后的字符串；与 ``old_str`` 形式对应
    :param jitter: 是否对测量数值做小幅随机抖动（默认开启，用于造差异化数据）；
        只做纯文本替换（例如换序列号）时传 ``False``，测量值保持与源文档一致
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        with zipfile.ZipFile(input_path, "r") as docx_zip:
            docx_zip.extractall(tmp_dir)

        document_xml_path = os.path.join(tmp_dir, DOCUMENT_XML)
        if not os.path.exists(document_xml_path):
            raise FileNotFoundError(f"{DOCUMENT_XML} not found in the DOCX file.")

        with open(document_xml_path, encoding="utf-8") as fp:
            content = fp.read()

        if isinstance(old_str, str):
            content = content.replace(old_str, new_str)
        elif old_str is not None:
            for source, target in zip(old_str, new_str or ()):
                if source is None:
                    continue
                content = content.replace(source, target)
        if jitter:
            content = replace_value(content)

        with open(document_xml_path, "w", encoding="utf-8") as fp:
            fp.write(content)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as new_docx:
            for root, _dirs, files in os.walk(tmp_dir):
                for name in files:
                    file_path = os.path.join(root, name)
                    new_docx.write(
                        file_path, arcname=os.path.relpath(file_path, tmp_dir)
                    )

    logger.info("已生成新文件: %s", output_path)


def replace_value(content: str) -> str:
    """对文档 XML 中的浮点数值按组做小幅随机抖动（用于造差异化的测试数据）。"""
    random.seed(time.time())

    values = [float(value) for value in re.findall(NUMBER_PATTERN, content)]
    for index, value in enumerate(values):
        if index % RANDOM_SLOT_MODULUS not in RANDOM_SLOT_OFFSETS:
            continue
        # 每组需要用到后面两个数值，末尾不完整的组直接跳过（原实现会在此处抛 IndexError）
        if index + 2 >= len(values):
            logger.warning("数值组不完整，跳过抖动: %s", value)
            continue

        # 抖动幅度取与下一个数值差值的一小部分
        bound = int((values[index + 1] - value) * 100)
        try:
            new_value = value + random.randrange(-bound, bound) / JITTER_DIVISOR
        except Exception:
            logger.warning("无法随机的值: %s", value)
            new_value = value

        paired_value = values[index + 1] - new_value
        content = content.replace(str(value), str(round(new_value, 2)))
        content = content.replace(str(values[index + 2]), str(round(paired_value, 2)))

    return content


class WordReplaceThread(QThread):
    """按字符串集批量重命名并替换 docx 内容。"""

    file_count = Signal(int)  # 待处理文件总数
    file_progress = Signal(int)  # 已处理文件数
    replace_finished = Signal()  # 全部结束
    replace_error = Signal(str)  # 错误信息

    def __init__(
        self,
        path_src: str,
        path_tgt: str,
        args_srcs: str,
        args_tgts: str,
        args_src: str | None = None,
        args_tgt: str | None = None,
    ) -> None:
        super().__init__()
        self.path_src = path_src
        self.path_tgt = path_tgt
        self.args_srcStrings = args_srcs
        self.args_tgtStrings = args_tgts
        self.args_srcString = args_src
        self.args_tgtString = args_tgt

    @staticmethod
    def _split_strings(raw: str) -> list[str]:
        """按逗号或空白把字符串集拆成列表。"""
        return raw.split("," if "," in raw else None)

    def run(self) -> None:
        if "" in [
            self.path_src,
            self.path_tgt,
            self.args_srcStrings,
            self.args_tgtStrings,
        ]:
            error = self.tr("请补充完整信息")
            logger.warning("%s", error)
            self.replace_error.emit(error)
            return

        path_src = os.path.abspath(self.path_src)
        path_tgt = os.path.abspath(self.path_tgt)

        source_strings = self._split_strings(self.args_srcStrings)
        target_strings = self._split_strings(self.args_tgtStrings)
        if len(source_strings) != len(target_strings):
            error = self.tr("源字符串集和目标字符串集数量不一致")
            logger.warning("%s", error)
            self.replace_error.emit(error)
            return

        if os.path.isdir(path_src):
            source_files = [
                name for name in os.listdir(path_src) if name.endswith(".docx")
            ]
        else:
            source_files = [path_src]

        if not os.path.exists(path_tgt):
            os.makedirs(path_tgt)
            logger.info("已创建目标目录: %s", path_tgt)

        total_files = len(source_files)
        logger.info(
            "开始替换: 源=%s, 目标=%s, docx 数量=%d, 替换组数=%d",
            path_src,
            path_tgt,
            total_files,
            len(source_strings),
        )
        if not source_files:
            logger.warning("源路径下没有 docx 文件: %s", path_src)

        self.file_count.emit(total_files)
        current = 0
        failed = 0
        self.file_progress.emit(current)

        for source_text, target_text in zip(source_strings, target_strings):
            handled_files = []
            for source_file in source_files:
                if self.isInterruptionRequested():
                    logger.info("替换被中断，已完成 %d 个文件。", current)
                    self.replace_finished.emit()
                    return
                if source_text not in source_file:
                    continue
                src_path = os.path.join(path_src, source_file)
                tgt_path = os.path.join(
                    path_tgt, source_file.replace(source_text, target_text)
                )
                try:
                    replace_text_in_docx(
                        src_path,
                        tgt_path,
                        [source_text, self.args_srcString],
                        [target_text, self.args_tgtString],
                    )
                    logger.debug("已替换: %s -> %s", src_path, tgt_path)
                except Exception as exc:
                    logger.exception("替换失败 %s: %s", source_file, exc)
                    failed += 1
                    current -= 1
                handled_files.append(source_file)
                current += 1
                self.file_progress.emit(current)

            for handled_file in handled_files:
                source_files.remove(handled_file)

        logger.info(
            "替换完成: 成功 %d / 共 %d（失败 %d）", current, total_files, failed
        )
        self.replace_finished.emit()


class WordReplace(QMainWindow):
    """Word 替换窗口：路径与字符串集输入、进度显示、中止。"""

    def __init__(
        self, parent: QWidget | None = None, rootpath: str | None = None
    ) -> None:
        super().__init__(parent)
        self.path = ""
        self.file_count = 0
        self.curr = 0
        self.pgBar: QProgressBar | None = None
        self.wordreplace_thread: WordReplaceThread | None = None

        self.setupUi()
        self.rootpath = (
            rootpath
            if rootpath and os.path.exists(rootpath)
            else QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.DocumentsLocation
            )
        )

        self.btn_srcpath.clicked.connect(self.select_srcdocx_path)
        self.btn_srcfile.clicked.connect(self.select_srcdocx_file)
        self.btn_tgtpath.clicked.connect(self.select_tgtpath)
        self.btn_start.clicked.connect(self.start_replace)
        self.btn_stop.clicked.connect(self.stop_replace)
        self.btn_close.clicked.connect(self.close)

        logger.info("Word 替换窗口初始化完成，rootpath=%s", self.rootpath)

    # ---- 界面 ------------------------------------------------------------ #

    def setupUi(self) -> None:
        self.setWindowTitle(self.tr("Word替换"))
        self.resize(600, 350)
        icon = QIcon()
        icon.addFile(":/emipdf/acbel -1.jpg", QSize(), QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)

        main_widget = QWidget()
        main_widget.setObjectName("mainWidget")
        self.setCentralWidget(main_widget)

        outer_layout = QHBoxLayout()
        main_layout = QVBoxLayout()
        main_widget.setLayout(outer_layout)

        spacer = QSpacerItem(
            20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        vertical_spacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        outer_layout.addItem(spacer)
        outer_layout.addLayout(main_layout)
        outer_layout.addItem(spacer)

        main_layout.addItem(vertical_spacer)
        input_layout = QVBoxLayout()
        main_layout.addLayout(input_layout)
        main_layout.addItem(vertical_spacer)

        self._build_path_layout(input_layout)
        self._build_args_layout(input_layout)
        self._build_buttons(input_layout)

        self.statusBar_docx = QStatusBar()
        self.setStatusBar(self.statusBar_docx)

    def _build_path_layout(self, input_layout: QVBoxLayout) -> None:
        """源路径与目标路径两行。"""
        source_row = QHBoxLayout()
        source_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        source_label = QLabel(self.tr("原来路径:"))
        source_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        source_row.addWidget(source_label)

        self.lineEdit_srcpath = QLineEdit()
        source_row.addWidget(self.lineEdit_srcpath)

        self.btn_srcpath = QPushButton(self.tr("目录"))
        self.btn_srcpath.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_srcpath.setFixedWidth(40)
        source_row.addWidget(self.btn_srcpath)

        self.btn_srcfile = QPushButton(self.tr("文件"))
        self.btn_srcfile.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_srcfile.setFixedWidth(40)
        source_row.addWidget(self.btn_srcfile)
        input_layout.addLayout(source_row)

        target_row = QHBoxLayout()
        target_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        target_label = QLabel(self.tr("目标路径:"))
        target_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        target_row.addWidget(target_label)

        self.lineEdit_tgtpath = QLineEdit()
        target_row.addWidget(self.lineEdit_tgtpath)

        self.btn_tgtpath = QPushButton(self.tr("目录"))
        self.btn_tgtpath.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tgtpath.setFixedWidth(86)
        target_row.addWidget(self.btn_tgtpath)
        input_layout.addLayout(target_row)

    def _build_args_layout(self, input_layout: QVBoxLayout) -> None:
        """左右两栏：原字符串集 + 原字符串 / 目标字符串集 + 目标字符串。

        点击「原字符串集」标签可从源路径的文件名中提取内容；
        点击「目标字符串集」标签可把输入框里的格式控制符整理为单个换行。
        """
        args_layout = QGridLayout()
        input_layout.addLayout(args_layout)

        self.label_srcStrings = ClickableLabel(self.tr("原字符串集:"))
        self.label_srcStrings.setToolTip(
            self.tr(
                "点击标签：从源文件夹/源文件的文件名中提取（按「-」取第一段并去重）"
            )
        )
        self.label_srcStrings.clicked.connect(self.fill_source_strings)
        self.text_srcStrings = QTextEdit()
        self.lineEdit_srcString = QLineEdit()
        args_layout.addLayout(
            self._build_string_column(
                self.label_srcStrings,
                self.tr("原字符串:"),
                self.text_srcStrings,
                self.lineEdit_srcString,
            ),
            0,
            0,
        )

        self.label_tgtStrings = ClickableLabel(self.tr("目标字符串集:"))
        self.label_tgtStrings.setToolTip(
            self.tr("点击标签：把输入框中的 \\n、\\t、\\r 等格式控制符整理为单个换行")
        )
        self.label_tgtStrings.clicked.connect(self.clean_target_strings)
        self.text_tgtStrings = QTextEdit()
        self.lineEdit_tgtString = QLineEdit()
        args_layout.addLayout(
            self._build_string_column(
                self.label_tgtStrings,
                self.tr("目标字符串:"),
                self.text_tgtStrings,
                self.lineEdit_tgtString,
            ),
            0,
            1,
        )

    @staticmethod
    def _build_string_column(
        label_set: QLabel,
        item_label: str,
        text_edit: QTextEdit,
        line_edit: QLineEdit,
    ) -> QVBoxLayout:
        column = QVBoxLayout()

        label_set.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        column.addWidget(label_set)

        text_edit.setFixedHeight(TEXT_EDIT_HEIGHT)
        text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        column.addWidget(text_edit)

        label_item = QLabel(item_label)
        label_item.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        column.addWidget(label_item)

        column.addWidget(line_edit)
        return column

    def _build_buttons(self, input_layout: QVBoxLayout) -> None:
        buttons = QHBoxLayout()
        buttons.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_start = QPushButton(self.tr("开始"))
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        buttons.addWidget(self.btn_start)
        buttons.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Fixed))

        self.btn_stop = QPushButton(self.tr("中止"))
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        buttons.addWidget(self.btn_stop)
        buttons.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Fixed))

        self.btn_close = QPushButton(self.tr("关闭"))
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        buttons.addWidget(self.btn_close)

        input_layout.addLayout(buttons)

    # ---- 路径选择 -------------------------------------------------------- #

    def select_srcdocx_path(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, self.tr("选择DOCX文件所在目录"), dir=self.rootpath
        )
        if path:
            self.rootpath = os.path.dirname(path)
            self.lineEdit_srcpath.setText(path)
            self.path = path
            logger.info("已选择源目录: %s", path)

    def select_srcdocx_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("选择DOCX文件"),
            filter="DOCX文件 (*.docx)",
            dir=self.rootpath,
        )
        if path:
            self.rootpath = os.path.dirname(os.path.dirname(path))
            self.lineEdit_srcpath.setText(path)
            self.path = path
            logger.info("已选择源文件: %s", path)

    def select_tgtpath(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, self.tr("选择保存位置"), dir=self.rootpath
        )
        if path:
            self.rootpath = os.path.dirname(path)
            self.lineEdit_tgtpath.setText(path)
            self.path = path
            logger.info("已选择目标目录: %s", path)

    # ---- 字符串集辅助操作 ------------------------------------------------ #

    def fill_source_strings(self) -> None:
        """点击「原字符串集」标签：从源路径的文件名中提取首段并去重填入。

        源路径是文件夹时，遍历其中所有 docx 文件名；同一首段只保留一次。
        """
        source = self.lineEdit_srcpath.text().strip()
        if not source:
            logger.warning("未选择源路径，无法提取原字符串集。")
            QMessageBox.information(
                self, self.tr("提示"), self.tr("请先选择源文件夹或源文件。")
            )
            return

        tokens = collect_name_tokens(source, DOCX_SUFFIX)
        if not tokens:
            logger.warning("未能从源路径提取到名称: %s", source)
            QMessageBox.information(
                self,
                self.tr("提示"),
                self.tr("未能从源路径提取到 docx 文件名，请确认路径是否正确。"),
            )
            return

        self.text_srcStrings.setPlainText("\n".join(tokens))
        logger.info("已从源路径提取 %d 个原字符串: %s", len(tokens), tokens)

    def clean_target_strings(self) -> None:
        """点击「目标字符串集」标签：把输入框中的格式控制符整理为单个换行。"""
        original = self.text_tgtStrings.toPlainText()
        cleaned = normalize_control_chars(original)
        if cleaned == original:
            logger.info("目标字符串集无需整理。")
            return
        self.text_tgtStrings.setPlainText(cleaned)
        logger.info("目标字符串集已整理: %d -> %d 字符", len(original), len(cleaned))

    # ---- 替换流程 -------------------------------------------------------- #

    def start_replace(self) -> None:
        """按界面当前输入启动替换线程。"""
        if self.wordreplace_thread is not None and self.wordreplace_thread.isRunning():
            logger.warning("Word 替换正在进行，忽略重复启动。")
            return

        source_dir = self.lineEdit_srcpath.text()
        target_dir = self.lineEdit_tgtpath.text()
        logger.info(
            "启动替换: 源=%s, 目标=%s, 原字符串集=%d 字符, 目标字符串集=%d 字符",
            source_dir,
            target_dir,
            len(self.text_srcStrings.toPlainText()),
            len(self.text_tgtStrings.toPlainText()),
        )
        self.wordreplace_thread = WordReplaceThread(
            source_dir,
            target_dir,
            self.text_srcStrings.toPlainText(),
            self.text_tgtStrings.toPlainText(),
            self.lineEdit_srcString.text(),
            self.lineEdit_tgtString.text(),
        )
        self.wordreplace_thread.file_count.connect(self.create_status_bar)
        self.wordreplace_thread.file_progress.connect(self.update_status_bar)
        self.wordreplace_thread.replace_finished.connect(self.end_status)
        self.wordreplace_thread.replace_error.connect(self.error_status)
        self.wordreplace_thread.start()

    def stop_replace(self) -> None:
        """请求线程在当前文件处理完后停止，并清理进度条。"""
        thread = self.wordreplace_thread
        if thread is not None and thread.isRunning():
            thread.requestInterruption()
            logger.info("wordreplace 已请求中止")
        self._remove_progress_bar()
        self.wordreplace_thread = None

    def _remove_progress_bar(self) -> None:
        if self.pgBar is not None:
            self.statusBar_docx.removeWidget(self.pgBar)
            self.pgBar = None

    @Slot(int)
    def create_status_bar(self, file_count: int) -> None:
        self.curr = 0
        self.file_count = file_count
        self.statusBar_docx.showMessage(self.tr("正在替换DOCX文件..."))
        self.pgBar = QProgressBar(self.statusBar_docx)
        self.pgBar.setMinimum(0)
        self.pgBar.setMaximum(file_count)
        self.pgBar.setValue(0)
        self.statusBar_docx.addPermanentWidget(self.pgBar)

    @Slot(int)
    def update_status_bar(self, value: int) -> None:
        self.curr = value
        if self.pgBar is not None:
            self.pgBar.setValue(value)
        self.statusBar_docx.showMessage(
            self.tr("正在替换DOCX文件...") + f"{value}/{self.file_count}"
        )

    @Slot()
    def end_status(self) -> None:
        self._remove_progress_bar()
        self.statusBar_docx.showMessage(
            self.tr("替换DOCX文件结束(成功/总数):") + f"{self.curr}/{self.file_count}"
        )
        logger.info("替换流程结束: 成功 %s / 共 %s", self.curr, self.file_count)
        self.wordreplace_thread = None

    @Slot(str)
    def error_status(self, err: str) -> None:
        QMessageBox.critical(self, self.tr("错误"), err)
        self.end_status()

    def closeEvent(self, event) -> None:
        """关闭窗口时请求中断而非强杀线程，避免文件写入被截断。"""
        thread = self.wordreplace_thread
        if thread is not None and thread.isRunning():
            thread.requestInterruption()
            thread.wait(INTERRUPT_WAIT_MS)
        super().closeEvent(event)


def test() -> None:
    """本地调试用：对单个文件做一次替换。"""
    ipath = "D:/Desktop_Li/WorkDir/EMC/WorkDir/12/FSL023-EL1G/8SSP50H29728A1DB59S1030-220V-100%-N.docx"
    opath = "D:/Desktop_Li/WorkDir/EMC/WorkDir/FSL023-EL1G/8SSP50H29728A1DB5C110E1-220V-100%-N.docx"
    replace_text_in_docx(
        ipath, opath, "8SSP50H29728A1DB59S1030", "8SSP50H29728A1DB5C110E1"
    )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = WordReplace()
    win.show()
    sys.exit(app.exec())
    # test()
