from PySide6.QtCore import QDate, QRect, QSize, Qt
from PySide6.QtGui import QAction, QCursor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QLineEdit,
    QSpinBox,
    QDateEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QGridLayout,
    QHBoxLayout,
    QGroupBox,
    QWidget,
    QFrame,
)
from gui.res_rc import *
import os
import sys
import logging

logger = logging.getLogger(__name__)
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


class HoverLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 创建一个用于显示预览的小部件
        self.preview_widget = QWidget()
        # self.preview_widget.setWindowFlags(Qt.WindowType.Popup)
        self.preview_widget.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        layout = QVBoxLayout()
        self.preview_label = QLabel(self.preview_widget)
        layout.addWidget(self.preview_label)
        self.preview_widget.setLayout(layout)

    def enterEvent(self, event):
        # 当鼠标进入QLineEdit时触发
        self.show_preview()

    def leaveEvent(self, event):
        # 当鼠标离开QLineEdit时隐藏预览
        self.hide_preview()

    def show_preview(self):
        # 从 QLineEdit 获取图片路径
        image_path = self.text().strip()
        if not image_path:
            return

        # 加载并显示图片
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self.preview_label.setPixmap(
                pixmap.scaledToWidth(300, Qt.SmoothTransformation)
            )  # 调整大小方便查看

            pos = self.mapToGlobal(self.geometry().topRight())
            self.preview_widget.move(pos.x(), pos.y())
            self.preview_widget.show()
        else:
            logger.error(f"无法加载图片: {image_path}")

    def hide_preview(self):
        # 隐藏图片预览
        self.preview_widget.hide()


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi()

    def setupUi(self):
        self.setWindowTitle(self.tr("EMI-Report"))
        self.setObjectName("MainWindow")
        self.resize(600, 450)
        icon = QIcon()
        icon.addFile(":/emipdf/acbel -1.jpg", QSize(), QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)
        self.setStyleSheet("QAction { font-size: 12px; }")
        self.statusBar_main = QStatusBar()
        self.setStatusBar(self.statusBar_main)

        self.setMainWidget()
        self.setMainMenu()

    def setMainWidget(self):
        mainWidget = QWidget()
        mainWidget.setObjectName("mainWidget")
        self.setCentralWidget(mainWidget)

        hSpacer = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        vSpacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        HLayout = QHBoxLayout()
        HLayout.setObjectName("HLayout")
        self.mainLayout = QVBoxLayout()

        HLayout.addSpacerItem(hSpacer)
        HLayout.addLayout(self.mainLayout)
        HLayout.addSpacerItem(hSpacer)
        mainWidget.setLayout(HLayout)

        self.mainLayout.addSpacerItem(vSpacer)
        layout_input = QVBoxLayout()
        self.mainLayout.addLayout(layout_input)
        self.mainLayout.addSpacerItem(vSpacer)

        layout_temp = QHBoxLayout()
        layout_temp.addWidget(QLabel(self.tr("模版路径：")))
        self.lineEdit_template = QLineEdit()
        layout_temp.addWidget(self.lineEdit_template)
        self.btnfile_template = QPushButton(self.tr("浏览"))
        self.btnfile_template.setMaximumWidth(40)
        self.btnfile_template.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        layout_temp.addWidget(self.btnfile_template)
        layout_input.addLayout(layout_temp)

        layout_model = QHBoxLayout()
        layout_model.addWidget(QLabel(self.tr("数据路径：")))
        self.lineEdit_model = QLineEdit()
        layout_model.addWidget(self.lineEdit_model)
        self.btnfile_model = QPushButton(self.tr("浏览"))
        self.btnfile_model.setMaximumWidth(40)
        self.btnfile_model.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        layout_model.addWidget(self.btnfile_model)
        layout_input.addLayout(layout_model)

        box_otherinfo = QGroupBox(self.tr("补充信息"))
        boxinfo_layout = QGridLayout(box_otherinfo)

        layout_qty = QHBoxLayout()
        layout_qty.setAlignment(Qt.AlignmentFlag.AlignLeft)
        label_qty = QLabel(self.tr("负载数量："))
        label_qty.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout_qty.addWidget(label_qty)
        self.spin_qty = QSpinBox()
        self.spin_qty.setValue(3)
        layout_qty.addWidget(self.spin_qty)
        boxinfo_layout.addLayout(layout_qty, 1, 1)

        layout_week = QHBoxLayout()
        layout_week.setAlignment(Qt.AlignmentFlag.AlignLeft)
        label_week = QLabel(self.tr("周期："))
        label_week.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout_week.addWidget(label_week)
        self.lineEdit_week = QLineEdit()
        layout_week.addWidget(self.lineEdit_week)
        boxinfo_layout.addLayout(layout_week, 1, 2)

        layout_rev = QHBoxLayout()
        layout_rev.setAlignment(Qt.AlignmentFlag.AlignLeft)
        label_rev = QLabel(self.tr("版本："))
        layout_rev.addWidget(label_rev)
        self.lineEdit_rev = QLineEdit()
        self.lineEdit_rev.setMaximumWidth(60)
        layout_rev.addWidget(self.lineEdit_rev)
        boxinfo_layout.addLayout(layout_rev, 1, 3)

        layout_testdate = QHBoxLayout()
        layout_testdate.setAlignment(Qt.AlignmentFlag.AlignLeft)
        label_testdate = QLabel(self.tr("测试日期："))
        label_testdate.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout_testdate.addWidget(label_testdate)
        self.date_test = QDateEdit()
        self.date_test.setDate(QDate.currentDate())
        self.date_test.setCalendarPopup(True)
        self.date_test.setMinimumWidth(90)
        layout_testdate.addWidget(self.date_test)
        boxinfo_layout.addLayout(layout_testdate, 2, 1)

        layout_workerno = QHBoxLayout()
        layout_workerno.setAlignment(Qt.AlignmentFlag.AlignLeft)
        label_workerno = QLabel(self.tr("工令："))
        label_workerno.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout_workerno.addWidget(label_workerno)
        self.lineEdit_workerno = QLineEdit()
        layout_workerno.addWidget(self.lineEdit_workerno)
        boxinfo_layout.addLayout(layout_workerno, 2, 2, 1, 2)

        layout_img = QHBoxLayout()
        layout_img.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.label_img = QLabel(self.tr("测试图片："))
        self.label_img.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout_img.addWidget(self.label_img)
        self.lineEdit_img = HoverLineEdit()
        layout_img.addWidget(self.lineEdit_img)
        self.btnfile_img = QPushButton(self.tr("选择"))
        self.btnfile_img.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btnfile_img.setMaximumWidth(40)
        layout_img.addWidget(self.btnfile_img)
        boxinfo_layout.addLayout(layout_img, 3, 1, 1, 3)

        # 添加分隔线
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setFrameShadow(QFrame.Shadow.Sunken)
        boxinfo_layout.addWidget(line1, 4, 1, 1, 3)

        layout_detail = QVBoxLayout()
        layout_detail.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout_detail_1 = QHBoxLayout()
        label_detail = QLabel(self.tr("测试细节："))
        label_detail.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout_detail_1.addWidget(label_detail)
        self.btn_getdetail = QPushButton(self.tr("点击此处获取"))
        self.btn_getdetail.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.btn_getdetail.setStyleSheet(
            "QPushButton{background-color: rgba(0,0,0,0);}"
        )
        self.btn_getdetail.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        layout_detail_1.addWidget(self.btn_getdetail)
        layout_detail.addLayout(layout_detail_1)
        self.text_detail = QTextEdit()
        layout_detail.addWidget(self.text_detail)
        boxinfo_layout.addLayout(layout_detail, 5, 1, 1, 3)

        layout_input.addWidget(box_otherinfo)

        layout_btns = QHBoxLayout()
        self.btn_start = QPushButton(self.tr("开始"))
        self.btn_start.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_start.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        layout_btns.addWidget(self.btn_start)
        self.btn_exit = QPushButton(self.tr("退出"))
        self.btn_exit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_exit.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout_btns.addWidget(self.btn_exit)
        layout_input.addLayout(layout_btns)

    def setMainMenu(self):
        self.mainMenuBar = QMenuBar(self)
        self.mainMenuBar.setGeometry(QRect(0, 0, 600, 26))
        self.mainMenuBar.setObjectName("menuBar")

        self.menuSelect = QMenu(self.mainMenuBar)
        self.menuSelect.setTitle(self.tr("选项"))
        self.mainMenuBar.addMenu(self.menuSelect)
        self.action_sets = QAction(self.tr("设置"), self.menuSelect)
        self.action_sets.setShortcut("Ctrl+I")
        self.action_exit = QAction(self.tr("退出"), self.menuSelect)
        self.menuSelect.addAction(self.action_sets)
        self.menuSelect.addAction(self.action_exit)
        self.mainMenuBar.addMenu(self.menuSelect)

        self.menuTool = QMenu(self.mainMenuBar)
        self.menuTool.setTitle(self.tr("工具"))
        self.mainMenuBar.addMenu(self.menuTool)
        self.action_log = QAction(self.tr("查看日志"), self.menuTool)
        self.action_log.setShortcut("Ctrl+J")
        self.action_topdf = QAction(self.tr("docx转pdf"), self.menuTool)
        self.action_topdf.setShortcut("Ctrl+T")
        self.action_wordreplace = QAction(self.tr("word替换"), self)
        self.action_wordreplace.setShortcut("Ctrl+G")
        self.menuTool.addAction(self.action_log)
        self.menuTool.addAction(self.action_topdf)
        self.addAction(self.action_wordreplace)
        self.mainMenuBar.addMenu(self.menuTool)

        self.menuHelp = QMenu(self.mainMenuBar)
        self.menuHelp.setTitle(self.tr("帮助"))
        self.mainMenuBar.addMenu(self.menuHelp)
        self.action_doc = QAction(self.tr("使用文档"), self.menuHelp)
        self.action_about = QAction(self.tr("关于"), self.menuHelp)
        self.menuHelp.addAction(self.action_doc)
        self.menuHelp.addAction(self.action_about)
        self.mainMenuBar.addMenu(self.menuHelp)

        self.setMenuBar(self.mainMenuBar)


if __name__ == "__main__":
    app = QApplication()
    window = MainWindow()
    window.show()
    app.exec()
