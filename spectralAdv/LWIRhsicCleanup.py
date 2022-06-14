from os import listdir
from os import remove
from os import path
from os.path import join
from sys import argv
from sys import exit
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class LWIRhsicCleanup(QMainWindow):
    def __init__(self, parent=None, settings=None):
        super(LWIRhsicCleanup, self).__init__()
        self.setWindowTitle("LWIR hsic file cleanup tool")
        self.setWindowIcon(QIcon('files_icon.ico'))
        self.setGeometry(150, 150, 700, 500)

        # menu bar actions
        # File menu
        hsicCleanupAction = QAction("Cleanup hsic directory", self)
        hsicCleanupAction.triggered.connect(self.hsic_cleanup)
        exitAction = QAction("Close", self)
        exitAction.triggered.connect(self.close_this)

        # add the menu bar
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu("&File")
        # For now - not having ability to select new image within the viewer
        fileMenu.addAction(hsicCleanupAction)
        fileMenu.addAction(exitAction)


        # list widget with list of files
        self.table_view = QTableWidget()
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.verticalHeader().setDefaultSectionSize(18)
        nCols = 1
        nRows = 0
        self.table_view.setRowCount(nRows)
        self.table_view.setColumnCount(nCols)
        self.table_view.setHorizontalHeaderLabels(['WARNING: This tool will remove many files from your hsic directory.  Use with caution.'])
        self.table_view.setColumnWidth(0, 80) # num spectra
        self.table_view.horizontalHeader().setStretchLastSection(True) # stretch last column
        self.table_view.verticalHeader().setAlternatingRowColors(True)

        # set the layout for the central widget
        self.widget_central = QWidget()
        self.vbox = QVBoxLayout()
        self.widget_central.setLayout(self.vbox)
        self.vbox.addWidget(self.table_view)

        # set as central widget and dock widget
        self.setCentralWidget(self.widget_central)

    def close_this(self):
        self.close()

    def hsic_cleanup(self):

        # set parameters
        nRows = 0

        LWIR_dir = QFileDialog.getExistingDirectory(self, 'Choose the LWIRx directory.')
        if len(LWIR_dir)==0:
            return
        LWIR_dir = path.abspath(LWIR_dir)
        # only searching int he hsic sub-directory
        LWIR_dir = join(LWIR_dir,'hsic')

        # list of terms to flag for non-deletion
        fname, ok = QFileDialog.getOpenFileName(self, 'Choose text file with numbers indicating files that you want to keep.')
        if not ok:
            return


        # get the list of all files in teh desired directory
        files = listdir(LWIR_dir)

        # read the file keep indicators
        with open(fname) as f:
            keep_indicator_strings = f.readlines()
        # remove whitespace characters like `\n` at the end of each line
        keep_indicator_strings = [x.strip() for x in keep_indicator_strings]


        self.table_view.setHorizontalHeaderLabels(['Removed File Names'])
        for file in files:
            keep = False
            for keep_string in keep_indicator_strings:
                if file.find(keep_string) > 0:
                    keep = True
            if not keep:

                # add a row to the table
                nRows = nRows + 1
                self.table_view.setRowCount(nRows)

                # put the spectra names in the new row
                self.table_view.setItem(nRows-1, 0, QTableWidgetItem(file))

                # delete the file
                remove(join(LWIR_dir,file))



if __name__ == "__main__":
    app = QApplication(argv)
    form = LWIRhsicCleanup()
    form.show()
    app.exec_()