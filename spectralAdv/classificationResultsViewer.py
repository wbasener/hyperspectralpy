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


class classAnalysisResultsGUI(QMainWindow):
    def __init__(self, parent=None, settings = None):
        super(classAnalysisResultsGUI, self).__init__(parent)
        self.title = 'Machine Learning Classification Metrics'
        self.left = 50
        self.top = 50
        self.width = 800
        self.height = 300
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.learners = parent.learners
        self.validation = parent.validation
        self.class_names = parent.class_names
        self.keys = list(self.learners.keys())
        self.table_widget = MyTableWidget(self)
        self.setCentralWidget(self.table_widget)
        self.show()

class MyTableWidget(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.class_names = parent.class_names
        self.learners = parent.learners
        self.numClasses = len(self.class_names)
        self.numLearners = len(self.learners)
        # Initialize tab screen
        self.tabs = QTabWidget()
        # Add tabs
        tab_summary= QWidget()
        self.tabs.addTab(tab_summary, "Accuracy Metrics")
        tab_summary.layout = QVBoxLayout(self)
        table_summary = QTableWidget()
        table_summary.setSelectionMode(QAbstractItemView.SingleSelection)
        table_summary.setRowCount(self.numLearners)
        table_summary.setColumnCount(2)
        table_summary.setHorizontalHeaderLabels(['Classifier','Accuracy'])
        table_summary.verticalHeader().setVisible(False)
        row_index = 0
        for learnerMethod in self.learners.keys():
            item = QTableWidgetItem(learnerMethod)
            table_summary.setItem(row_index, 0, item)
            val = parent.validation[learnerMethod]['accuracy']
            item = QTableWidgetItem(str(val))
            table_summary.setItem(row_index, 1, item)
            row_index = row_index + 1
        table_summary.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table_summary.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        tab_summary.layout.addWidget(table_summary)
        tab_summary.setLayout(tab_summary.layout)
        for learnerMethod in self.learners.keys():
            tab_learner = QWidget()
            self.tabs.addTab(tab_learner, learnerMethod)
            tab_learner.layout = QVBoxLayout(self)
            table_learner = QTableWidget()
            table_learner.setSelectionMode(QAbstractItemView.SingleSelection)
            table_learner.setRowCount(self.numClasses)
            table_learner.setColumnCount(self.numClasses)
            table_learner.setHorizontalHeaderLabels(self.class_names)
            table_learner.setVerticalHeaderLabels(self.class_names)
            for r in range(self.numClasses):
                for c in range(self.numClasses):
                    val = parent.validation[learnerMethod]['confusionMatrix'][r,c]
                    item = QTableWidgetItem(str(val))
                    item.setBackground(QColor(int(val*255), int(255-val*255), 0))
                    table_learner.setItem(r, c, item)
            for c in range(self.numClasses):
                table_learner.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
            tab_learner.layout.addWidget(table_learner)
            tab_learner.setLayout(tab_learner.layout)
        self.tabs.resize(300, 200)

        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

def temp():

        if ('LDA' in  parent.keys):
            self.tabLDA = QWidget()
            self.tabs.addTab(self.tabLDA, "LDA")
            self.tabLDA.layout = QVBoxLayout(self)
            self.LDA_table = QTableWidget()
            self.LDA_table.setSelectionMode(QAbstractItemView.SingleSelection)
            self.LDA_table.setRowCount(self.numClasses)
            self.LDA_table.setColumnCount(self.numClasses)
            self.LDA_table.setHorizontalHeaderLabels(self.class_names)
            self.LDA_table.setVerticalHeaderLabels(self.class_names)
            for c in range(self.numClasses):
                self.LDA_table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
                for r in range(self.numClasses):
                    val = parent.validation['LDA']['confusionMatrix'][r,c]
                    item = QTableWidgetItem(str(val))
                    item.setBackground(QColor(val*255, 255-val*255, 0))
                    self.LDA_table.setItem(r, c, item)
            self.tabLDA.layout.addWidget(self.LDA_table)
            self.tabLDA.setLayout(self.tabLDA.layout)
        if ('QDA' in  parent.keys):
            self.tabQDA = QWidget()
            self.tabs.addTab(self.tabQDA, "QDA")
            self.tabQDA.layout = QVBoxLayout(self)
            self.QDA_table = QTableWidget()
            self.QDA_table.setSelectionMode(QAbstractItemView.SingleSelection)
            self.QDA_table.setRowCount(self.numClasses)
            self.QDA_table.setColumnCount(self.numClasses)
            self.QDA_table.setHorizontalHeaderLabels(self.class_names)
            self.QDA_table.setVerticalHeaderLabels(self.class_names)
            for c in range(self.numClasses):
                self.LDA_table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
                for r in range(self.numClasses):
                    val = parent.validation['QDA']['confusionMatrix'][r,c]
                    item = QTableWidgetItem(str(val))
                    item.setBackground(QColor(val*255, 255-val*255, 0))
                    self.QDA_table.setItem(r, c, item)
            self.tabQDA.layout.addWidget(self.QDA_table)
            self.tabQDA.setLayout(self.tabQDA.layout)
        if ('RF' in  parent.keys):
            self.tabRF = QWidget()
            self.tabs.addTab(self.tabRF, "Random Forest")
            self.tabRF.layout = QVBoxLayout(self)
            self.RF_table = QTableWidget()
            self.RF_table.setSelectionMode(QAbstractItemView.SingleSelection)
            self.RF_table.setRowCount(self.numClasses)
            self.RF_table.setColumnCount(self.numClasses)
            self.RF_table.setHorizontalHeaderLabels(self.class_names)
            self.RF_table.setVerticalHeaderLabels(self.class_names)
            for c in range(self.numClasses):
                self.LDA_table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
                for r in range(self.numClasses):
                    val = parent.validation['RF']['confusionMatrix'][r,c]
                    item = QTableWidgetItem(str(val))
                    item.setBackground(QColor(val*255, 255-val*255, 0))
                    self.RF_table.setItem(r, c, item)
            self.tabRF.layout.addWidget(self.RF_table)
            self.tabRF.setLayout(self.tabRF.layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    #app = QApplication.instance() # when running in Canopy
    form = classificationResultsViewer()
    form.show()
    app.exec_()