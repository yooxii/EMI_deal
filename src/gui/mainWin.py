"""主窗口界面。

界面全部用代码搭建（不再依赖 Qt Designer 的 .ui 文件），由 :class:`MainWindow`
提供骨架与控件，业务逻辑在 :class:`EMI-Report.EMIWindow` 中实现。

直接预览本界面：在 ``src`` 目录下执行 ``python -m gui.mainWin``。
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QDate, QRect, QSize, Qt
from PySide6.QtGui import QAction, QCursor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QStatusBar,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.res_rc import *  # noqa: F401,F403  # 导入即注册 Qt 资源（:/emipdf/...）
from gui.widgets import ClickableLabel

logger = logging.getLogger(__name__)

SERIAL_VIEW_HEIGHT = 50  # 序列号显示区高度
SERIAL_TABLE_HEIGHT = 110  # 按序列号填写表格的高度（超出可滚动）
SERIAL_HEADER_WIDTH = 200  # 表格行标题宽度（显示序列号）


class HoverLineEdit(QLineEdit):
    """鼠标悬停时在右侧弹出图片预览的输入框（用于测试图片路径）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.preview_widget = QWidget(self, Qt.WindowType.FramelessWindowHint)
        preview_layout = QVBoxLayout()
        self.preview_label = QLabel(self.preview_widget)
        preview_layout.addWidget(self.preview_label)
        self.preview_widget.setLayout(preview_layout)

    def enterEvent(self, event) -> None:
        self.show_preview()

    def leaveEvent(self, event) -> None:
        self.hide_preview()

    def show_preview(self) -> None:
        """把输入框内容当作图片路径加载并显示预览。"""
        image_path = self.text().strip()
        if not image_path:
            return

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            logger.error("无法加载图片: %s", image_path)
            return

        self.preview_label.setPixmap(pixmap.scaledToWidth(300, Qt.SmoothTransformation))
        position = self.mapToGlobal(self.geometry().topRight())
        self.preview_widget.move(position.x(), position.y())
        self.preview_widget.show()

    def hide_preview(self) -> None:
        self.preview_widget.hide()


class MainWindow(QMainWindow):
    """主窗口骨架：路径输入、补充信息、操作按钮与菜单栏。"""

    def __init__(self) -> None:
        super().__init__()
        self.setupUi()

    def setupUi(self) -> None:
        self.setWindowTitle(self.tr("EMI-Report"))
        self.setObjectName("MainWindow")
        # 比旧版高一些：新增了「序列号」显示区与「按序列号填写」表格
        self.resize(600, 680)
        icon = QIcon()
        icon.addFile(":/emipdf/acbel -1.jpg", QSize(), QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)
        self.setStyleSheet("QAction { font-size: 12px; }")

        self.statusBar_main = QStatusBar()
        self.setStatusBar(self.statusBar_main)

        self._build_main_widget()
        self._build_main_menu()

    # ---- 界面构建 -------------------------------------------------------- #

    def _build_main_widget(self) -> None:
        main_widget = QWidget()
        main_widget.setObjectName("mainWidget")
        self.setCentralWidget(main_widget)

        h_spacer = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        v_spacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        outer_layout = QHBoxLayout()
        outer_layout.setObjectName("HLayout")
        self.main_layout = QVBoxLayout()

        outer_layout.addSpacerItem(h_spacer)
        outer_layout.addLayout(self.main_layout)
        outer_layout.addSpacerItem(h_spacer)
        main_widget.setLayout(outer_layout)

        self.main_layout.addSpacerItem(v_spacer)
        input_layout = QVBoxLayout()
        self.main_layout.addLayout(input_layout)
        self.main_layout.addSpacerItem(v_spacer)

        self._build_path_rows(input_layout)
        input_layout.addWidget(self._build_serial_box())
        input_layout.addWidget(self._build_info_box())
        # 表格默认隐藏，由「工令不同」勾选框控制展开
        self.serial_table_box = self._build_serial_table_box()
        self.serial_table_box.setVisible(False)
        input_layout.addWidget(self.serial_table_box)
        self._build_action_buttons(input_layout)

    def _build_serial_table_box(self) -> QGroupBox:
        """按序列号填写工令 / 版本（留空则用「补充信息」里的默认值）。

        行标题显示序列号，两列分别是工令与版本；行随数据路径下的序列号自动刷新。
        """
        table_box = QGroupBox(self.tr("按序列号填写工令 / 版本（留空用上面的默认值）"))
        table_layout = QVBoxLayout(table_box)

        self.table_serial = QTableWidget(0, 2)
        self.table_serial.setHorizontalHeaderLabels([self.tr("工令"), self.tr("版本")])
        self.table_serial.verticalHeader().setFixedWidth(SERIAL_HEADER_WIDTH)
        self.table_serial.verticalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.table_serial.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table_serial.setAlternatingRowColors(True)
        self.table_serial.setFixedHeight(SERIAL_TABLE_HEIGHT)
        self.table_serial.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
        )
        table_layout.addWidget(self.table_serial)
        return table_box

    def _build_serial_box(self) -> QGroupBox:
        """序列号显示区（位于「补充信息」上方）。

        序列号取自数据路径下报告文件名中「-」之前的第一段，点击标签可手动刷新。
        """
        serial_box = QGroupBox(self.tr("序列号"))
        serial_layout = QVBoxLayout(serial_box)

        self.label_serial = ClickableLabel(self.tr("序列号（点击刷新）"))
        self.label_serial.setToolTip(
            self.tr("从数据路径下的报告文件名中提取：按「-」取第一段并自动去重。")
        )
        serial_layout.addWidget(self.label_serial)

        self.text_serial = QTextEdit()
        self.text_serial.setReadOnly(True)
        self.text_serial.setFixedHeight(SERIAL_VIEW_HEIGHT)
        serial_layout.addWidget(self.text_serial)
        return serial_box

    def _build_path_rows(self, input_layout: QVBoxLayout) -> None:
        """模板路径与数据路径两行输入。"""
        self.lineEdit_template = QLineEdit()
        self.btnfile_template = self._make_browse_button(self.lineEdit_template)
        input_layout.addLayout(
            self._make_path_row(
                self.tr("模版路径："), self.lineEdit_template, self.btnfile_template
            )
        )

        self.lineEdit_model = QLineEdit()
        self.btnfile_model = self._make_browse_button(self.lineEdit_model)
        input_layout.addLayout(
            self._make_path_row(
                self.tr("数据路径："), self.lineEdit_model, self.btnfile_model
            )
        )

    def _make_browse_button(self, line_edit: QLineEdit) -> QPushButton:
        button = QPushButton(self.tr("浏览"))
        button.setMaximumWidth(40)
        button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        return button

    @staticmethod
    def _make_path_row(
        label_text: str, line_edit: QLineEdit, button: QPushButton
    ) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label_text))
        row.addWidget(line_edit)
        row.addWidget(button)
        return row

    def _build_info_box(self) -> QGroupBox:
        """补充信息区：负载数量、周期、版本、测试日期、工令、图片与测试细节。"""
        info_box = QGroupBox(self.tr("补充信息"))
        info_layout = QGridLayout(info_box)

        # 第一行：负载数量 / 周期 / 版本
        self.spin_qty = QSpinBox()
        self.spin_qty.setValue(3)
        info_layout.addLayout(
            self._make_info_row(self.tr("负载数量："), self.spin_qty), 1, 1
        )

        self.lineEdit_week = QLineEdit()
        info_layout.addLayout(
            self._make_info_row(self.tr("周期："), self.lineEdit_week), 1, 2
        )

        self.lineEdit_rev = QLineEdit()
        self.lineEdit_rev.setMaximumWidth(60)
        info_layout.addLayout(
            self._make_info_row(self.tr("版本："), self.lineEdit_rev), 1, 3
        )

        # 第二行：测试日期 / 工令
        self.date_test = QDateEdit()
        self.date_test.setDate(QDate.currentDate())
        self.date_test.setCalendarPopup(True)
        self.date_test.setMinimumWidth(90)
        info_layout.addLayout(
            self._make_info_row(self.tr("测试日期："), self.date_test), 2, 1
        )

        self.lineEdit_workerno = QLineEdit()
        workno_row = self._make_info_row(self.tr("工令："), self.lineEdit_workerno)
        self.check_diff_workno = QCheckBox(self.tr("工令不同"))
        self.check_diff_workno.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.check_diff_workno.setToolTip(
            self.tr("勾选后展开下方表格，可按序列号分别填写工令与版本。")
        )
        workno_row.addWidget(self.check_diff_workno)
        info_layout.addLayout(workno_row, 2, 2, 1, 2)

        # 第三行：测试图片（悬停可预览）
        self.lineEdit_img = HoverLineEdit()
        self.btnfile_img = QPushButton(self.tr("选择"))
        self.btnfile_img.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btnfile_img.setMaximumWidth(40)
        image_row = QHBoxLayout()
        image_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.label_img = QLabel(self.tr("测试图片："))
        self.label_img.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        image_row.addWidget(self.label_img)
        image_row.addWidget(self.lineEdit_img)
        image_row.addWidget(self.btnfile_img)
        info_layout.addLayout(image_row, 3, 1, 1, 3)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        info_layout.addWidget(divider, 4, 1, 1, 3)

        # 第四行：测试细节
        self.text_detail = QTextEdit()
        detail_row = QHBoxLayout()
        detail_label = QLabel(self.tr("测试细节："))
        detail_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        detail_row.addWidget(detail_label)

        self.btn_getdetail = QPushButton(self.tr("点击此处获取"))
        self.btn_getdetail.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.btn_getdetail.setStyleSheet(
            "QPushButton{background-color: rgba(0,0,0,0);}"
        )
        self.btn_getdetail.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        detail_row.addWidget(self.btn_getdetail)

        detail_layout = QVBoxLayout()
        detail_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        detail_layout.addLayout(detail_row)
        detail_layout.addWidget(self.text_detail)
        info_layout.addLayout(detail_layout, 5, 1, 1, 3)

        return info_box

    @staticmethod
    def _make_info_row(label_text: str, widget: QWidget) -> QHBoxLayout:
        """一行「标签 + 输入控件」，标签宽度固定。"""
        row = QHBoxLayout()
        row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        label = QLabel(label_text)
        label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        row.addWidget(label)
        row.addWidget(widget)
        return row

    def _build_action_buttons(self, input_layout: QVBoxLayout) -> None:
        self.btn_start = QPushButton(self.tr("开始"))
        self.btn_start.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_start.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.btn_clear = QPushButton(self.tr("清空"))
        self.btn_clear.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_clear.setToolTip(
            self.tr("清空除「模版路径」「测试细节」以外的输入内容。")
        )

        self.btn_exit = QPushButton(self.tr("退出"))
        self.btn_exit.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_exit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        buttons = QHBoxLayout()
        buttons.addWidget(self.btn_start)
        buttons.addWidget(self.btn_clear)
        buttons.addWidget(self.btn_exit)
        input_layout.addLayout(buttons)

    def _build_main_menu(self) -> None:
        self.mainMenuBar = QMenuBar(self)
        self.mainMenuBar.setGeometry(QRect(0, 0, 600, 26))
        self.mainMenuBar.setObjectName("menuBar")

        self.menuSelect = QMenu(self.mainMenuBar)
        self.menuSelect.setTitle(self.tr("选项"))
        self.action_sets = QAction(self.tr("设置"), self.menuSelect)
        self.action_sets.setShortcut("Ctrl+I")
        self.action_restart = QAction(self.tr("重启"), self.menuSelect)
        self.action_restart.setShortcut("Ctrl+R")
        self.action_restart.setToolTip(self.tr("重启程序，输入内容与设置会保留。"))
        self.action_exit = QAction(self.tr("退出"), self.menuSelect)
        self.menuSelect.addAction(self.action_sets)
        self.menuSelect.addAction(self.action_restart)
        self.menuSelect.addAction(self.action_exit)

        self.menuTool = QMenu(self.mainMenuBar)
        self.menuTool.setTitle(self.tr("工具"))
        self.action_log = QAction(self.tr("查看日志"), self.menuTool)
        self.action_log.setShortcut("Ctrl+J")
        self.action_topdf = QAction(self.tr("docx转pdf"), self.menuTool)
        self.action_topdf.setShortcut("Ctrl+T")
        self.action_wordreplace = QAction(self.tr("word替换"), self)
        self.action_wordreplace.setShortcut("Ctrl+G")
        self.menuTool.addAction(self.action_log)
        self.menuTool.addAction(self.action_topdf)
        self.menuTool.addAction(self.action_wordreplace)

        self.menuHelp = QMenu(self.mainMenuBar)
        self.menuHelp.setTitle(self.tr("帮助"))
        self.action_doc = QAction(self.tr("使用文档"), self.menuHelp)
        self.action_about = QAction(self.tr("关于"), self.menuHelp)
        self.menuHelp.addAction(self.action_doc)
        self.menuHelp.addAction(self.action_about)

        self.mainMenuBar.addMenu(self.menuSelect)
        self.mainMenuBar.addMenu(self.menuTool)
        self.mainMenuBar.addMenu(self.menuHelp)
        self.setMenuBar(self.mainMenuBar)


if __name__ == "__main__":
    app = QApplication()
    window = MainWindow()
    window.show()
    app.exec()
