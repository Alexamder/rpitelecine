# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'telecineui.ui'
#
# Created: Wed Mar 18 16:54:21 2015
#      by: pyside-uic 0.2.13 running on PySide 1.1.1
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_TelecinePreview(object):
    def setupUi(self, TelecinePreview):
        TelecinePreview.setObjectName("TelecinePreview")
        TelecinePreview.resize(897, 660)
        self.centralwidget = QtGui.QWidget(TelecinePreview)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.tabs = QtGui.QTabWidget(self.centralwidget)
        self.tabs.setObjectName("tabs")
        self.tabRun = QtGui.QWidget()
        self.tabRun.setObjectName("tabRun")
        self.tabs.addTab(self.tabRun, "")
        self.gridLayout.addWidget(self.tabs, 0, 0, 1, 1)
        TelecinePreview.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(TelecinePreview)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 897, 22))
        self.menubar.setObjectName("menubar")
        self.menu_File = QtGui.QMenu(self.menubar)
        self.menu_File.setObjectName("menu_File")
        TelecinePreview.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(TelecinePreview)
        self.statusbar.setObjectName("statusbar")
        TelecinePreview.setStatusBar(self.statusbar)
        self.action_Quit = QtGui.QAction(TelecinePreview)
        self.action_Quit.setShortcutContext(QtCore.Qt.WindowShortcut)
        self.action_Quit.setObjectName("action_Quit")
        self.menu_File.addAction(self.action_Quit)
        self.menubar.addAction(self.menu_File.menuAction())

        self.retranslateUi(TelecinePreview)
        self.tabs.setCurrentIndex(0)
        QtCore.QObject.connect(self.action_Quit, QtCore.SIGNAL("triggered()"), TelecinePreview.close)
        QtCore.QMetaObject.connectSlotsByName(TelecinePreview)

    def retranslateUi(self, TelecinePreview):
        TelecinePreview.setWindowTitle(QtGui.QApplication.translate("TelecinePreview", "MainWindow", None, QtGui.QApplication.UnicodeUTF8))
        self.tabs.setTabText(self.tabs.indexOf(self.tabRun), QtGui.QApplication.translate("TelecinePreview", "Run Telecine", None, QtGui.QApplication.UnicodeUTF8))
        self.menu_File.setTitle(QtGui.QApplication.translate("TelecinePreview", "&File", None, QtGui.QApplication.UnicodeUTF8))
        self.action_Quit.setText(QtGui.QApplication.translate("TelecinePreview", "&Quit", None, QtGui.QApplication.UnicodeUTF8))
        self.action_Quit.setShortcut(QtGui.QApplication.translate("TelecinePreview", "Ctrl+Q", None, QtGui.QApplication.UnicodeUTF8))

