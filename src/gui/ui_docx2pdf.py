# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'docx2pdfWNXTiu.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QPushButton, QSizePolicy,
    QSpacerItem, QStatusBar, QWidget)
import gui.doc_rc

class Ui_Docx2PdfWin(object):
    def setupUi(self, Docx2PdfWin):
        if not Docx2PdfWin.objectName():
            Docx2PdfWin.setObjectName(u"Docx2PdfWin")
        Docx2PdfWin.resize(600, 160)
        icon = QIcon()
        icon.addFile(u":/logo/acbel-1.jpg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        Docx2PdfWin.setWindowIcon(icon)
        self.centralwidget = QWidget(Docx2PdfWin)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout_2 = QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.textEdit_docx = QLineEdit(self.centralwidget)
        self.textEdit_docx.setObjectName(u"textEdit_docx")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.textEdit_docx.sizePolicy().hasHeightForWidth())
        self.textEdit_docx.setSizePolicy(sizePolicy)
        self.textEdit_docx.setMinimumSize(QSize(360, 30))

        self.gridLayout.addWidget(self.textEdit_docx, 0, 1, 1, 1)

        self.btn_docxdir = QPushButton(self.centralwidget)
        self.btn_docxdir.setObjectName(u"btn_docxdir")
        self.btn_docxdir.setMinimumSize(QSize(0, 30))

        self.gridLayout.addWidget(self.btn_docxdir, 0, 2, 1, 1)

        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")
        self.label.setMinimumSize(QSize(0, 30))

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.button_docxfile = QPushButton(self.centralwidget)
        self.button_docxfile.setObjectName(u"button_docxfile")
        self.button_docxfile.setMinimumSize(QSize(0, 30))

        self.gridLayout.addWidget(self.button_docxfile, 0, 3, 1, 1)


        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.btn_docx2pdf = QPushButton(self.centralwidget)
        self.btn_docx2pdf.setObjectName(u"btn_docx2pdf")
        sizePolicy.setHeightForWidth(self.btn_docx2pdf.sizePolicy().hasHeightForWidth())
        self.btn_docx2pdf.setSizePolicy(sizePolicy)
        self.btn_docx2pdf.setMinimumSize(QSize(50, 30))

        self.horizontalLayout.addWidget(self.btn_docx2pdf)

        self.button_cancel = QPushButton(self.centralwidget)
        self.button_cancel.setObjectName(u"button_cancel")
        sizePolicy.setHeightForWidth(self.button_cancel.sizePolicy().hasHeightForWidth())
        self.button_cancel.setSizePolicy(sizePolicy)
        self.button_cancel.setMinimumSize(QSize(50, 30))

        self.horizontalLayout.addWidget(self.button_cancel)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)


        self.gridLayout_2.addLayout(self.horizontalLayout, 1, 0, 1, 1)

        Docx2PdfWin.setCentralWidget(self.centralwidget)
        self.statusBar_docx = QStatusBar(Docx2PdfWin)
        self.statusBar_docx.setObjectName(u"statusBar_docx")
        Docx2PdfWin.setStatusBar(self.statusBar_docx)

        self.retranslateUi(Docx2PdfWin)
        self.button_cancel.clicked.connect(Docx2PdfWin.close)

        QMetaObject.connectSlotsByName(Docx2PdfWin)
    # setupUi

    def retranslateUi(self, Docx2PdfWin):
        Docx2PdfWin.setWindowTitle(QCoreApplication.translate("Docx2PdfWin", u"DOCX\u8f6cPDF", None))
        self.textEdit_docx.setPlaceholderText(QCoreApplication.translate("Docx2PdfWin", u"\u8bf7\u8f93\u5165DOCX\u6587\u4ef6\u8def\u5f84\u6216\u5305\u542bDOCX\u6587\u4ef6\u7684\u6587\u4ef6\u5939\u8def\u5f84", None))
        self.btn_docxdir.setText(QCoreApplication.translate("Docx2PdfWin", u"\u9009\u62e9\u76ee\u5f55", None))
        self.label.setText(QCoreApplication.translate("Docx2PdfWin", u"\u8def\u5f84\uff1a", None))
        self.button_docxfile.setText(QCoreApplication.translate("Docx2PdfWin", u"\u9009\u62e9\u6587\u4ef6", None))
        self.btn_docx2pdf.setText(QCoreApplication.translate("Docx2PdfWin", u"\u8f6c \u6362", None))
        self.button_cancel.setText(QCoreApplication.translate("Docx2PdfWin", u"\u8fd4 \u56de", None))
    # retranslateUi

