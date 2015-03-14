# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'livePreview.ui'
#
# Created: Fri Mar 13 23:41:42 2015
#      by: pyside-uic 0.2.13 running on PySide 1.1.1
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_livePreviewForm(object):
    def setupUi(self, livePreviewForm):
        livePreviewForm.setObjectName("livePreviewForm")
        livePreviewForm.resize(702, 368)
        self.horizontalLayout = QtGui.QHBoxLayout(livePreviewForm)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.frame = QtGui.QFrame(livePreviewForm)
        self.frame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtGui.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.verticalLayout = QtGui.QVBoxLayout(self.frame)
        self.verticalLayout.setObjectName("verticalLayout")
        self.lblPreview = QtGui.QLabel(self.frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lblPreview.sizePolicy().hasHeightForWidth())
        self.lblPreview.setSizePolicy(sizePolicy)
        self.lblPreview.setMinimumSize(QtCore.QSize(400, 300))
        self.lblPreview.setFrameShape(QtGui.QFrame.NoFrame)
        self.lblPreview.setObjectName("lblPreview")
        self.verticalLayout.addWidget(self.lblPreview)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.sliderPreviewZoom = QtGui.QSlider(self.frame)
        self.sliderPreviewZoom.setMinimum(10)
        self.sliderPreviewZoom.setMaximum(40)
        self.sliderPreviewZoom.setSingleStep(1)
        self.sliderPreviewZoom.setPageStep(4)
        self.sliderPreviewZoom.setProperty("value", 10)
        self.sliderPreviewZoom.setTracking(True)
        self.sliderPreviewZoom.setOrientation(QtCore.Qt.Horizontal)
        self.sliderPreviewZoom.setTickPosition(QtGui.QSlider.NoTicks)
        self.sliderPreviewZoom.setObjectName("sliderPreviewZoom")
        self.horizontalLayout_2.addWidget(self.sliderPreviewZoom)
        self.btnPreviewL = QtGui.QToolButton(self.frame)
        self.btnPreviewL.setObjectName("btnPreviewL")
        self.horizontalLayout_2.addWidget(self.btnPreviewL)
        self.btnPreviewU = QtGui.QToolButton(self.frame)
        self.btnPreviewU.setObjectName("btnPreviewU")
        self.horizontalLayout_2.addWidget(self.btnPreviewU)
        self.btnPreviewD = QtGui.QToolButton(self.frame)
        self.btnPreviewD.setObjectName("btnPreviewD")
        self.horizontalLayout_2.addWidget(self.btnPreviewD)
        self.btnPreviewR = QtGui.QToolButton(self.frame)
        self.btnPreviewR.setObjectName("btnPreviewR")
        self.horizontalLayout_2.addWidget(self.btnPreviewR)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.horizontalLayout.addWidget(self.frame)
        self.framePreviewTools = QtGui.QFrame(livePreviewForm)
        self.framePreviewTools.setMinimumSize(QtCore.QSize(256, 0))
        self.framePreviewTools.setMaximumSize(QtCore.QSize(256, 16777215))
        self.framePreviewTools.setFrameShape(QtGui.QFrame.NoFrame)
        self.framePreviewTools.setFrameShadow(QtGui.QFrame.Plain)
        self.framePreviewTools.setLineWidth(0)
        self.framePreviewTools.setObjectName("framePreviewTools")
        self.verticalLayout_9 = QtGui.QVBoxLayout(self.framePreviewTools)
        self.verticalLayout_9.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_9.setObjectName("verticalLayout_9")
        self.btnAutoExpose = QtGui.QPushButton(self.framePreviewTools)
        self.btnAutoExpose.setObjectName("btnAutoExpose")
        self.verticalLayout_9.addWidget(self.btnAutoExpose)
        self.lblAWBMode = QtGui.QLabel(self.framePreviewTools)
        self.lblAWBMode.setObjectName("lblAWBMode")
        self.verticalLayout_9.addWidget(self.lblAWBMode)
        self.cmbAWBMode = QtGui.QComboBox(self.framePreviewTools)
        self.cmbAWBMode.setObjectName("cmbAWBMode")
        self.verticalLayout_9.addWidget(self.cmbAWBMode)
        self.lblExpInfo = QtGui.QLabel(self.framePreviewTools)
        self.lblExpInfo.setAlignment(QtCore.Qt.AlignCenter)
        self.lblExpInfo.setWordWrap(True)
        self.lblExpInfo.setObjectName("lblExpInfo")
        self.verticalLayout_9.addWidget(self.lblExpInfo)
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_9.addItem(spacerItem1)
        self.btnPreviewSave = QtGui.QPushButton(self.framePreviewTools)
        self.btnPreviewSave.setObjectName("btnPreviewSave")
        self.verticalLayout_9.addWidget(self.btnPreviewSave)
        self.horizontalLayout.addWidget(self.framePreviewTools)

        self.retranslateUi(livePreviewForm)
        QtCore.QMetaObject.connectSlotsByName(livePreviewForm)

    def retranslateUi(self, livePreviewForm):
        livePreviewForm.setWindowTitle(QtGui.QApplication.translate("livePreviewForm", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.lblPreview.setText(QtGui.QApplication.translate("livePreviewForm", "<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:600;\">Note</span><span style=\" font-size:12pt;\">: Preview only visible on </span></p><p align=\"center\"><span style=\" font-size:12pt;\">Raspberry Pi HDMI display</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.sliderPreviewZoom.setToolTip(QtGui.QApplication.translate("livePreviewForm", "Zoom preview", None, QtGui.QApplication.UnicodeUTF8))
        self.sliderPreviewZoom.setAccessibleName(QtGui.QApplication.translate("livePreviewForm", "Zoom Preview", None, QtGui.QApplication.UnicodeUTF8))
        self.btnPreviewL.setToolTip(QtGui.QApplication.translate("livePreviewForm", "Preview left", None, QtGui.QApplication.UnicodeUTF8))
        self.btnPreviewL.setText(QtGui.QApplication.translate("livePreviewForm", "←", None, QtGui.QApplication.UnicodeUTF8))
        self.btnPreviewU.setToolTip(QtGui.QApplication.translate("livePreviewForm", "Preview up", None, QtGui.QApplication.UnicodeUTF8))
        self.btnPreviewU.setText(QtGui.QApplication.translate("livePreviewForm", "↑", None, QtGui.QApplication.UnicodeUTF8))
        self.btnPreviewD.setToolTip(QtGui.QApplication.translate("livePreviewForm", "Preview down", None, QtGui.QApplication.UnicodeUTF8))
        self.btnPreviewD.setText(QtGui.QApplication.translate("livePreviewForm", "↓", None, QtGui.QApplication.UnicodeUTF8))
        self.btnPreviewR.setToolTip(QtGui.QApplication.translate("livePreviewForm", "Preview right", None, QtGui.QApplication.UnicodeUTF8))
        self.btnPreviewR.setText(QtGui.QApplication.translate("livePreviewForm", "→", None, QtGui.QApplication.UnicodeUTF8))
        self.btnAutoExpose.setText(QtGui.QApplication.translate("livePreviewForm", "Auto Exposure", None, QtGui.QApplication.UnicodeUTF8))
        self.lblAWBMode.setText(QtGui.QApplication.translate("livePreviewForm", "White Balance mode", None, QtGui.QApplication.UnicodeUTF8))
        self.lblExpInfo.setText(QtGui.QApplication.translate("livePreviewForm", "<html><head/><body><p>Exposure info</p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.btnPreviewSave.setText(QtGui.QApplication.translate("livePreviewForm", "Set as default exposure", None, QtGui.QApplication.UnicodeUTF8))

