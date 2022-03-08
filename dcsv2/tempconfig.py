# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'tempiconfig.ui'
#
# Created: Wed Feb 04 16:44:25 2015
#      by: PyQt4 UI code generator 4.10.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_iconfig_dialog(object):
    def setupUi(self, iconfig_dialog):
        iconfig_dialog.setObjectName(_fromUtf8("iconfig_dialog"))
        iconfig_dialog.resize(400, 125)
        iconfig_dialog.setMinimumSize(QtCore.QSize(400, 125))
        iconfig_dialog.setMaximumSize(QtCore.QSize(400, 125))
        iconfig_dialog.setSizeGripEnabled(False)
        self.verticalLayoutWidget = QtGui.QWidget(iconfig_dialog)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(10, 10, 381, 101))
        self.verticalLayoutWidget.setObjectName(_fromUtf8("verticalLayoutWidget"))
        self.verticalLayout = QtGui.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setMargin(0)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.label = QtGui.QLabel(self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label.setFont(font)
        self.label.setObjectName(_fromUtf8("label"))
        self.verticalLayout.addWidget(self.label)
        self.comboBox = QtGui.QComboBox(self.verticalLayoutWidget)
        self.comboBox.setObjectName(_fromUtf8("comboBox"))
        self.verticalLayout.addWidget(self.comboBox)
        self.buttonBox = QtGui.QDialogButtonBox(self.verticalLayoutWidget)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(iconfig_dialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), iconfig_dialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), iconfig_dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(iconfig_dialog)

    def retranslateUi(self, iconfig_dialog):
        iconfig_dialog.setWindowTitle(_translate("iconfig_dialog", "Initial Configuration", None))
        self.label.setText(_translate("iconfig_dialog", "Connected USB Boards:", None))

