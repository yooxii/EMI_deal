# -*- coding: utf-8 -*-

from PySide6.QtCore import QCoreApplication, QMetaObject, QSize, QThread, Signal, Slot
from PySide6.QtGui import (
    QIcon,
)
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStatusBar,
    QWidget,
    QMessageBox,
    QFileDialog,
    QProgressBar,
    QMainWindow,
)

import os
import win32com.client as win32
import logging
import win32com.client as win32

logger = logging.getLogger(__name__)


class ConvertThread(QThread):
    docx_count = Signal(int)
    docx_curr = Signal(int)
    docx_end = Signal()
    docx_error = Signal(str)

    def __init__(self, docx_path=None):
        super().__init__()
        self.docx_path = docx_path
        self.stop = False

    def run(self):
        if self.docx_path is None:
            return
        else:
            docx_path = self.docx_path
        try:
            word = win32.Dispatch("Word.Application")
            word.Visible = False
        except:
            print("Please install Microsoft Word 2010 or later.")
            logger.error("Please install Microsoft Word 2010 or later.")
            QMessageBox.warning(
                self, "Error", "Please install Microsoft Word 2010 or later."
            )
            return
        docx_path = os.path.abspath(docx_path)
        if os.path.isdir(docx_path):
            source_files = [f for f in os.listdir(docx_path) if f.endswith(".docx")]
        else:
            source_files = [docx_path]
        file_count = len(source_files)
        self.docx_count.emit(file_count)
        curr = 0
        error_counts = 0
        self.docx_curr.emit(curr)
        for file_ in source_files:
            if self.stop:
                break
            docx_file = os.path.join(docx_path, file_)
            pdf_file = os.path.join(docx_path, file_.replace(".docx", ".pdf"))
            try:
                doc = word.Documents.Open(os.path.abspath(docx_file))
                doc.SaveAs(os.path.abspath(pdf_file), FileFormat=17)
                doc.Close(SaveChanges=False)
                logger.info(f"Converted {docx_file} to PDF.")
            except Exception as e:
                logger.error(f"Error converting {docx_file} to PDF: {e}")
                error_counts += 1
            curr = curr + 1
            self.docx_curr.emit(curr)
        if error_counts > 0:
            QMessageBox.warning(
                self, "Warning", f"{error_counts} files failed to convert."
            )
        logger.info(f"{error_counts} Fail / {file_count} Total files convert.")
        word.Quit()
        self.docx_end.emit()

    def terminate(self):
        self.stop = True
        return super().terminate()


class Ui_Docx2PdfWin(QMainWindow):
    def setupUi(self, Docx2PdfWin: QWidget):
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
        self.textEdit_docx = QLineEdit(self.centralwidget)
        self.textEdit_docx.setObjectName("textEdit_docx")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
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

    # setupUi

    def retranslateUi(self, Docx2PdfWin: QWidget):
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

    # retranslateUi


class Docx2PdfWindow(Ui_Docx2PdfWin):
    def __init__(self, parent=None, rootpath=None):
        super().__init__(parent)
        self.running = False

        self.setupUi(self)
        self.rootpath = (
            rootpath
            if os.path.exists(rootpath)
            else os.path.join(os.path.expanduser("~"), "Documents")
        )
        self.docx2pdf_thread = None
        self.path = ""

        self.btn_docxdir.clicked.connect(lambda: self.select_docx_path(is_dir=True))
        self.button_docxfile.clicked.connect(
            lambda: self.select_docx_path(is_dir=False)
        )
        self.btn_docx2pdf.clicked.connect(self.docx2pdfThread)

        logger.info("Docx2PdfWindow inited")

    def select_docx_path(self, is_dir=True):
        if is_dir:
            path = QFileDialog.getExistingDirectory(
                self,
                "选择DOCX文件所在目录",
                dir=self.rootpath,
            )
            self.rootpath = os.path.split(path)[0]
            if path:
                self.textEdit_docx.setText(path)
                self.path = path
        else:
            path = QFileDialog.getOpenFileName(
                self,
                "选择DOCX文件",
                filter="DOCX文件 (*.docx)",
                dir=self.rootpath,
            )
            self.rootpath = os.path.split(os.path.dirname(path[0]))[0]
            if path:
                self.textEdit_docx.setText(path[0])
                self.path = path[0]

    def docx2pdfThread(self):
        if self.running:
            logger.warning("docx2pdfThread is running, do not start again")
            return
        self.running = True
        logger.info("docx2pdfThread start")
        self.path = self.textEdit_docx.text()
        self.docx2pdf_thread = ConvertThread(self.path)
        self.docx2pdf_thread.docx_count.connect(self.createStatusBar)
        self.docx2pdf_thread.docx_curr.connect(self.updateStatusBar)
        self.docx2pdf_thread.docx_end.connect(self.endStatus)
        self.docx2pdf_thread.start()

    @Slot(int)
    def createStatusBar(self, file_count):
        self.file_count = file_count
        # 创建状态栏进度条
        self.statusBar_docx.showMessage("正在转换DOCX文件...")
        self.pgBar = QProgressBar(self.statusBar_docx)
        self.pgBar.setMaximumHeight(15)
        self.pgBar.setMinimum(0)
        self.pgBar.setMaximum(file_count)
        self.pgBar.setValue(0)
        self.statusBar_docx.addPermanentWidget(self.pgBar)

    @Slot(int)
    def updateStatusBar(self, value):
        self.curr = value
        self.pgBar.setValue(value)
        self.statusBar_docx.showMessage(f"正在转换DOCX文件...{value}/{self.file_count}")

    @Slot()
    def endStatus(self):
        self.statusBar_docx.removeWidget(self.pgBar)
        self.statusBar_docx.showMessage(
            f"转换DOCX文件:{self.curr}成功/{self.file_count-self.curr}失败"
        )
        self.running = False

    def closeEvent(self, event):
        if hasattr(self, "docx2pdf_thread") and self.docx2pdf_thread is not None:
            self.docx2pdf_thread.terminate()
        return super().closeEvent(event)
