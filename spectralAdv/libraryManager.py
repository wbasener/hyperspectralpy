from __future__ import division
import time
import sys
import os
from . import specTools
from math import *
import matplotlib
import matplotlib.pyplot as plt 
#matplotlib.use('Qt4Agg')
from spectral import *
import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
#from pyqtgraph.widgets.MatplotlibWidget import *


class MergeOptionsDlg(QDialog):

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)

        # Set up widgets

        # Combobox to set extend data method
        extendLabel = QLabel("&Extend Data By:")
        self.extendComboBox = QComboBox()
        extendLabel.setBuddy(self.extendComboBox)
        self.extendComboBox.addItems(["Extend with 0","Extend with 0.000001","Extend with NaN","Clip to common values"])

        # Combobox to set units
        unitsLabel = QLabel("&Wavelength Units:")
        self.unitsComboBox = QComboBox()
        unitsLabel.setBuddy(self.unitsComboBox)
        self.unitsComboBox.addItems(["Micrometers","Nanometers"])

        # Buttons to accept or reject Dialog contents
        okButton = QPushButton("&OK")
        cancelButton = QPushButton("Cancel")

        # Set layout
        # Buttons (note addstretch is sort of like adding an additional widget:
        # depending on when you add it, it has different effects)
        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch()  # pushes buttons to the right (adds blank space to left)
        buttonLayout.addWidget(okButton)
        # buttonLayout.addStretch() #pushes buttons to the side (adds blank space in middle)
        buttonLayout.addWidget(cancelButton)
        # buttonLayout.addStretch() #pushes buttons to the left (adds blank space to right)

        # Widgets (including buttons) lay out in grid
        layout = QGridLayout()
        layout.addWidget(extendLabel, 0, 0)
        layout.addWidget(self.extendComboBox, 0, 1, 1, 2)
        layout.addWidget(unitsLabel, 1, 0)
        layout.addWidget(self.unitsComboBox, 1, 1, 1, 2)  # takes up 1 row, 2 columns
        layout.addLayout(buttonLayout, 2, 0, 1, 3)  # takes up 1 row, 3 columns
        self.setLayout(layout)
        self.setWindowTitle("Merge Options")

        # Connect buttons to slots
        # Note that accept() and reject() are built-in methods of the dialog
        # that give control back to the caller
        okButton.clicked.connect(self.accept)  # exec_ returns 1 to caller


        cancelButton.clicked.connect(self.reject)  # exec_ returns 0 to caller


class libraryManager(QMainWindow):
    # setup signal to send dictionary back to main menu bar
    library_changed = pyqtSignal(dict)
    openedLibraryInManager = pyqtSignal(dict)

    def __init__(self, parent=None, settings=None):
        super(libraryManager, self).__init__(parent)
        self.setWindowTitle("Library Manager")
        self.setGeometry(150, 150, 1450, 600)
        self.settings=settings
        self.libraryDir = None
        self.spectral_libraries = {}

        # menu bar actions
        # File menu
        selectImagesAction = QAction("Open library",self)
        selectImagesAction.triggered.connect(self.open_library)
        #exitAction = QAction("Close",self)
        #exitAction.triggered.connect(self.dummy)
        # Tools menu
        MergeLibrariesAction = QAction("Merge Libraries",self)
        MergeLibrariesAction.triggered.connect(self.merge_libraries)

        # add the menu bar
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu("&File")
        fileMenu.addAction(selectImagesAction)
        #fileMenu.addAction(exitAction)
        settingsMenu = mainMenu.addMenu("&Tools")
        settingsMenu.addAction(MergeLibrariesAction)

        # list widget with list of images
        self.table_view = QTableWidget()
        self.table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        nCols = 7
        nRows = 0
        self.table_view.setRowCount(nRows)
        self.table_view.setColumnCount(nCols)
        self.table_view.setHorizontalHeaderLabels(['Num Spectra','Num Bands','Scale','Wavelengths','Range: min-max','Directory'])
        self.table_view.setColumnHidden(6, True)
        self.table_view.horizontalHeader().setStretchLastSection(True) # stretch last column
        self.table_view.horizontalHeader().ResizeMode(QHeaderView.ResizeToContents)
        self.table_view.verticalHeader().setAlternatingRowColors(True)
        self.table_view.doubleClicked.connect(self.cell_was_double_clicked)
        self.table_view.verticalHeader().sectionClicked.connect(self.vertical_header_was_clicked)

        # set the layout for the central widget
        self.widget_central = QWidget()
        self.vbox = QVBoxLayout()
        self.widget_central.setLayout(self.vbox)
        self.vbox.addWidget(self.table_view)

        # set as central widget and dock widget
        self.setCentralWidget(self.widget_central)

    def merge_libraries(self):

        # determine the selected libraries
        selected_indices = []
        libraries = []
        for item in self.table_view.selectedIndexes():
            row = item.row()
            if row not in selected_indices:
                selected_indices.append(row)
                fname = self.table_view.item(row, 6).text()
                libraries.append(self.spectral_libraries[fname])
        # exit if no libraries are selected
        if len(selected_indices) == 0:
            return

        # get the merge options
        dialog = MergeOptionsDlg(self)  # instance of morege options setter dialog is a child of libraryManager
        # show extant property values
        dialog.extendComboBox.setCurrentIndex(
            dialog.extendComboBox.findText("Extend with 0"))
        dialog.unitsComboBox.setCurrentIndex(
            dialog.unitsComboBox.findText("Micrometers"))
        # setting new property values based on user interaction
        if dialog.exec_():  # waits for dialog.exec_(), at which case it pulls the values
            self.extendMethod = dialog.extendComboBox.currentText()
            self.units = dialog.unitsComboBox.currentText()
        else:
            return

        # get the output filename
        fname = QFileDialog.getSaveFileName(self, 'Save Spectral Library', '')
        if fname == '':
            return

        # determine the wavelengths to merge to
        wlScaleFactor = []
        wl = set([])
        for idx in range(len(libraries)):
            # check if the units are nanometers or microns, are rescale as needed here
            if min(libraries[idx].bands.centers) > 300:
                # if the units a nm
                if self.units == 'Nanometers':
                    wlScaleFactor.append(1)
                else:
                    wlScaleFactor.append(0.001)
            else:
                # if the units a micormeters
                if self.units == 'Nanometers':
                    wlScaleFactor.append(1000)
                else:
                    wlScaleFactor.append(1)

            # put the library on the new wavelength scale
            # using try-except in case these are not all defined in the structure (which may or may not be the case for libraries[idx].metadata.wavelength)
            try:
                libraries[idx].bands.bandwidths = specTools.list_multiply(libraries[idx].bands.bandwidths, wlScaleFactor[-1])
            except:
                pass
            try:
                libraries[idx].bands.bandwidth_stdevs = specTools.list_multiply(libraries[idx].bands.bandwidth_stdevs, wlScaleFactor[-1])
            except:
                pass
            try:
                libraries[idx].bands.centers = specTools.list_multiply(libraries[idx].bands.centers, wlScaleFactor[-1])
            except:
                pass
            try:
                libraries[idx].bands.centers_stdevs = specTools.list_multiply(libraries[idx].bands.centers_stdevs, wlScaleFactor[-1])
            except:
                pass
            try:
                libraries[idx].metadata.wavelength = specTools.list_multiply(libraries[idx].metadata.wavelength, wlScaleFactor[-1])
            except:
                pass
            # add the wavelengths
            wl = wl.union(set(libraries[idx].bands.centers))

        # determine the number of spectra
        nBands = len(wl)
        nSpectra = 0
        for lib in libraries:
            nSpectra = nSpectra + len(lib.names)

        # create band information for resampling
        new_band_info = BandInfo()
        new_band_info.centers = list(wl)
        new_band_info.centers.sort()
        first_time = True
        for lib in libraries:
            # resample library to image wavelengths
            # compute resampling matrix
            #resample = BandResampler(lib.bands, new_band_info)
            resample = np.zeros([len(new_band_info.centers), len(lib.bands.centers)])
            new_lib_indices = []
            for lib_band_idx in range(len(lib.bands.centers)):
                new_idx = new_band_info.centers.index(lib.bands.centers[lib_band_idx])
                new_lib_indices.append(new_idx)
                resample[new_idx,lib_band_idx] = 1

            previous_lib_wl_idx = 0
            for new_idx in range(new_lib_indices[0]+1,new_lib_indices[-1]-1):
                if new_idx in new_lib_indices:
                    previous_lib_wl_idx = previous_lib_wl_idx + 1
                else:
                    new_wl = new_band_info.centers[new_idx]
                    pct_from_next = (new_wl - lib.bands.centers[previous_lib_wl_idx]) / (lib.bands.centers[previous_lib_wl_idx+1] - lib.bands.centers[previous_lib_wl_idx])
                    pct_from_prior = 1 - pct_from_next
                    resample[new_idx, previous_lib_wl_idx] = pct_from_prior
                    resample[new_idx, previous_lib_wl_idx+1] = pct_from_next


            # compute y-scale factor
            if np.median(lib.spectra) < 2:
                yscalefactor = 1
            else:
                yscalefactor =10**(-np.ceil(np.log10(np.median(lib.spectra))))

            if first_time == True:
                # resample
                new_spectra = np.matmul(lib.spectra*yscalefactor, resample.T)
                new_names = lib.names
                first_time = False
            else:
                # resample
                new_spectra = np.vstack([new_spectra,np.matmul(lib.spectra*yscalefactor, resample.T)])
                new_names = new_names + lib.names

        # create the header
        header = {}
        header['spectra names'] = new_names
        header['wavelength'] = new_band_info.centers
        # make the library
        lib = envi.SpectralLibrary(new_spectra, header, [])

        # save the file
        lib.save(fname, 'Library from image spectra')

        # open the library
        lib, ok = specTools.is_library_file(fname)
        lib_dict = {'lib': lib}
        # uncheck this if we want to also view the library
        #self.openedLibraryInManager.emit(lib_dict)
        self.add_to_table(lib)

    def cell_was_double_clicked(self, QModelIndex):
        rowIdx = QModelIndex.row()
        fname = self.table_view.item(rowIdx,6).text()
        lib = self.spectral_libraries[fname]
        lib_dict = {'lib': lib}
        self.openedLibraryInManager.emit(lib_dict)

    def vertical_header_was_clicked(self, rowIdx):
        fname = self.table_view.item(rowIdx,6).text()
        lib = self.spectral_libraries[fname]
        lib_dict = {'lib': lib}
        self.openedLibraryInManager.emit(lib_dict)

    def open_library(self):
        # Get the library name
        lib, ok = specTools.select_library(self, prompt="Choose a library")
        if ok:
            self.libraryDir = os.path.dirname(os.path.abspath(lib.params.filename))
        else: return
        lib_dict = {'lib': lib}
        # uncheck this if we want to also view the library
        #self.openedLibraryInManager.emit(lib_dict)
        self.add_to_table(lib)

    def add_to_table(self, lib):

        # check if the library is already present
        nRows = self.table_view.rowCount()
        vheaders = []
        fnames = []
        for i in range(nRows):
            vheaders.append(self.table_view.verticalHeaderItem(i).text())
            fnames.append(self.table_view.item(i,6).text())
        if lib.params.filename in fnames:
            rowID = fnames.index(lib.params.filename)
            self.table_view.selectRow(rowID)
            return

        # add the metadata for the new row
        self.table_view.insertRow(nRows)
        vheaders.append(os.path.basename(lib.params.filename))
        self.table_view.setVerticalHeaderLabels(vheaders)
        self.table_view.setItem(nRows, 0, QTableWidgetItem("%d"%lib.params.nrows))
        self.table_view.setItem(nRows, 1, QTableWidgetItem("%d"%lib.params.ncols))
        self.table_view.setItem(nRows, 2, QTableWidgetItem("0 - %d"%10**ceil(log10(np.median(lib.spectra)))))
        self.table_view.setItem(nRows, 3, QTableWidgetItem("%f - %f"%(np.min(lib.bands.centers),np.max(lib.bands.centers))))
        self.table_view.setItem(nRows, 4, QTableWidgetItem("%f - %f"%(np.min(lib.spectra),np.max(lib.spectra))))
        self.table_view.setItem(nRows, 5, QTableWidgetItem(os.path.dirname(os.path.abspath(lib.params.filename))))
        self.table_view.setItem(nRows, 6, QTableWidgetItem(lib.params.filename))

        self.spectral_libraries[lib.params.filename] = lib
        self.library_changed.emit(self.spectral_libraries)

        # To Do - toggle min-max by removing bad bands in a little gui

    def save_as_library(self):
        # get the data from the plot
        ax = self.MPWidget.getFigure().gca()
        lines = ax.lines
        names = []
        wl = lines[0].get_xdata()
        spectra = []
        for line in lines:
            if max(abs(wl) - line.get_xdata()) == 0:
                # if the wl matches the wl of the first spectrum
                names.append(line.get_label())
                spectra.append(line.get_ydata())
            else:
                QMessageBox.information(self, "Multiple Wavelengths in plot:",
                                        "Only spectra with the following wavelengths will be saved: " + str(wl))

        # create the numpy spectra array
        np_spectra = np.zeros([len(names), len(wl)])
        row = 0
        for s in spectra:
            np_spectra[row, :] = np.asarray(s)
            row = row + 1

        # create the header
        header = {}
        header['spectra names'] = names
        header['wavelength'] = wl
        # make the library
        lib = envi.SpectralLibrary(np_spectra, header, [])
        # select output filename
        fname, ok = QFileDialog.getSaveFileName(self, 'Save Spectral Library', '')
        if not ok:
            return
        print(fname)
        # save the file
        lib.save(fname, 'Library from image spectra')

if __name__ == "__main__":
    app = QApplication(sys.argv)
    #app = QApplication.instance() # when running in Canopy
    form = libraryManager()
    form.show()
    app.exec_()