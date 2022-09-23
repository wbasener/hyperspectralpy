from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *



class imageViewerLinker(QDialog):
    linkViewers = pyqtSignal(list)

    def __init__(self, key=None, settings=None, imageViewerDict = None, linked_keys=[], parent = None):
        super(imageViewerLinker, self).__init__(parent)
        self.setWindowTitle("Link Image Viewers")
        self.setGeometry(150, 350, 1000, 500)
        self.key = key
        self.imageViewerDict=imageViewerDict
        self.viewerKeyList = list(self.imageViewerDict.keys())
        self.selected_num_columns = None
        self.selected_num_rows = None
        self.linked_keys = linked_keys

        # create a table with image viewers
        self.table_view = QTableWidget()
        self.table_view.setRowCount(len(imageViewerDict))
        self.table_view.setColumnCount(3)
        self.table_view.setHorizontalHeaderLabels(['Select Image Viewers','Num Rows','Num Cols'])
        self.table_view.horizontalHeader().setStretchLastSection(True)  # stretch last column
        self.table_view.verticalHeader().hide() # hide the vertical headers
        self.add_data_to_table()
        self.table_view.itemClicked.connect(self.handleItemClicked)

        self.button_ok = QPushButton('OK', self)
        self.button_ok.clicked.connect(self.ok)
        self.button_cancel = QPushButton('Cancel', self)
        self.button_cancel.clicked.connect(self.cancel)

        # create the layout
        vbox = QVBoxLayout()
        vbox.addWidget(self.table_view)
        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self.button_ok)
        hbox.addWidget(self.button_cancel)
        vbox.addLayout(hbox)
        self.setLayout(vbox)

    def add_data_to_table(self):
        idx = 0
        for key in self.viewerKeyList:

            # add a checkbox in the first column
            chkBoxItem = QTableWidgetItem('[%d] %s'%(key,self.imageViewerDict[key].getFname()))
            chkBoxItem.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled )
            if key in self.linked_keys:
                chkBoxItem.setCheckState(Qt.Checked)
                self.selected_num_rows = self.imageViewerDict[key].getNumRows()
                self.selected_num_columns = self.imageViewerDict[key].getNumCols()
            else:
                chkBoxItem.setCheckState(Qt.Unchecked)
            self.table_view.setItem(idx, 0, chkBoxItem)

            # add the nRows and nCols data
            item = QTableWidgetItem(str(self.imageViewerDict[key].getNumRows()))
            item.setFlags(Qt.ItemIsEnabled)
            self.table_view.setItem(idx, 1, item)
            item = QTableWidgetItem(str(self.imageViewerDict[key].getNumCols()))
            item.setFlags(Qt.ItemIsEnabled)
            self.table_view.setItem(idx, 2, item)

            # increment the index
            idx = idx + 1

        # some basic formating to teh table
        self.table_view.setFocusPolicy(Qt.NoFocus)
        self.table_view.resizeColumnsToContents()

    def handleItemClicked(self, item):

        # check that the clicked item is in the first column
        if item.column() > 0:
            return

        if item.checkState() == Qt.Checked:
            nRows_clicked = int(self.table_view.item(item.row(), 1).text())
            nCols_clicked = int(self.table_view.item(item.row(), 2).text())

            if self.selected_num_rows == None:
                self.selected_num_rows = nRows_clicked
                self.selected_num_columns = nCols_clicked
                return

            if ((nRows_clicked != self.selected_num_rows) or
                (nCols_clicked != self.selected_num_columns)):
                self.table_view.item(item.row(), 0).setCheckState(Qt.Unchecked)

        else:
            # set the selected_num_rows and selected_num_columns to None if no rows are selected
            checked_rows = []
            for row_idx in range(self.table_view.rowCount()):
                if self.table_view.item(row_idx, 0).checkState() == Qt.Checked:
                    checked_rows.append(row_idx)

            if len(checked_rows) == 0:
                self.selected_num_rows = None
                self.selected_num_columns = None

    def ok(self):
        # determine t
        self.linked_keys = []
        for row_idx in range(self.table_view.rowCount()):
            if self.table_view.item(row_idx, 0).checkState() == Qt.Checked:
                self.linked_keys.append(self.viewerKeyList[row_idx])
        self.accept()

    def cancel(self):
        self.linked_keys = []
        self.accept()