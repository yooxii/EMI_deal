"""DOCX 转 PDF 子窗口。

通过 Word COM 接口把 .docx 另存为 .pdf；转换在 :class:`ConvertThread` 中执行，
界面线程只负责展示进度与错误提示（窗口一律不在子线程中创建）。
"""

from __future__ import annotations

import logging
import os

import win32com.client as win32
from PySide6.QtCore import QCoreApplication, QMetaObject, QSize, QThread, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
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
    QWidget,
)

logger = logging.getLogger(__name__)

PDF_FILE_FORMAT = 17  # Word 的 wdFormatPDF
STATUS_BAR_HEIGHT = 15
INTERRUPT_WAIT_MS = 5000


class ConvertThread(QThread):
    """在后台用 Word 批量把 docx 转换为 pdf。"""

    docx_count = Signal(int)  # 待转换文件总数
    docx_curr = Signal(int)  # 已处理文件数
    docx_end = Signal()  # 全部结束
    docx_error = Signal(str)  # 致命错误（无法启动 Word 等）
    docx_warning = Signal(str)  # 部分文件失败等非致命提示

    def __init__(self, docx_path: str | None = None) -> None:
        super().__init__()
        self.docx_path = docx_path

    def run(self) -> None:
        if not self.docx_path:
            return

        try:
            word = win32.Dispatch("Word.Application")
            word.Visible = False
        except Exception as exc:
            message = "未检测到 Microsoft Word 2010 或更高版本。"
            logger.exception("%s (%s)", message, exc)
            self.docx_error.emit(message)
            return

        docx_path = os.path.abspath(self.docx_path)
        if os.path.isdir(docx_path):
            source_files = [
                name for name in os.listdir(docx_path) if name.endswith(".docx")
            ]
        else:
            source_files = [docx_path]

        file_count = len(source_files)
        self.docx_count.emit(file_count)
        current = 0
        failed = 0
        self.docx_curr.emit(current)

        for filename in source_files:
            if self.isInterruptionRequested():
                logger.info("DOCX 转换被中断。")
                break
            docx_file = os.path.join(docx_path, filename)
            pdf_file = os.path.join(docx_path, filename.replace(".docx", ".pdf"))
            try:
                doc = word.Documents.Open(os.path.abspath(docx_file))
                doc.SaveAs(os.path.abspath(pdf_file), FileFormat=PDF_FILE_FORMAT)
                doc.Close(SaveChanges=False)
                logger.info("Converted %s to PDF.", docx_file)
            except Exception as exc:
                logger.exception("Error converting %s to PDF: %s", docx_file, exc)
                failed += 1
            current += 1
            self.docx_curr.emit(current)

        logger.info("%d Fail / %d Total files convert.", failed, file_count)
        if failed:
            self.docx_warning.emit(f"{failed} 个文件转换失败，详情见日志。")
        word.Quit()
        self.docx_end.emit()


class Ui_Docx2PdfWin(QMainWindow):
    """界面构建（由 Qt Designer 生成后整理为手写代码）。"""

    def setupUi(self, Docx2PdfWin: QWidget) -> None:
        if not Docx2PdfWin.objectName():
            Docx2PdfWin.setObjectName("Docx2PdfWin")
        Docx2PdfWin.resize(600, 160)
        icon = QIcon()
        icon.addFile(":/emipdf/acbel -1.jpg", QSize(), QIcon.Normal, QIcon.Off)
        Docx2PdfWin.setWindowIcon(icon)

        self.centralwidget = QWidget(Docx2PdfWin)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_2 = QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName("gridLayout_2")

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName("gridLayout")

        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)

        self.textEdit_docx = QLineEdit(self.centralwidget)
        self.textEdit_docx.setObjectName("textEdit_docx")
        sizePolicy.setHeightForWidth(
            self.textEdit_docx.sizePolicy().hasHeightForWidth()
        )
        self.textEdit_docx.setSizePolicy(sizePolicy)
        self.textEdit_docx.setMinimumSize(QSize(360, 30))
        self.gridLayout.addWidget(self.textEdit_docx, 0, 1, 1, 1)

        self.btn_docxdir = QPushButton(self.centralwidget)
        self.btn_docxdir.setObjectName("btn_docxdir")
        self.btn_docxdir.setMinimumSize(QSize(0, 30))
        self.gridLayout.addWidget(self.btn_docxdir, 0, 2, 1, 1)

        self.label = QLabel(self.centralwidget)
        self.label.setObjectName("label")
        self.label.setMinimumSize(QSize(0, 30))
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.button_docxfile = QPushButton(self.centralwidget)
        self.button_docxfile.setObjectName("button_docxfile")
        self.button_docxfile.setMinimumSize(QSize(0, 30))
        self.gridLayout.addWidget(self.button_docxfile, 0, 3, 1, 1)

        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalSpacer = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.btn_docx2pdf = QPushButton(self.centralwidget)
        self.btn_docx2pdf.setObjectName("btn_docx2pdf")
        sizePolicy.setHeightForWidth(self.btn_docx2pdf.sizePolicy().hasHeightForWidth())
        self.btn_docx2pdf.setSizePolicy(sizePolicy)
        self.btn_docx2pdf.setMinimumSize(QSize(50, 30))
        self.horizontalLayout.addWidget(self.btn_docx2pdf)

        self.btn_docxcancel = QPushButton(self.centralwidget)
        self.btn_docxcancel.setObjectName("button_cancel")
        sizePolicy.setHeightForWidth(
            self.btn_docxcancel.sizePolicy().hasHeightForWidth()
        )
        self.btn_docxcancel.setSizePolicy(sizePolicy)
        self.btn_docxcancel.setMinimumSize(QSize(50, 30))
        self.horizontalLayout.addWidget(self.btn_docxcancel)

        self.horizontalSpacer_2 = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.gridLayout_2.addLayout(self.horizontalLayout, 1, 0, 1, 1)

        Docx2PdfWin.setCentralWidget(self.centralwidget)
        self.statusBar_docx = QStatusBar(Docx2PdfWin)
        self.statusBar_docx.setObjectName("statusBar_docx")
        Docx2PdfWin.setStatusBar(self.statusBar_docx)

        self.retranslateUi(Docx2PdfWin)
        self.btn_docxcancel.clicked.connect(Docx2PdfWin.close)

        QMetaObject.connectSlotsByName(Docx2PdfWin)

    def retranslateUi(self, Docx2PdfWin: QWidget) -> None:
        Docx2PdfWin.setWindowTitle(
            QCoreApplication.translate("Docx2PdfWin", "DOCX\u8f6cPDF", None)
        )
        self.textEdit_docx.setPlaceholderText(
            QCoreApplication.translate(
                "Docx2PdfWin",
                "\u8bf7\u8f93\u5165DOCX\u6587\u4ef6\u8def\u5f84\u6216\u5305\u542bDOCX\u6587\u4ef6\u7684\u6587\u4ef6\u5939\u8def\u5f84",
                None,
            )
        )
        self.btn_docxdir.setText(
            QCoreApplication.translate("Docx2PdfWin", "\u9009\u62e9\u76ee\u5f55", None)
        )
        self.label.setText(
            QCoreApplication.translate("Docx2PdfWin", "\u8def\u5f84\uff1a", None)
        )
        self.button_docxfile.setText(
            QCoreApplication.translate("Docx2PdfWin", "\u9009\u62e9\u6587\u4ef6", None)
        )
        self.btn_docx2pdf.setText(
            QCoreApplication.translate("Docx2PdfWin", "\u8f6c \u6362", None)
        )
        self.btn_docxcancel.setText(
            QCoreApplication.translate("Docx2PdfWin", "\u8fd4 \u56de", None)
        )


class Docx2PdfWindow(Ui_Docx2PdfWin):
    """docx 转 pdf 窗口：选择目录/文件、启动转换、显示进度。"""

    def __init__(
        self, parent: QWidget | None = None, rootpath: str | None = None
    ) -> None:
        super().__init__(parent)
        self.running = False
        self.pgBar: QProgressBar | None = None
        self.docx2pdf_thread: ConvertThread | None = None
        self.path = ""
        self.file_count = 0
        self.curr = 0

        self.setupUi(self)
        self.rootpath = (
            rootpath
            if rootpath and os.path.exists(rootpath)
            else os.path.join(os.path.expanduser("~"), "Documents")
        )

        self.btn_docxdir.clicked.connect(lambda: self.select_docx_path(is_dir=True))
        self.button_docxfile.clicked.connect(
            lambda: self.select_docx_path(is_dir=False)
        )
        self.btn_docx2pdf.clicked.connect(self.start_convert)

        logger.info("DOCX 转换窗口初始化完成")

    def select_docx_path(self, is_dir: bool = True) -> None:
        """选择待转换的目录或单个 docx 文件。"""
        if is_dir:
            path = QFileDialog.getExistingDirectory(
                self, "选择DOCX文件所在目录", dir=self.rootpath
            )
            if path:
                self.rootpath = os.path.dirname(path)
                self.textEdit_docx.setText(path)
                self.path = path
                logger.info("已选择待转换目录: %s", path)
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "选择DOCX文件", filter="DOCX文件 (*.docx)", dir=self.rootpath
            )
            if path:
                self.rootpath = os.path.dirname(os.path.dirname(path))
                self.textEdit_docx.setText(path)
                self.path = path
                logger.info("已选择待转换文件: %s", path)

    def start_convert(self) -> None:
        """启动转换线程（重复点击会被忽略）。"""
        if self.running:
            logger.warning("DOCX 转换正在进行，忽略重复启动。")
            return

        self.running = True
        self.path = self.textEdit_docx.text()
        logger.info("启动 DOCX 转换: %s", self.path)

        self.docx2pdf_thread = ConvertThread(self.path)
        self.docx2pdf_thread.docx_count.connect(self.create_status_bar)
        self.docx2pdf_thread.docx_curr.connect(self.update_status_bar)
        self.docx2pdf_thread.docx_end.connect(self.end_status)
        self.docx2pdf_thread.docx_error.connect(self.on_error)
        self.docx2pdf_thread.docx_warning.connect(self.on_warning)
        self.docx2pdf_thread.start()

    @Slot(int)
    def create_status_bar(self, file_count: int) -> None:
        self.file_count = file_count
        self.statusBar_docx.showMessage("正在转换DOCX文件...")
        self.pgBar = QProgressBar(self.statusBar_docx)
        self.pgBar.setMaximumHeight(STATUS_BAR_HEIGHT)
        self.pgBar.setMinimum(0)
        self.pgBar.setMaximum(file_count)
        self.pgBar.setValue(0)
        self.statusBar_docx.addPermanentWidget(self.pgBar)

    @Slot(int)
    def update_status_bar(self, value: int) -> None:
        self.curr = value
        if self.pgBar is not None:
            self.pgBar.setValue(value)
        self.statusBar_docx.showMessage(f"正在转换DOCX文件...{value}/{self.file_count}")

    @Slot()
    def end_status(self) -> None:
        if self.pgBar is not None:
            self.statusBar_docx.removeWidget(self.pgBar)
            self.pgBar = None
        self.statusBar_docx.showMessage(
            f"转换DOCX文件:{self.curr}成功/{self.file_count - self.curr}失败"
        )
        logger.info("DOCX 转换结束: 成功 %d / 共 %d", self.curr, self.file_count)
        self.running = False

    @Slot(str)
    def on_error(self, message: str) -> None:
        """致命错误：在主线程提示并解除运行锁。"""
        logger.error("DOCX 转换失败: %s", message)
        QMessageBox.warning(self, "Error", message)
        self.running = False

    @Slot(str)
    def on_warning(self, message: str) -> None:
        logger.warning("DOCX 转换提示: %s", message)
        QMessageBox.warning(self, "Warning", message)

    def closeEvent(self, event) -> None:
        """关闭窗口时请求中断而非强杀线程，避免残留 Word 进程。"""
        thread = self.docx2pdf_thread
        if thread is not None and thread.isRunning():
            logger.info("关闭窗口，请求中断 DOCX 转换线程。")
            thread.requestInterruption()
            thread.wait(INTERRUPT_WAIT_MS)
        super().closeEvent(event)
