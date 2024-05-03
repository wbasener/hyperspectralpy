from __future__ import division
import time
import sys
import os

from PyQt5 import QtGui

from . import specTools
from math import *
import matplotlib
import matplotlib.pyplot as plt
from spectral import *
from . import spectraViewer
import numpy as np
import pandas as pd
from scipy.optimize import nnls
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import *
from PyQt5.QtWidgets import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from pyqtgraph.widgets.MatplotlibWidget import *
#matplotlib.use('Qt4Agg')





class libraryViewer(QMainWindow):
    # setup signal to send copied spectrum back
    copiedSpectrum = pyqtSignal(dict)
    pasteSpectrumRequest = pyqtSignal(int)
    pasteSpectrum = pyqtSignal(dict)
    openedLibrary = pyqtSignal(dict)

    def __init__(self, settings=None, libraryDir=None, lib=None, parent=None):
        super(libraryViewer, self).__init__(parent)
        self.setWindowTitle("Library Viewer: "+os.path.basename(lib.params.filename))
        self.setGeometry(850, 450, 1000, 500)
        self.settings = settings
        self.libraryDir = libraryDir
        self.lib = lib
        self.scale = 1
        self.spectral_plot_offset = 0

        # menu bar actions
        # File menu
        selectLibraryAction = QAction("Open new library",self)
        selectLibraryAction.triggered.connect(self.open_new_library)
        saveLibraryAction = QAction("Save library as csv",self)
        saveLibraryAction.triggered.connect(self.save_as_csv)
        exitAction = QAction("Close",self)
        exitAction.triggered.connect(self.close_this)

        # Tools menu
        sortSpectraAction = QAction("Sort by Text Match",self)
        sortSpectraAction.triggered.connect(self.search_and_sort_spectra_names)

        # add the menu bar
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu("&File")
        # For now - not having ability to select new image within the viewer
        fileMenu.addAction(selectLibraryAction)
        fileMenu.addAction(saveLibraryAction)
        fileMenu.addAction(exitAction)
        toolsMenu = mainMenu.addMenu("&Tools")
        toolsMenu.addAction(sortSpectraAction)

        # list widget with list of images
        self.table_view = QTableWidget()
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.verticalHeader().setDefaultSectionSize(18)
        nCols = 3
        nRows = 0
        self.table_view.setRowCount(nRows)
        self.table_view.setColumnCount(nCols)
        self.table_view.setColumnHidden(1, True)
        self.table_view.setColumnHidden(2, True)
        self.table_view.setHorizontalHeaderLabels(['Spectra Names','Index','String Match Score'])
        self.table_view.setColumnWidth(0, 80)
        self.table_view.horizontalHeader().setStretchLastSection(True) # stretch last column
        self.table_view.verticalHeader().setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)
        self.table_view.setWordWrap(False)

        # set the layout for the central widget
        self.widget_central = QWidget()
        self.vbox = QVBoxLayout()
        self.widget_central.setLayout(self.vbox)
        self.vbox.addWidget(self.table_view)

        # set as central widget and dock widget
        self.setCentralWidget(self.widget_central)

        # SIGNALS:
        # signal when the selection is changed
        self.table_view.itemSelectionChanged.connect(self.selection_changed)

        # set the library
        self.open_library()

    def close_this(self):
        sys.exit()

    def open_library(self):
        # Get the library name
        if self.lib == None:
            lib, ok = specTools.select_library(self, prompt="Choose a library")
            if not ok:
                return
            self.lib = lib
        self.libraryDir = os.path.dirname(os.path.abspath(self.lib.params.filename))
        self.setWindowTitle("Library Viewer: "+os.path.basename(self.lib.params.filename))
        lib_dict = {'lib': self.lib}
        self.openedLibrary.emit(lib_dict)
        self.add_data_to_table()

    def open_new_library(self):
        # Get the library name
        # Get the library name
        lib, ok = specTools.select_library(self, prompt="Choose a library")
        if not ok:
            return
        self.lib = lib
        self.libraryDir = os.path.dirname(os.path.abspath(self.lib.params.filename))
        self.setWindowTitle("Library Viewer: "+os.path.basename(self.lib.params.filename))
        lib_dict = {'lib': self.lib}
        self.openedLibrary.emit(lib_dict)
        self.add_data_to_table()

    def add_data_to_table(self):

        # set up the number of rows
        nRows = len(self.lib.names)
        self.table_view.setRowCount(nRows)

        # put the spectra names in the rows
        for row_idx in range(len(self.lib.names)):
            self.table_view.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(self.lib.names[row_idx]))
            self.table_view.setItem(row_idx, 1, QtWidgets.QTableWidgetItem('%d' % row_idx))
            self.table_view.setItem(row_idx, 2, QtWidgets.QTableWidgetItem('%d' % 0))

        # resize to fit the new contents
        self.table_view.resizeRowsToContents()

    def selection_changed(self):
        indices = self.table_view.selectedIndexes()

        for index in indices:
            row = indices[0].row()
            selected_spectrum_index = int(self.table_view.item(row, 1).text())
            wl = self.lib.bands.centers
            vals = self.lib.spectra[selected_spectrum_index,:]
            name = self.lib.names[selected_spectrum_index]
            self.plotSpectrum(wl, vals, name)

    def plotSpectrum(self, wl, vals, name):

            if not hasattr(self, 'spectral_plot'):
                # This is the case if not spectral plot has been made
                # Create an empty spectral viewer gui
                self.spectral_plot = spectraViewer.specPlot(parent=self, settings=self.settings, offset=0)
                self.spectral_plot.setStyleSheet('QMainWindow{padding: 0px}')
                self.spectral_plot.copiedSpectrum.connect(self.copy_spectrum)
                self.spectral_plot.pasteSpectrumRequest.connect(self.paste_spectrum_request)
                self.pasteSpectrum.connect(self.spectral_plot.paste_spectrum)
            elif self.spectral_plot.isHidden():
                # This is the case if a spectral plot was made and then closed
                # Create an empty spectral viewer gui
                self.spectral_plot = spectraViewer.specPlot(parent=self, settings=self.settings, offset=0)
                self.spectral_plot.setStyleSheet('QMainWindow{padding: 0px;}')
                self.spectral_plot.copiedSpectrum.connect(self.copy_spectrum)
                self.spectral_plot.pasteSpectrumRequest.connect(self.paste_spectrum_request)
                self.pasteSpectrum.connect(self.spectral_plot.paste_spectrum)
            # generate the plot
            self.spectral_plot.subplot.plot(wl,vals, label=name, linewidth=1)
            if self.settings.screen_width > 3000:
                self.spectral_plot.subplot.axes.legend(fontsize=20)
            else:
                self.spectral_plot.subplot.axes.legend()
            self.spectral_plot.MPWidget.draw()

    def copy_spectrum(self, copied_spectrum):
        # emit the signal to send data back
        self.copiedSpectrum.emit(copied_spectrum)

    def paste_spectrum_request(self):
        # emit the signal to send data back
        self.pasteSpectrumRequest.emit(1)

    def paste_spectrum(self, pasted_spectrum):
        self.pasteSpectrum.emit(pasted_spectrum)

    def search_and_sort_spectra_names(self):

        nRows = self.table_view.rowCount()
        if nRows > 0:
            query, ok = QInputDialog.getText(self, "Enter words to search for", "Query words:", QLineEdit.Normal, "")
            if not ok:
                return
            self.table_view.sortItems(1, order=Qt.AscendingOrder)
            query = query.lower()
            snames = [self.table_view.item(idx,0).text().lower() for idx in range(nRows)]
            matchScores = specTools.fuzzy_string_match(query, snames)
            for row_idx in range(nRows):
                self.table_view.setItem(row_idx, 2, QtGui.QTableWidgetItem('%.3f' % matchScores[row_idx])  )
            self.table_view.sortItems(2, order=Qt.AscendingOrder)

    def save_as_csv(self):

        # create a dataframe from the spectra
        df = pd.DataFrame(np.transpose(self.lib.spectra))
        # add column nemas
        df.columns = self.lib.names
        # add the wavelengths as a column
        df['wavelength'] = self.lib.bands.centers

        # select output filename
        fname = QFileDialog.getSaveFileName(self, 'Save Spectral Library',
                                                     'lib.csv',
                                                     'CSV (*.csv)')
        if fname == '':
            return
        df.to_csv(fname,index=False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    #app = QApplication.instance() # when running in Canopy
    form = libraryViewer(libraryDir='C:\\Users\\wfbsm\\OneDrive\\Documents\\Desktop Temp\\specTools Tools\\libraries')
    form.show()
    app.exec_()