# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file '1.ui'
##
## Created by: Qt User Interface Compiler version 6.6.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMainWindow,
    QMenu, QMenuBar, QPushButton, QSizePolicy,
    QStatusBar, QTextEdit, QVBoxLayout, QWidget)
import gui.res_rc as res_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(703, 333)
        MainWindow.setMinimumSize(QSize(600, 0))
        icon = QIcon()
        icon.addFile(u":/emipdf/acbel -1.jpg", QSize(), QIcon.Normal, QIcon.Off)
        MainWindow.setWindowIcon(icon)
        MainWindow.setStyleSheet(u"QAction { font-size: 12px; }")
        self.actionsetting = QAction(MainWindow)
        self.actionsetting.setObjectName(u"actionsetting")
        self.actionhelpdoc = QAction(MainWindow)
        self.actionhelpdoc.setObjectName(u"actionhelpdoc")
        self.actionabout = QAction(MainWindow)
        self.actionabout.setObjectName(u"actionabout")
        self.actionabout.setMenuRole(QAction.AboutRole)
        self.actiondocx2pdf = QAction(MainWindow)
        self.actiondocx2pdf.setObjectName(u"actiondocx2pdf")
        self.actionlog = QAction(MainWindow)
        self.actionlog.setObjectName(u"actionlog")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout_2 = QHBoxLayout(self.centralwidget)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.widget = QWidget(self.centralwidget)
        self.widget.setObjectName(u"widget")
        self.widget.setStyleSheet(u"")
        self.verticalLayout = QVBoxLayout(self.widget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.widget_input = QWidget(self.widget)
        self.widget_input.setObjectName(u"widget_input")
        self.widget_input.setMinimumSize(QSize(0, 200))
        self.widget_input.setMaximumSize(QSize(650, 200))
        font = QFont()
        font.setFamilies([u"Microsoft YaHei"])
        self.widget_input.setFont(font)
        self.widget_input.setLayoutDirection(Qt.LeftToRight)
        self.widget_input.setStyleSheet(u"QLabel { font-size: 15px; }")
        self.label_modelName = QLabel(self.widget_input)
        self.label_modelName.setObjectName(u"label_modelName")
        self.label_modelName.setGeometry(QRect(20, 80, 120, 41))
        self.label_modelName.setStyleSheet(u"")
        self.label_modelName.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self.label_loadQTY = QLabel(self.widget_input)
        self.label_loadQTY.setObjectName(u"label_loadQTY")
        self.label_loadQTY.setGeometry(QRect(20, 140, 120, 41))
        self.label_loadQTY.setStyleSheet(u"")
        self.label_loadQTY.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self.label_tempFile = QLabel(self.widget_input)
        self.label_tempFile.setObjectName(u"label_tempFile")
        self.label_tempFile.setGeometry(QRect(20, 20, 120, 41))
        self.label_tempFile.setStyleSheet(u"")
        self.label_tempFile.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self.textEdit_name = QTextEdit(self.widget_input)
        self.textEdit_name.setObjectName(u"textEdit_name")
        self.textEdit_name.setGeometry(QRect(150, 80, 341, 41))
        self.textEdit_name.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.textEdit_name.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.textEdit_name.setLineWrapMode(QTextEdit.NoWrap)
        self.textEdit_name.setOverwriteMode(True)
        self.textEdit_tempFile = QTextEdit(self.widget_input)
        self.textEdit_tempFile.setObjectName(u"textEdit_tempFile")
        self.textEdit_tempFile.setGeometry(QRect(150, 20, 341, 41))
        self.textEdit_tempFile.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.textEdit_tempFile.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.textEdit_tempFile.setLineWrapMode(QTextEdit.NoWrap)
        self.textEdit_tempFile.setOverwriteMode(True)
        self.textEdit_loadQTY = QTextEdit(self.widget_input)
        self.textEdit_loadQTY.setObjectName(u"textEdit_loadQTY")
        self.textEdit_loadQTY.setGeometry(QRect(150, 140, 421, 41))
        self.textEdit_loadQTY.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.textEdit_loadQTY.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.textEdit_loadQTY.setLineWrapMode(QTextEdit.WidgetWidth)
        self.btn_pathName = QPushButton(self.widget_input)
        self.btn_pathName.setObjectName(u"btn_pathName")
        self.btn_pathName.setGeometry(QRect(500, 80, 71, 41))
        self.btn_pathTemp = QPushButton(self.widget_input)
        self.btn_pathTemp.setObjectName(u"btn_pathTemp")
        self.btn_pathTemp.setGeometry(QRect(500, 20, 71, 41))

        self.verticalLayout.addWidget(self.widget_input)

        self.widget_button = QWidget(self.widget)
        self.widget_button.setObjectName(u"widget_button")
        self.widget_button.setMinimumSize(QSize(0, 50))
        self.widget_button.setMaximumSize(QSize(16777215, 100))
        self.horizontalLayout = QHBoxLayout(self.widget_button)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.btn_deal = QPushButton(self.widget_button)
        self.btn_deal.setObjectName(u"btn_deal")
        self.btn_deal.setMinimumSize(QSize(90, 30))
        self.btn_deal.setMaximumSize(QSize(75, 24))

        self.horizontalLayout.addWidget(self.btn_deal)

        self.btn_exit = QPushButton(self.widget_button)
        self.btn_exit.setObjectName(u"btn_exit")
        self.btn_exit.setMinimumSize(QSize(90, 30))
        self.btn_exit.setMaximumSize(QSize(75, 24))

        self.horizontalLayout.addWidget(self.btn_exit)


        self.verticalLayout.addWidget(self.widget_button)


        self.horizontalLayout_2.addWidget(self.widget)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 703, 21))
        self.menu_1 = QMenu(self.menubar)
        self.menu_1.setObjectName(u"menu_1")
        self.menu_3 = QMenu(self.menubar)
        self.menu_3.setObjectName(u"menu_3")
        self.menu_2 = QMenu(self.menubar)
        self.menu_2.setObjectName(u"menu_2")
        MainWindow.setMenuBar(self.menubar)
        self.statusBar_main = QStatusBar(MainWindow)
        self.statusBar_main.setObjectName(u"statusBar_main")
        MainWindow.setStatusBar(self.statusBar_main)

        self.menubar.addAction(self.menu_1.menuAction())
        self.menubar.addAction(self.menu_2.menuAction())
        self.menubar.addAction(self.menu_3.menuAction())
        self.menu_1.addAction(self.actionsetting)
        self.menu_3.addAction(self.actionhelpdoc)
        self.menu_3.addAction(self.actionabout)
        self.menu_2.addAction(self.actionlog)
        self.menu_2.addAction(self.actiondocx2pdf)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"EMI-\u6570\u636e\u5904\u7406", None))
        self.actionsetting.setText(QCoreApplication.translate("MainWindow", u"\u8bbe\u7f6e", None))
        self.actionhelpdoc.setText(QCoreApplication.translate("MainWindow", u"\u5e2e\u52a9\u6587\u6863", None))
        self.actionabout.setText(QCoreApplication.translate("MainWindow", u"\u5173\u4e8e", None))
        self.actiondocx2pdf.setText(QCoreApplication.translate("MainWindow", u"docx\u8f6cpdf", None))
#if QT_CONFIG(tooltip)
        self.actiondocx2pdf.setToolTip(QCoreApplication.translate("MainWindow", u"docx\u8f6cpdf", None))
#endif // QT_CONFIG(tooltip)
        self.actionlog.setText(QCoreApplication.translate("MainWindow", u"\u67e5\u770b\u65e5\u5fd7", None))
        self.label_modelName.setText(QCoreApplication.translate("MainWindow", u"\u673a\u79cd\u6570\u636e\u8def\u5f84\uff1a", None))
        self.label_loadQTY.setText(QCoreApplication.translate("MainWindow", u"\u8d1f\u8f7d\u6570\u91cf\uff1a", None))
        self.label_tempFile.setText(QCoreApplication.translate("MainWindow", u"\u6a21\u677f(\u53ef\u9009)\uff1a", None))
#if QT_CONFIG(tooltip)
        self.textEdit_name.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>\u586b\u5199\u673a\u79cd\u6570\u636e\u6587\u4ef6\u5939\u8def\u5f84</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.textEdit_name.setStatusTip(QCoreApplication.translate("MainWindow", u"\u8bf7\u586b\u5165\u6216\u9009\u62e9\u673a\u79cd\u6570\u636e\u6587\u4ef6\u5939\u6240\u5728\u8def\u5f84", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.textEdit_name.setWhatsThis(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>\u586b\u5199\u673a\u79cd\u6570\u636e\u6587\u4ef6\u5939\u8def\u5f84</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(tooltip)
        self.textEdit_tempFile.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>\u81ea\u5b9a\u4e49\u6a21\u677f\u6587\u4ef6\u8def\u5f84\uff0c\u7559\u7a7a\u5219\u4f7f\u7528\u9ed8\u8ba4\u6a21\u677f</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.textEdit_tempFile.setStatusTip(QCoreApplication.translate("MainWindow", u"\u8bf7\u586b\u5165\u6216\u9009\u62e9\u6a21\u677f\u8def\u5f84", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.textEdit_tempFile.setWhatsThis(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>\u81ea\u5b9a\u4e49\u6a21\u677f\u6587\u4ef6\u8def\u5f84\uff0c\u7559\u7a7a\u5219\u4f7f\u7528\u9ed8\u8ba4\u6a21\u677f</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(tooltip)
        self.textEdit_loadQTY.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>\u7a0b\u5e8f\u4f9d\u636e\u6b64\u9879\u9009\u62e9\u5bf9\u5e94\u9ed8\u8ba4\u6a21\u677f\uff0c\u5982\u679c\u81ea\u5b9a\u4e49\u6a21\u677f\u5219\u8be5\u9879\u65e0\u6548</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(whatsthis)
        self.textEdit_loadQTY.setWhatsThis(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>\u7a0b\u5e8f\u4f9d\u636e\u6b64\u9879\u9009\u62e9\u5bf9\u5e94\u9ed8\u8ba4\u6a21\u677f\uff0c\u5982\u679c\u81ea\u5b9a\u4e49\u6a21\u677f\u5219\u8be5\u9879\u65e0\u6548</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.btn_pathName.setText(QCoreApplication.translate("MainWindow", u"\u6d4f \u89c8", None))
        self.btn_pathTemp.setText(QCoreApplication.translate("MainWindow", u"\u6d4f \u89c8", None))
        self.btn_deal.setText(QCoreApplication.translate("MainWindow", u"\u5f00\u59cb\u5904\u7406", None))
        self.btn_exit.setText(QCoreApplication.translate("MainWindow", u"\u9000 \u51fa", None))
        self.menu_1.setTitle(QCoreApplication.translate("MainWindow", u"\u9009\u9879", None))
        self.menu_3.setTitle(QCoreApplication.translate("MainWindow", u"\u5e2e\u52a9", None))
        self.menu_2.setTitle(QCoreApplication.translate("MainWindow", u"\u5de5\u5177", None))
    # retranslateUi

