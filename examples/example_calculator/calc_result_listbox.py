from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *


class ResultListbox(QListWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        # init
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragEnabled(False)

    def sizeHint(self):
        # used for the initial size of the drag boxes
        return QSize(150, 75)

    def addResult(self, list):
        self.clear()
        for result in list:
            if result:
                self.addMyItem(result)

    def addMyItem(self, name):
        item = QListWidgetItem(name, self)
        item.setFlags(Qt.NoItemFlags)
        # item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
