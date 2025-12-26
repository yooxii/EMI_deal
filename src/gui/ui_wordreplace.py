# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt, QSize, QThread, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
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
import re
import sys
import random
import time
import zipfile
import tempfile
import logging

logger = logging.getLogger(__name__)


def replace_text_in_docx(input_path, output_path, old_str, new_str):
    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmp_dir:
        # 解压 .docx 到临时目录
        with zipfile.ZipFile(input_path, "r") as docx_zip:
            docx_zip.extractall(tmp_dir)

        # 替换 word/document.xml 中的内容
        document_xml_path = os.path.join(tmp_dir, "word", "document.xml")
        if os.path.exists(document_xml_path):
            with open(document_xml_path, "r", encoding="utf-8") as f:
                content = f.read()
            # 执行替换
            if isinstance(old_str, str):
                new_content = content.replace(old_str, new_str)
            elif isinstance(old_str, list):
                new_content = content
                for old_str_i, new_str_i in zip(old_str, new_str):
                    if old_str_i is None:
                        continue
                    new_content = new_content.replace(old_str_i, new_str_i)
            new_content = replace_value(new_content)
            with open(document_xml_path, "w", encoding="utf-8") as f:
                f.write(new_content)
        else:
            raise FileNotFoundError("word/document.xml not found in the DOCX file.")

        # 重新打包为新的 .docx
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as new_docx:
            for root, dirs, files in os.walk(tmp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # 计算归档中的相对路径
                    arcname = os.path.relpath(file_path, tmp_dir)
                    new_docx.write(file_path, arcname)

    print(f"✅ 已生成新文件: {output_path}")


def replace_value(content: str):
    random.seed(time.time())

    all_value = re.findall(r"(?<=\>)\d+\.\d+(?=\<)", content)
    all_value = [float(x) for x in all_value]
    for i, value in enumerate(all_value):
        if i % 8 == 1 or i % 8 == 4:
            upper = int((all_value[i + 1] - value) * 100)
            tmp1 = value + random.randrange(-upper, upper) / 2000
            tmp2 = all_value[i + 1] - tmp1
            content = content.replace(str(value), str(round(tmp1, 2)))
            content = content.replace(str(all_value[i + 2]), str(round(tmp2, 2)))

    return content


class WordReplaceThread(QThread):
    docx_count = Signal(int)
    docx_curr = Signal(int)
    docx_end = Signal()

    def __init__(
        self, path_src, path_tgt, args_srcs, args_tgts, args_src=None, args_tgt=None
    ):
        super().__init__()
        self.path_src = path_src
        self.path_tgt = path_tgt
        self.args_srcStrings = args_srcs
        self.args_tgtStrings = args_tgts
        self.args_srcString = args_src
        self.args_tgtString = args_tgt
        self.stop = False

    def run(self):
        if "" in [
            self.path_src,
            self.path_tgt,
            self.args_srcStrings,
            self.args_tgtStrings,
        ]:
            logger.error("请选择源文件、目标文件、源参数、目标参数")
            return
        else:
            # 确保路径可被访问
            path_src = os.path.abspath(self.path_src)
            path_tgt = os.path.abspath(self.path_tgt)

            # 将获取到的sn字符串转换为列表
            if isinstance(self.args_srcStrings, str):
                self.args_srcStrings = self.args_srcStrings.split(
                    "," if "," in self.args_srcStrings else None
                )
            if isinstance(self.args_tgtStrings, str):
                self.args_tgtStrings = self.args_tgtStrings.split(
                    "," if "," in self.args_tgtStrings else None
                )
            if len(self.args_srcStrings) != len(self.args_tgtStrings):
                logger.error("源字符串集和目标字符串集数量不一致")
                QMessageBox.critical(
                    self, "Error", "源字符串集和目标字符串集数量不一致"
                )
                return
        # 获取源文件列表
        if os.path.isdir(path_src):
            source_files = [f for f in os.listdir(path_src) if f.endswith(".docx")]
        else:
            source_files = [path_src]
        # 创建目标文件夹
        if not os.path.exists(path_tgt):
            os.makedirs(path_tgt)
        file_count = len(source_files)
        self.docx_count.emit(file_count)
        curr = 0  # 当前处理文件计数
        self.docx_curr.emit(curr)
        #
        for src_Strings, tgt_Strings in zip(self.args_srcStrings, self.args_tgtStrings):
            dealed_files = []
            for srcfile in source_files:
                if srcfile.find(src_Strings) >= 0:
                    srcpath = os.path.join(path_src, srcfile)
                    tgtpath = os.path.join(
                        path_tgt, srcfile.replace(src_Strings, tgt_Strings)
                    )
                    replace_text_in_docx(
                        srcpath,
                        tgtpath,
                        [src_Strings, self.args_srcString],
                        [tgt_Strings, self.args_tgtString],
                    )
                    dealed_files.append(srcfile)
                    curr += 1
                    self.docx_curr.emit(curr)
            for dealed_file in dealed_files:
                source_files.remove(dealed_file)
        self.docx_end.emit()

    def terminate(self):
        self.stop = True
        return super().terminate()


class WordReplace(QMainWindow):
    def __init__(self, parent=None, rootpath=None):
        super().__init__(parent)
        self.setupUi()
        self.rootpath = (
            rootpath if rootpath else os.path.join(os.path.expanduser("~"), "Documents")
        )
        self.wordreplace_thread = None

        self.btn_srcpath.clicked.connect(self.select_srcdocx_path)
        self.btn_srcfile.clicked.connect(self.select_srcdocx_file)
        self.btn_tgtpath.clicked.connect(self.select_tgtpath)
        self.btn_start.clicked.connect(self.wordreplaceThread)
        self.btn_close.clicked.connect(self.close)

    def setupUi(self):
        self.setWindowTitle(self.tr("Word替换"))
        self.resize(600, 350)
        icon = QIcon()
        icon.addFile(":/emipdf/acbel -1.jpg", QSize(), QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)
        mainWidget = QWidget()
        mainWidget.setObjectName("mainWidget")
        self.setCentralWidget(mainWidget)
        self.HLayout = QHBoxLayout()
        self.VLayout = QVBoxLayout()

        mainWidget.setLayout(self.HLayout)

        hSpacer = QSpacerItem(
            20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        vSpacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        self.HLayout.addItem(hSpacer)
        self.HLayout.addLayout(self.VLayout)
        self.HLayout.addItem(hSpacer)

        self.VLayout.addItem(vSpacer)

        self.Layout_input = QVBoxLayout()
        self.VLayout.addLayout(self.Layout_input)
        self.VLayout.addItem(vSpacer)

        layout_srcpath = QHBoxLayout()
        layout_srcpath.setAlignment(Qt.AlignmentFlag.AlignLeft)
        label_srcpath = QLabel(self.tr("原来路径:"))
        label_srcpath.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout_srcpath.addWidget(label_srcpath)
        self.lineEdit_srcpath = QLineEdit()
        layout_srcpath.addWidget(self.lineEdit_srcpath)
        self.btn_srcpath = QPushButton(self.tr("目录"))
        self.btn_srcpath.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_srcpath.setFixedWidth(40)
        layout_srcpath.addWidget(self.btn_srcpath)
        self.btn_srcfile = QPushButton(self.tr("文件"))
        self.btn_srcfile.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_srcfile.setFixedWidth(40)
        layout_srcpath.addWidget(self.btn_srcfile)
        self.Layout_input.addLayout(layout_srcpath)

        layout_topath = QHBoxLayout()
        layout_topath.setAlignment(Qt.AlignmentFlag.AlignLeft)
        label_topath = QLabel(self.tr("目标路径:"))
        label_topath.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout_topath.addWidget(label_topath)
        self.lineEdit_tgtpath = QLineEdit()
        layout_topath.addWidget(self.lineEdit_tgtpath)
        self.btn_tgtpath = QPushButton(self.tr("目录"))
        self.btn_tgtpath.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tgtpath.setFixedWidth(86)
        layout_topath.addWidget(self.btn_tgtpath)
        self.Layout_input.addLayout(layout_topath)

        layout_args = QGridLayout()
        self.Layout_input.addLayout(layout_args)

        text_height = 60
        layout_srcargs = QVBoxLayout()
        label_srcStrings = QLabel(self.tr("原字符串集:"))
        label_srcStrings.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        layout_srcargs.addWidget(label_srcStrings)
        self.text_srcStrings = QTextEdit()
        self.text_srcStrings.setFixedHeight(text_height)
        self.text_srcStrings.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout_srcargs.addWidget(self.text_srcStrings)
        label_srcString = QLabel(self.tr("原字符串:"))
        label_srcString.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum
        )
        layout_srcargs.addWidget(label_srcString)
        self.lineEdit_srcString = QLineEdit()
        layout_srcargs.addWidget(self.lineEdit_srcString)
        layout_args.addLayout(layout_srcargs, 0, 0)

        layout_tgtargs = QVBoxLayout()
        label_tgtStrings = QLabel(self.tr("目标字符串集:"))
        label_tgtStrings.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        layout_tgtargs.addWidget(label_tgtStrings)
        self.text_tgtStrings = QTextEdit()
        self.text_tgtStrings.setFixedHeight(text_height)
        self.text_tgtStrings.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout_tgtargs.addWidget(self.text_tgtStrings)
        label_tgtString = QLabel(self.tr("目标字符串:"))
        label_tgtString.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum
        )
        layout_tgtargs.addWidget(label_tgtString)
        self.lineEdit_tgtString = QLineEdit()
        layout_tgtargs.addWidget(self.lineEdit_tgtString)
        layout_args.addLayout(layout_tgtargs, 0, 1)

        Layout_btns = QHBoxLayout()
        Layout_btns.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_start = QPushButton(self.tr("开始"))
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        Layout_btns.addWidget(self.btn_start)
        Layout_btns.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Fixed))
        self.btn_close = QPushButton(self.tr("关闭"))
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        Layout_btns.addWidget(self.btn_close)
        self.Layout_input.addLayout(Layout_btns)

        self.statusBar_docx = QStatusBar()
        self.setStatusBar(self.statusBar_docx)

    def select_srcdocx_path(self):
        path = QFileDialog.getExistingDirectory(
            self,
            "选择DOCX文件所在目录",
            dir=self.rootpath,
        )
        self.rootpath = os.path.split(path)[0]
        if path:
            self.lineEdit_srcpath.setText(path)
            self.path = path

    def select_tgtpath(self):
        path = QFileDialog.getExistingDirectory(
            self,
            "选择DOCX文件所在目录",
            dir=self.rootpath,
        )
        self.rootpath = os.path.split(path)[0]
        if path:
            self.lineEdit_tgtpath.setText(path)
            self.path = path

    def select_srcdocx_file(self):
        path = QFileDialog.getOpenFileName(
            self,
            "选择DOCX文件",
            filter="DOCX文件 (*.docx)",
            dir=self.rootpath,
        )
        self.rootpath = os.path.split(os.path.dirname(path[0]))[0]
        if path:
            self.lineEdit_srcpath.setText(path[0])
            self.path = path[0]

    def wordreplaceThread(self):
        self.wordreplace_thread = WordReplaceThread(
            self.lineEdit_srcpath.text(),
            self.lineEdit_tgtpath.text(),
            self.text_srcStrings.toPlainText(),
            self.text_tgtStrings.toPlainText(),
            self.lineEdit_srcString.text(),
            self.lineEdit_tgtString.text(),
        )

        self.wordreplace_thread.docx_count.connect(self.createStatusBar)
        self.wordreplace_thread.docx_curr.connect(self.updateStatusBar)
        self.wordreplace_thread.docx_end.connect(self.endStatus)
        self.wordreplace_thread.start()

    @Slot(int)
    def createStatusBar(self, file_count):
        self.file_count = file_count
        # 创建状态栏进度条
        self.statusBar_docx.showMessage("正在替换DOCX文件...")
        self.pgBar = QProgressBar(self.statusBar_docx)
        self.pgBar.setMinimum(0)
        self.pgBar.setMaximum(file_count)
        self.pgBar.setValue(0)
        self.statusBar_docx.addPermanentWidget(self.pgBar)

    @Slot(int)
    def updateStatusBar(self, value):
        self.curr = value
        self.pgBar.setValue(value)
        self.statusBar_docx.showMessage(f"正在替换DOCX文件...{value}/{self.file_count}")

    @Slot()
    def endStatus(self):
        self.statusBar_docx.removeWidget(self.pgBar)
        self.statusBar_docx.showMessage(
            f"替换DOCX文件:{self.curr}成功/{self.file_count-self.curr}失败"
        )

    def closeEvent(self, event):
        if hasattr(self, "wordreplace_thread") and self.wordreplace_thread is not None:
            self.wordreplace_thread.terminate()
        return super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = WordReplace()
    win.show()
    sys.exit(app.exec())
