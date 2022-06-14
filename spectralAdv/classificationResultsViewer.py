import sys
import numpy as np
from scipy.optimize import nnls
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
#from pyqtgraph.widgets.MatplotlibWidget import *


class classificationResultsViewer(QMainWindow):

    def __init__(self, settings=None, methods=None, learners=None, validation=None, plot_data=None, parent=None):
        super(classificationResultsViewer, self).__init__(parent)
        self.setWindowTitle("Image Viewer")
        self.setGeometry(150, 150, 1000, 1000)
        self.results = methods
        self.results = learners
        self.results = validation
        self.results = plot_data
        self.settings = settings


        # list widget with list of images
        self.table_view = QTableWidget()
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        nCols = 7
        nRows = 0
        self.table_view.setRowCount(nRows)
        self.table_view.setColumnCount(nCols)
        self.table_view.setHorizontalHeaderLabels(['Num Spectra','Num Bands','Scale','Wavelengths','Range: min-max','Directory'])
        self.table_view.setColumnWidth(0, 80) # num spectra
        self.table_view.setColumnWidth(1, 80) # num bands
        self.table_view.setColumnWidth(2, 80) # scale
        self.table_view.setColumnWidth(3, 150) # wavelengths
        self.table_view.setColumnWidth(4, 150) # min-max
        self.table_view.setColumnWidth(5, 80) # directory
        self.table_view.setColumnWidth(6, 80) # file_name
        self.table_view.setColumnHidden(6, True)
        self.table_view.horizontalHeader().setStretchLastSection(True) # stretch last column
        #self.table_view.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch) # stretch all columns to fit width
        self.table_view.verticalHeader().setAlternatingRowColors(True)

        # set the layout for the central widget
        self.widget_central = QWidget()
        self.vbox = QVBoxLayout()
        self.widget_central.setLayout(self.vbox)
        self.vbox.addWidget(self.table_view)

        # set as central widget and dock widget
        self.setCentralWidget(self.widget_central)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    #app = QApplication.instance() # when running in Canopy
    form = classificationResultsViewer()
    form.show()
    app.exec_()