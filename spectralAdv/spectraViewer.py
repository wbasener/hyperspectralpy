from __future__ import division
import time
import sys
import os
import functools
from math import *
import matplotlib
import matplotlib.pyplot as plt
#matplotlib.use('Qt4Agg')
from spectral import *
import numpy as np
import pandas as pd
from scipy.optimize import nnls
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from pyqtgraph.widgets.MatplotlibWidget import *


class rescaleSingleSpectrum(QDialog):
    newBRSpectrum = pyqtSignal(object, object, object)

    def __init__(self, parent=None):
        super(rescaleSingleSpectrum, self).__init__(parent)
        self.setWindowTitle("Choose Spectrum to rescale")
        self.setGeometry(150, 150, 550, 250)

        # list widget with list of images
        self.table_view = QTableWidget()
        self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        nCols = 3
        nRows = 0
        self.table_view.verticalHeader().setDefaultSectionSize(18)
        self.table_view.setRowCount(nRows)
        self.table_view.setColumnCount(nCols)
        self.table_view.setHorizontalHeaderLabels(['Spectrum', 'Desired Scale', 'Name'])
        self.table_view.setColumnWidth(0, 80)  # num spectra
        self.table_view.setColumnWidth(1, 80)  # num bands
        self.table_view.setColumnWidth(2, 80)  # scale
        self.table_view.horizontalHeader().setStretchLastSection(True)  # stretch last column
        self.table_view.verticalHeader().hide()
        self.fill_table()

        # create buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.Apply |
                                     QDialogButtonBox.Close)
        # add buttons to layout
        vbox = QVBoxLayout()
        vbox.addWidget(self.table_view)
        vbox.addWidget(buttonBox)
        self.setLayout(vbox)

        # set signals for the buttons
        self.connect(buttonBox.button(QDialogButtonBox.Apply), SIGNAL("clicked()"), self.apply)
        self.connect(buttonBox, SIGNAL("rejected()"), self, SLOT("reject()"))

    def fill_table(self):

        names = []
        colors = []
        self.wl_all = []
        self.spectra_all = []
        for line in self.lines:
            wl_in_window = []
            spectrum_in_window = []
            for wl, y in zip(line.get_xdata(), line.get_ydata()):
                if wl > self.xlim[0] and wl < self.xlim[1]:
                    wl_in_window.append(wl)
                    spectrum_in_window.append(y)
            if len(spectrum_in_window) == 0:
                wl_in_window = line.get_xdata()
                spectrum_in_window = line.get_ydata()
            self.wl_all.append(wl_in_window)
            self.spectra_all.append(spectrum_in_window)
            names.append(line._label)
            colors.append(line._color)
        self.nRows = len(names)
        self.table_view.setRowCount(self.nRows)
        for i in range(self.nRows):
            # create the spectrum label text
            item = QTableWidgetItem(names[i])
            rgb = self.hex_to_rgb(colors[i])
            item.setForeground(QColor(rgb[0], rgb[1], rgb[2]))
            self.table_view.setItem(i, 2, item)
            self.table_view.setItem(i, 0, QTableWidgetItem(''))
            self.table_view.setItem(i, 1, QTableWidgetItem(''))

        # signal for selection changed
        self.table_view.itemSelectionChanged.connect(self.selection_changed)

    def selection_changed(self):
        # get the row and column of the selection
        indices = self.table_view.selectedIndexes()
        try:
            row = indices[0].row()
            col = indices[0].column()
            self.process_selection(row, col)
        except:
            # user clicked outside the table entries
            return

    def process_selection(self, row, col):
        # reject if the selected cell is not selectable
        if col > 2:
            return

        # determine the current selection for thie spectrum, if present
        current_selection = None
        if self.table_view.item(row, 0).text() == 'X':
            current_selection = 0
        if self.table_view.item(row, 1).text() == 'X':
            current_selection = 1

        # remove the current selection, if there is a current selection
        if current_selection != None:
            self.table_view.setItem(row, current_selection, QTableWidgetItem(''))

        # if the user selection is the current selection we leave it blank,
        # otherwise we select the user selection
        if current_selection != col:
            self.table_view.setItem(row, col, QTableWidgetItem('X'))

    def apply(self):
        pixel = np.zeros(0)
        backgrounds = np.zeros(0)
        targets = np.zeros(0)
        numPixels = 0
        numTargets = 0

        # get the data
        for row_idx in range(self.nRows):

            # check if this spectrum is the pixel
            if self.table_view.item(row_idx, 0).text() == 'X':
                if len(pixel) == 0:
                    pixel = np.array(self.spectra_all[row_idx])
                    wl = np.array(self.wl_all[row_idx])
                    numPixels = 1
                else:
                    numPixels = numPixels + 1
                    pixel = pixel + np.array(self.spectra_all[row_idx])

            # check if this spectrum is a background
            if self.table_view.item(row_idx, 1).text() == 'X':
                if len(backgrounds) == 0:
                    backgrounds = np.array(self.spectra_all[row_idx])
                else:
                    backgrounds = np.vstack([backgrounds, np.array(self.spectra_all[row_idx])])

            # check if this spectrum is a target
            if self.table_view.item(row_idx, 2).text() == 'X':
                if len(targets) == 0:
                    targets = np.array(self.spectra_all[row_idx])
                    numTargets = 1
                else:
                    numTargets = numTargets + 1
                    targets = np.vstack([targets, np.array(self.spectra_all[row_idx])])
        # take the mean of the pixels spectra
        pixel = pixel / numPixels

        # validation that required selections were made
        if len(pixel) == 0:
            QMessageBox.warning(self, "Selection Error",
                                "You must select one pixel spectrum.")
            return
        if len(backgrounds) == 0:
            QMessageBox.warning(self, "Selection Error",
                                "You must select at least one background spectrum.")
            return

        # compute the background-removed pixel
        if numTargets == 0:
            coeff = nnls(np.transpose(backgrounds), np.transpose(pixel))
            bk = np.matmul(coeff[0], backgrounds)
            bk_removed = pixel - bk
        elif numTargets == 1:
            data = np.vstack([targets, backgrounds])
            coeff = nnls(np.transpose(data), np.transpose(pixel))
            bk = np.matmul(coeff[0][1:len(coeff[0])], backgrounds)
            bk_removed = pixel - bk
        else:
            bk_removed = np.zeros(len(wl))
            for idx in range(numTargets):
                target = targets[idx, :]
                data = np.vstack([target, backgrounds])
                coeff = nnls(np.transpose(data), np.transpose(pixel))
                bk = np.matmul(coeff[0][1:len(coeff[0])], backgrounds)
                bk_removed = bk_removed + pixel - bk
            bk_removed = bk_removed / numTargets

        # compute the abundance
        abundance = 100 * np.sum(np.abs(bk_removed)) / np.sum(np.abs(pixel))
        # rescale
        if self.scale == 'data':
            bk_removed = bk_removed*(100/abundance)

        # emit the signal to send data back
        label = 'Background removed spectrum, %.0f%%' % abundance
        self.newBRSpectrum.emit(wl, bk_removed, label)


class editDataDlg(QDialog):
    # signal to send back the new background removed spectrum
    updateData = pyqtSignal()

    def __init__(self, lines, parent=None):
        super(editDataDlg, self).__init__(parent)
        self.setWindowTitle("Edit Data")
        self.setGeometry(150, 150, 750, 450)
        self.lines = lines

        # list widget with list of images
        self.table_view = QTableWidget()
        self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        nCols = 3
        nRows = 0
        self.table_view.setRowCount(nRows)
        self.table_view.setColumnCount(nCols)
        self.table_view.setHorizontalHeaderLabels(['Width', 'Color', 'Name'])
        self.table_view.horizontalHeader().ResizeMode(QHeaderView.ResizeToContents)
        self.table_view.horizontalHeader().setStretchLastSection(True)  # stretch last column
        self.table_view.verticalHeader().hide()
        self.fill_table()

        # add buttons to layout
        vbox = QVBoxLayout()
        vbox.addWidget(self.table_view)
        self.setLayout(vbox)

    def fill_table(self):

        # disconnect signals for selection changed,
        # try/except used in case the signals are not connected
        try:
            self.table_view.cellChanged.disconnect()
            self.table_view.itemSelectionChanged.disconnect()
        except:
            pass

        names = []
        colors = []
        widths = []
        for line in self.lines:
            widths.append(line._linewidth)
            names.append(line._label)
            colors.append(line._color)
        self.nRows = len(names)
        self.table_view.setRowCount(self.nRows)
        for i in range(self.nRows):
            # plot line width
            sp = QDoubleSpinBox()
            sp.setSingleStep(0.25)
            sp.setRange(0.25,10)
            sp.setValue(widths[i])
            sp.valueChanged.connect(self.data_changed)
            self.table_view.setCellWidget(i, 0, sp)

            # plot line color
            item = QTableWidgetItem('  ')
            rgb = self.hex_to_rgb(colors[i])
            item.setBackground(QColor(rgb[0], rgb[1], rgb[2]))
            self.table_view.setItem(i, 1, item)

            # create the spectrum label text
            self.table_view.setItem(i, 2, QTableWidgetItem(names[i]))

        # signal for selection changed
        self.table_view.cellChanged.connect(self.data_changed)
        self.table_view.itemSelectionChanged.connect(self.item_selected)

    def contextMenuEvent(self, event):
        item = self.table_view.selectedItems()[0]
        row = item.row()
        column = item.column()
        if column == 2:
            choice = QMessageBox.question(self, 'Delete Spectrum',
                                                "Delete "+item.text()+"?",
                                                QMessageBox.Yes | QMessageBox.No)
            if choice == QMessageBox.Yes:
                del self.lines[row]
                self.fill_table()
                self.data_changed()

    def item_selected(self):
        # get the first selected item
        item = self.table_view.selectedItems()[0]
        row = item.row()
        column = item.column()
        # if this is the color column, initiate color picker
        if column == 1:
            current_color = item.background().color()
            new_color = QColorDialog.getColor(initial = current_color)
            if new_color.isValid():
                item = QTableWidgetItem('  ')
                rgb = [new_color.red(),new_color.green(),new_color.blue()]
                item.setBackground(QColor(rgb[0], rgb[1], rgb[2]))
                self.table_view.setItem(row, 1, item)
            self.table_view.clearSelection()

    def hex_to_rgb(self, value):
        value = value.lstrip('#')
        lv = len(value)
        return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

    def data_changed(self):
        i = 0
        for line in self.lines:
            # get the line width from the table
            line._linewidth = self.table_view.cellWidget(i,0).value()
            # get the line color from the table
            color = self.table_view.item(i, 1).background().color()
            line._color = '#%02x%02x%02x' % (color.red(),color.green(),color.blue())
            # get the label from the table
            line._label = self.table_view.item(i, 2).text()
            i = i+1
        self.updateData.emit()


class copySomeDlg(QDialog):

    def __init__(self, lines, parent=None):
        super(copySomeDlg, self).__init__(parent)
        self.setWindowTitle("Select Spectra to Copy")
        self.setGeometry(150, 150, 750, 450)
        self.lines = lines

        # list widget with list of images
        self.table_view = QTableWidget()
        self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        nCols = 1
        nRows = 0
        self.table_view.setRowCount(nRows)
        self.table_view.setColumnCount(nCols)
        self.table_view.setHorizontalHeaderLabels(['Spectra Names'])
        self.table_view.horizontalHeader().ResizeMode(QHeaderView.ResizeToContents)
        self.table_view.horizontalHeader().setStretchLastSection(True)  # stretch last column
        self.table_view.verticalHeader().hide()
        self.table_view.horizontalHeader().hide()
        self.fill_table()

        # ok / cancel buttons
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        # add buttons to layout
        vbox = QVBoxLayout()
        vbox.addWidget(self.table_view)
        vbox.addWidget(self.buttonbox)
        self.setLayout(vbox)

    def fill_table(self):

        names = []
        colors = []
        for line in self.lines:
            names.append(line._label)
            colors.append(line._color)
        self.nRows = len(names)
        self.table_view.setRowCount(self.nRows)
        for idx in range(self.nRows):

            # checkbox to select this spectrum
            chkBoxItem = QTableWidgetItem(names[idx])
            rgb = self.hex_to_rgb(colors[idx])
            chkBoxItem.setForeground(QColor(rgb[0], rgb[1], rgb[2]))
            chkBoxItem.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled )
            chkBoxItem.setCheckState(Qt.Unchecked)
            self.table_view.setItem(idx, 0, chkBoxItem)

    def hex_to_rgb(self, value):
        value = value.lstrip('#')
        lv = len(value)
        return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))







class backgroundRemoval(QDialog):
    # signal to send back the new background removed spectrum
    newBRSpectrum = pyqtSignal(object, object, object)

    def __init__(self, lines, xlim, scale, parent=None):
        super(backgroundRemoval, self).__init__(parent)
        self.setWindowTitle("Background Removal")
        self.setGeometry(150, 150, 750, 450)
        self.lines = lines
        self.xlim = xlim
        self.scale = scale

        # list widget with list of images
        self.table_view = QTableWidget()
        self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        nCols = 4
        nRows = 0
        self.table_view.setRowCount(nRows)
        self.table_view.setColumnCount(nCols)
        self.table_view.setHorizontalHeaderLabels(['Pixel', 'Background', 'Target', 'Name'])
        self.table_view.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.table_view.horizontalHeader().setStretchLastSection(True)  # stretch last column
        self.table_view.verticalHeader().hide()
        self.fill_table()

        # create buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.Apply |
                                     QDialogButtonBox.Close)
        # add buttons to layout
        vbox = QVBoxLayout()
        vbox.addWidget(self.table_view)
        vbox.addWidget(buttonBox)
        self.setLayout(vbox)

        # set signals for the buttons
        self.connect(buttonBox.button(QDialogButtonBox.Apply), SIGNAL("clicked()"), self.apply)
        self.connect(buttonBox, SIGNAL("rejected()"), self, SLOT("reject()"))

    def fill_table(self):

        names = []
        colors = []
        self.wl_all = []
        self.spectra_all = []
        for line in self.lines:
            wl_in_window = []
            spectrum_in_window = []
            for wl, y in zip(line.get_xdata(), line.get_ydata()):
                if wl >= self.xlim[0] and wl <= self.xlim[1]:
                    wl_in_window.append(wl)
                    spectrum_in_window.append(y)
            if len(spectrum_in_window) == 0:
                wl_in_window = line.get_xdata()
                spectrum_in_window = line.get_ydata()
            self.wl_all.append(wl_in_window)
            self.spectra_all.append(spectrum_in_window)
            names.append(line._label)
            colors.append(line._color)
        self.nRows = len(names)
        self.table_view.setRowCount(self.nRows)
        for i in range(self.nRows):
            # create the spectrum label text
            item = QTableWidgetItem(names[i])
            rgb = self.hex_to_rgb(colors[i])
            item.setForeground(QColor(rgb[0], rgb[1], rgb[2]))
            self.table_view.setItem(i, 3, item)
            self.table_view.setItem(i, 0, QTableWidgetItem(''))
            self.table_view.setItem(i, 1, QTableWidgetItem(''))
            self.table_view.setItem(i, 2, QTableWidgetItem(''))

        # signal for selection changed
        self.table_view.itemSelectionChanged.connect(self.selection_changed)

    def hex_to_rgb(self, value):
        value = value.lstrip('#')
        lv = len(value)
        return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

    def selection_changed(self):
        # get the row and column of the selection
        indices = self.table_view.selectedIndexes()
        try:
            row = indices[0].row()
            col = indices[0].column()
            self.process_selection(row, col)
        except:
            # user clicked outside the table entries
            return

    def process_selection(self, row, col):
        # reject if the selected cell is not selectable
        if col > 2:
            return

        # determine the current selection for thie spectrum, if present
        current_selection = None
        if self.table_view.item(row, 0).text() == 'X':
            current_selection = 0
        if self.table_view.item(row, 1).text() == 'X':
            current_selection = 1
        if self.table_view.item(row, 2).text() == 'X':
            current_selection = 2

        # remove the current selection, if there is a current selection
        if current_selection != None:
            self.table_view.setItem(row, current_selection, QTableWidgetItem(''))

        # if the user selection is the current selection we leave it blank,
        # otherwise we select the user selection
        if current_selection != col:
            self.table_view.setItem(row, col, QTableWidgetItem('X'))

    def apply(self):
        pixel = np.zeros(0)
        backgrounds = np.zeros(0)
        targets = np.zeros(0)
        numPixels = 0
        numTargets = 0

        # get the data
        for row_idx in range(self.nRows):

            # check if this spectrum is the pixel
            if self.table_view.item(row_idx, 0).text() == 'X':
                if len(pixel) == 0:
                    pixel = np.array(self.spectra_all[row_idx])
                    wl = np.array(self.wl_all[row_idx])
                    numPixels = 1
                else:
                    numPixels = numPixels + 1
                    pixel = pixel + np.array(self.spectra_all[row_idx])

            # check if this spectrum is a background
            if self.table_view.item(row_idx, 1).text() == 'X':
                if len(backgrounds) == 0:
                    backgrounds = np.array(self.spectra_all[row_idx])
                else:
                    backgrounds = np.vstack([backgrounds, np.array(self.spectra_all[row_idx])])

            # check if this spectrum is a target
            if self.table_view.item(row_idx, 2).text() == 'X':
                if len(targets) == 0:
                    targets = np.array(self.spectra_all[row_idx])
                    numTargets = 1
                else:
                    numTargets = numTargets + 1
                    targets = np.vstack([targets, np.array(self.spectra_all[row_idx])])
        # take the mean of the pixels spectra
        pixel = pixel / numPixels

        # validation that required selections were made
        if len(pixel) == 0:
            QMessageBox.warning(self, "Selection Error",
                                "You must select one pixel spectrum.")
            return
        if len(backgrounds) == 0:
            QMessageBox.warning(self, "Selection Error",
                                "You must select at least one background spectrum.")
            return

        # compute the background-removed pixel
        if numTargets == 0:
            coeff = nnls(np.transpose(backgrounds), np.transpose(pixel))
            bk = np.matmul(coeff[0], backgrounds)
            bk_removed = pixel - bk
        elif numTargets == 1:
            data = np.vstack([targets, backgrounds])
            coeff = nnls(np.transpose(data), np.transpose(pixel))
            bk = np.matmul(coeff[0][1:len(coeff[0])], backgrounds)
            bk_removed = pixel - bk
        else:
            bk_removed = np.zeros(len(wl))
            for idx in range(numTargets):
                target = targets[idx, :]
                data = np.vstack([target, backgrounds])
                coeff = nnls(np.transpose(data), np.transpose(pixel))
                bk = np.matmul(coeff[0][1:len(coeff[0])], backgrounds)
                bk_removed = bk_removed + pixel - bk
            bk_removed = bk_removed / numTargets

        # compute the abundance
        abundance = 100 * np.sum(np.abs(bk_removed)) / np.sum(np.abs(pixel))
        # rescale
        if self.scale == 'data':
            bk_removed = bk_removed*(100/abundance)

        # emit the signal to send data back
        label = 'Background removed spectrum, %.0f%%' % abundance
        self.newBRSpectrum.emit(wl, bk_removed, label)



# creating a custom MainWindow to collect resize events to redraw the plot
class MyMainWindow(QMainWindow):
    resized = pyqtSignal()
    def resizeEvent(self, event):
        self.resized.emit()
        QMainWindow.resizeEvent(self, event)

class specPlot(MyMainWindow):
    # setup signal to send copied spectrum back
    copiedSpectrum = pyqtSignal(dict)
    pasteSpectrumRequest = pyqtSignal(int)
    setImageDisplayBand = pyqtSignal(int)

    def __init__(self, settings=None, x=None, y=None, parent=None, wl=None, vals=None, offset=0,
                 marker=None, image_type=None):
        super(specPlot, self).__init__(parent)
        self.setWindowTitle("Spectral Viewer")
        self.resized.connect(self.replot_tight)
        self.setGeometry(400 + offset, 200 + offset, 800, 450)
        self.settings = settings
        self.spectra_names = []
        self.pasteSpectrumRequestSent = False
        self.mousePressed = False
        self.right_zoom = False
        self.image_type = image_type

        # pop up context menu
        self.popMenu = QMenu(self)

        # menu bar actions
        saveLibraryAction = QAction("Save as Library", self)
        saveLibraryAction.triggered.connect(self.save_as_library)
        saveLibraryActionCSV = QAction("Save library as csv",self)
        saveLibraryActionCSV.triggered.connect(self.save_as_csv)
        editDataAction = QAction("Edit Data", self)
        editDataAction.triggered.connect(self.edit_data)
        commonScaleAction = QAction("Common Scale in Window", self)
        commonScaleAction.triggered.connect(self.common_scale)
        singleSpectrumScaleAction = QAction("Scale a Single Spectrum", self)
        singleSpectrumScaleAction.triggered.connect(self.rescale_single_spectrum)
        removeScaleAction = QAction("Original scale", self)
        removeScaleAction.triggered.connect(self.remove_scale)

        backgroundRemovalRescaleAction = QAction("Output in Fullpixel Data Scale", self)
        backgroundRemovalRescaleAction.triggered.connect(self.background_removal_rescale)
        backgroundRemovalRawScaleAction = QAction("Output in Raw Subpixel Scale", self)
        backgroundRemovalRawScaleAction.triggered.connect(self.background_removal)



        # menu Items
        self.mainMenu = self.menuBar()
        fileMenu = self.mainMenu.addMenu("&File ")
        fileMenu.addAction(saveLibraryAction)
        fileMenu.addAction(saveLibraryActionCSV)
        editMenu = self.mainMenu.addMenu("&Edit ")
        editMenu.addAction(editDataAction)
        optionsMenu = self.mainMenu.addMenu("&Scale Options ")
        optionsMenu.addAction(commonScaleAction)
        optionsMenu.addAction(singleSpectrumScaleAction)
        optionsMenu.addAction(removeScaleAction)
        analysisMenu = self.mainMenu.addMenu("&Analysis ")
        backgroundRemovalMenu = QMenu("Background Removal", self)
        analysisMenu.addMenu(backgroundRemovalMenu)
        backgroundRemovalMenu.addAction(backgroundRemovalRescaleAction)
        backgroundRemovalMenu.addAction(backgroundRemovalRawScaleAction)
        self.spectraManagerMenu = self.mainMenu.addMenu("Copy Spectrum ")
        if self.image_type == 'data':
            self.maxBandMenu = self.mainMenu.addMenu("Display Max Band ")

        try:
            self.MPWidget = MatplotlibWidgetBottomToolbar()
        except:
            self.MPWidget = MatplotlibWidget()
        self.subplot = self.MPWidget.getFigure().add_subplot(111)
        try:
            #print('row: ' + str(y) + ', col: ' + str(x))
            #for v in vals: print(v)
            #print(vals[0])
            #print(marker)
            self.subplot.plot(wl, vals, label='row: ' + str(y) + ', col: ' + str(x), marker=marker, linewidth=1)
            self.addGainOffset('row: ' + str(y) + ', col: ' + str(x))
        except:
            pass
        #self.subplot.axes.autoscale(enable=True, tight=True)
        self.cid = self.subplot.figure.canvas.mpl_connect('draw_event', self.plot_changed)
        self.cid = self.subplot.figure.canvas.mpl_connect('button_press_event', self.onMouseDown)
        self.cid = self.subplot.figure.canvas.mpl_connect('button_release_event', self.onMouseUp)
        self.cid = self.subplot.figure.canvas.mpl_connect('motion_notify_event', self.onMouseMove)
        self.cid = self.subplot.figure.canvas.mpl_connect('axes_enter_event', self.replot_tight_from_mouseover)
        if self.settings.screen_width > 3000:
            self.subplot.axes.legend(fontsize=20)
            self.subplot.axes.xaxis.set_tick_params(labelsize=20)
            self.subplot.axes.yaxis.set_tick_params(labelsize=20)
        else:
            self.subplot.axes.legend()
        # Hide the right and top spines
        self.subplot.axes.spines['right'].set_visible(False)
        self.subplot.axes.spines['top'].set_visible(False)

        def format_coord(x, y):
            return 'Wl=%1.4f, Val=%1.4f' % (x, y)

        self.subplot.axes.format_coord = format_coord

        self.subplot.axes.format_coord = format_coord

        font = QFont()
        font.setPixelSize(20)
        #self.subplot.getAxis("bottom").tickFont = font
        #self.subplot.getAxis("bottom").setStyle(tickTextOffset=20)

        self.MPWidget.draw()

        self.label = QLabel('Available Spectra:')
        self.cb_spectral = QComboBox()

        self.widget_central = QWidget()
        self.vbox = QVBoxLayout()
        self.widget_central.setLayout(self.vbox)
        self.vbox.addWidget(self.MPWidget)
        self.vbox.setSpacing(0)
        self.vbox.setContentsMargins(0, 0, 0, 0)

        # set as central widget
        self.setCentralWidget(self.widget_central)
        self.show()

        # There appears to be a bug int he Matplotlib plot:
        # https://github.com/matplotlib/matplotlib/issues/10361
        # we have to modify the plot, then redraw
        self.subplot.figure.canvas.updateGeometry()
        self.subplot.axes.autoscale(enable=True, tight=True)
        self.subplot.margins(0, tight=True)
        self.MPWidget.getFigure().tight_layout()
        self.MPWidget.draw()


    def addGainOffset(self, label):
        for line in self.MPWidget.getFigure().gca().lines:
            if line.get_label() == label:
                line.gain = 1
                line.offset = 0

    def keyPressEvent(self, event):

        # check if this is key event
        if type(event) != QKeyEvent:
            return

        # check that the ctrl key is pressed
        if QApplication.keyboardModifiers() != Qt.ControlModifier:
            return

        # check if this is a copy spectrum event
        if event.key() == Qt.Key_C:
            if self.mousePressed:
                self.copy_spectrum(self.select_spectrum_name)

        # check if this is a paste spectrum event
        if event.key() == Qt.Key_V:
            # emit signal that paste was requested
            self.paste_spectrum_request()

    def paste_spectrum_request(self):
            self.pasteSpectrumRequestSent = True
            self.pasteSpectrumRequest.emit(1)

    def plot_changed(self, event):

        # determine if the lines have changed
        lines = self.MPWidget.getFigure().gca().lines
        change_detect = False
        if len(self.spectra_names) == len(lines):
            for name,line in zip(self.spectra_names,lines):
                if name != line._label:
                    change_detect = True
        else:
            change_detect = True

        # update the lines and menu if needed
        if change_detect == True:
            # clear spectra manager menu
            for action in self.spectraManagerMenu.actions():
                self.spectraManagerMenu.removeAction(action)
            # clear popup menu
            for action in self.popMenu.actions():
                self.popMenu.removeAction(action)
            if self.image_type == 'data':
                # clear max band menu
                for action in self.maxBandMenu.actions():
                    self.maxBandMenu.removeAction(action)
            # add paste to spectraManagerMenu and popMenu
            pasteSpectrumAction = QAction("Paste", self)
            pasteSpectrumAction.triggered.connect(self.paste_spectrum_request)
            self.spectraManagerMenu.addAction(pasteSpectrumAction)
            self.popMenu.addAction(pasteSpectrumAction)
            # add copy all to spectraManagerMenu and popMenu
            copyAllSpectraAction = QAction("Copy All Spectra", self)
            copyAllSpectraAction.triggered.connect(self.copy_all_spectra)
            self.spectraManagerMenu.addAction(copyAllSpectraAction)
            self.popMenu.addAction(copyAllSpectraAction)
            # add copy some to spectraManagerMenu and popMenu
            copySomeSpectraAction = QAction("Copy Some Spectra", self)
            copySomeSpectraAction.triggered.connect(self.copy_some_spectra)
            self.spectraManagerMenu.addAction(copySomeSpectraAction)
            self.popMenu.addAction(copySomeSpectraAction)
            self.spectra_names = []        # menu Items
            # get the spectra names
            for line in lines:
                self.spectra_names.append(line._label)
            # create the menu actions
            for name in self.spectra_names:

                # create menu item for spectraManagerMenu and popMenu
                action_name = "Copy: "+name
                copySpectrumAction = QAction(action_name, self)
                copySpectrumAction.triggered.connect(functools.partial(self.copy_spectrum,name))
                self.spectraManagerMenu.addAction(copySpectrumAction)
                self.popMenu.addAction(copySpectrumAction)

                # create menu item for maxBandMenu
                if self.image_type == 'data':
                    action_name = "Display band for max value for pixel "+name
                    maxBandAction = QAction(action_name, self)
                    maxBandAction.triggered.connect(functools.partial(self.display_max_band,name))
                    self.maxBandMenu.addAction(maxBandAction)
            # if the edit data dialog is open, update the table
            if hasattr(self, 'editDataDlg') == True:
                self.editDataDlg.lines = lines
                self.editDataDlg.fill_table()

    def copy_all_spectra(self):
        copied_spectra = {}
        counter = 0
        for line in self.MPWidget.getFigure().gca().lines:
            copied_spectra['spec_'+str(counter)] = line
            counter = counter + 1

        # emit the signal to send data back
        self.copiedSpectrum.emit(copied_spectra)

    def copy_some_spectra(self):

        self.copySomeDlg = copySomeDlg(self.MPWidget.getFigure().gca().lines, self)
        # create the linking GUI for user selection
        self.copySomeDlg.show()
        # if the users accepts a linking, create it
        if self.copySomeDlg.exec():

            copied_spectra = {}
            counter = 0
            lines = self.MPWidget.getFigure().gca().lines
            for idx in range(self.copySomeDlg.table_view.rowCount()):
                if self.copySomeDlg.table_view.item(idx,0).checkState():
                    copied_spectra['spec_' + str(counter)] = lines[idx]
                    counter = counter + 1

        # emit the signal to send data back
        self.copiedSpectrum.emit(copied_spectra)


    def copy_spectrum(self, name):
        for line in self.MPWidget.getFigure().gca().lines:
            if line._label == name:
                copied_spectrum_Line2D = line
                break
        copied_spectrum = {}
        copied_spectrum['spec'] = copied_spectrum_Line2D

        # emit the signal to send data back
        self.copiedSpectrum.emit(copied_spectrum)

    def display_max_band(self, name):
        for line in self.MPWidget.getFigure().gca().lines:
            if line._label == name:
                max_band = np.argmax(line._y)
                break

        # emit the signal to imageViewer to display new band
        self.setImageDisplayBand.emit(max_band)

    def paste_spectrum(self, pasted_spectrum):
        # if this gui sent the request for a paste
        if self.pasteSpectrumRequestSent:
            # loop through all spectra in the clipboard spectral plot dictionary
            for key in pasted_spectrum.keys():
                pasted_spectrum_Line2D = pasted_spectrum[key]
                self.subplot.plot(pasted_spectrum_Line2D._x,pasted_spectrum_Line2D._y,
                                  color = pasted_spectrum_Line2D._color,
                                  label = pasted_spectrum_Line2D._label,
                                  marker = pasted_spectrum_Line2D._marker,
                                  linestyle = pasted_spectrum_Line2D._linestyle,
                                  linewidth = pasted_spectrum_Line2D._linewidth)
                self.addGainOffset(pasted_spectrum_Line2D._label)
                if self.settings.screen_width > 3000:
                    self.subplot.axes.legend(fontsize=20)
                else:
                    self.subplot.axes.legend()
                self.MPWidget.draw()
                self.pasteSpectrumRequestSent = False

    def edit_data(self):
        #if hasattr(self,'editDataDlg') == False:
        self.editDataDlg = editDataDlg(self.MPWidget.getFigure().gca().lines, self)
        self.editDataDlg.updateData.connect(self.update_line_data)
        self.editDataDlg.show()
        self.editDataDlg.raise_()
        self.editDataDlg.activateWindow()

    def update_line_data(self):
        if self.settings.screen_width > 3000:
            self.subplot.axes.legend(fontsize=20)
        else:
            self.subplot.axes.legend()
        self.MPWidget.draw()

    def background_removal(self):
        xlim = self.MPWidget.getFigure().gca().get_xlim()
        self.backgroundRemoval = backgroundRemoval(self.MPWidget.getFigure().gca().lines, xlim, scale = 'raw')
        # self.connect(self.backgroundRemoval, SIGNAL("newBRSpectrum(dict, QString)"), self.add_br_spectrum)
        self.backgroundRemoval.newBRSpectrum.connect(self.add_br_spectrum)
        self.backgroundRemoval.show()

    def background_removal_rescale(self):
        xlim = self.MPWidget.getFigure().gca().get_xlim()
        self.backgroundRemoval = backgroundRemoval(self.MPWidget.getFigure().gca().lines, xlim, scale = 'data')
        # self.connect(self.backgroundRemoval, SIGNAL("newBRSpectrum(dict, QString)"), self.add_br_spectrum)
        self.backgroundRemoval.newBRSpectrum.connect(self.add_br_spectrum)
        self.backgroundRemoval.show()

    def add_br_spectrum(self, wl, bk_removed, label):
        self.subplot.plot(wl, bk_removed.flatten(), label=label, linewidth=1)
        self.addGainOffset(label)
        if self.settings.screen_width > 3000:
            self.subplot.axes.legend(fontsize=20)
        else:
            self.subplot.axes.legend()
        self.MPWidget.draw()

    def common_scale(self):
        # get the data from the plot
        spectra = []
        means = []
        stdevs = []
        gains = []
        offsets = []
        yMins = []
        yMaxs = []
        xlim = self.MPWidget.getFigure().gca().get_xlim()
        for line in self.MPWidget.getFigure().gca().lines:
            spectra.append(line.get_ydata())
            try:
                gains.append(line.gain)
                offsets.append(line.offset)
            except:
                self.addGainOffset(line.get_label())
                gains.append(line.gain)
                offsets.append(line.offset)
            # compute spectrum within th ezoom window
            spectrum_in_window = []
            for wl, y in zip(line.get_xdata(), line.get_ydata()):
                if wl > xlim[0] and wl < xlim[1]:
                    spectrum_in_window.append(y)
            if len(spectrum_in_window) == 0:
                spectrum_in_window = line.get_ydata()
            means.append(np.mean(spectrum_in_window))
            stdevs.append(np.std(spectrum_in_window))
            yMins.append(np.min(spectrum_in_window))
            yMaxs.append(np.max(spectrum_in_window))

        # compute the common mean and standard deviation
        common_mean = np.mean(means)
        common_stdev = np.mean(stdevs)

        # rescale the y data
        for i in range(len(self.MPWidget.getFigure().gca().lines)):
            gain_apply = common_stdev / stdevs[i]
            offest_apply = common_mean - gain_apply * means[i]
            self.MPWidget.getFigure().gca().lines[i].set_ydata(gain_apply * spectra[i] + offest_apply)
            self.MPWidget.getFigure().gca().lines[i].gain = gain_apply * gains[i]
            self.MPWidget.getFigure().gca().lines[i].offset = gain_apply * offsets[i] + offest_apply
            yMins[i] = gain_apply * yMins[i] + offest_apply
            yMaxs[i] = gain_apply * yMaxs[i] + offest_apply

        self.MPWidget.getFigure().gca().set_ylim(bottom=np.min(yMins), top=np.max(yMaxs))
        self.MPWidget.draw()

    def rescale_single_spectrum(self):

        class spectraSelectorDlg(QDialog):
            def __init__(self, parent=None):
                super(spectraSelectorDlg, self).__init__(parent)
                #self.setGeometry(300, 300, 300, 200)
                self.setWindowTitle('Single Spectrum Scaling')

                # combo boxes
                comboSpectrumLabel = QLabel("Spectrum to scale:")
                self.comboSpectrum = QComboBox(self)
                comboOutputScaleLabel = QLabel("Spectrum with output scale:")
                self.comboOutputScale = QComboBox(self)

                 # buttons
                okButton = QPushButton("&OK")
                cancelButton = QPushButton("Cancel")

                # layout
                buttonLayout = QHBoxLayout()
                buttonLayout.addStretch()
                buttonLayout.addWidget(okButton)
                buttonLayout.addWidget(cancelButton)
                layout = QVBoxLayout()
                layout.addWidget(comboSpectrumLabel)
                layout.addWidget(self.comboSpectrum)
                layout.addWidget(comboOutputScaleLabel)
                layout.addWidget(self.comboOutputScale)
                layout.addLayout(buttonLayout)
                self.setLayout(layout)

                # signals to connect the buttons to accept and reject
                self.connect(okButton, SIGNAL("clicked()"), self, SLOT("accept()"))
                self.connect(cancelButton, SIGNAL("clicked()"), self, SLOT("reject()"))

        dialog = spectraSelectorDlg(self)
        # place the labels in the comboboxes
        for line in self.MPWidget.getFigure().gca().lines:
            dialog.comboSpectrum.addItem(line._label)
            dialog.comboOutputScale.addItem(line._label)
        if dialog.exec_():
            idx_spectrum = dialog.comboSpectrum.currentIndex()
            idx_scale = dialog.comboOutputScale.currentIndex()

        # compute the mean and std for the spectrum we want to scale
        line_spectrum = self.MPWidget.getFigure().gca().lines[idx_spectrum]

        spectrum_in_window = []
        xlim = self.MPWidget.getFigure().gca().get_xlim()
        for wl, y in zip(line_spectrum.get_xdata(), line_spectrum.get_ydata()):
            if wl > xlim[0] and wl < xlim[1]:
                spectrum_in_window.append(y)
        if len(spectrum_in_window) == 0:
            spectrum_in_window = line_spectrum.get_ydata()
        spectrum_mean = np.mean(spectrum_in_window)
        spectrum_std = np.std(spectrum_in_window)

        # compute the mean and std for the output scale
        line_output_scale = self.MPWidget.getFigure().gca().lines[idx_scale]
        spectrum_in_window = []
        for wl, y in zip(line_output_scale.get_xdata(), line_output_scale.get_ydata()):
            if wl > xlim[0] and wl < xlim[1]:
                spectrum_in_window.append(y)
        if len(spectrum_in_window) == 0:
            spectrum_in_window = line_output_scale.get_ydata()
        output_mean = np.mean(spectrum_in_window)
        output_std = np.std(spectrum_in_window)

        # compute the new gain and offset, and apply
        gain_apply = output_std / spectrum_std
        offest_apply = output_mean - gain_apply * spectrum_mean
        self.MPWidget.getFigure().gca().lines[idx_spectrum].set_ydata(gain_apply * line_spectrum.get_ydata() + offest_apply)
        self.MPWidget.getFigure().gca().lines[idx_spectrum].gain = gain_apply * self.MPWidget.getFigure().gca().lines[idx_spectrum].gain
        self.MPWidget.getFigure().gca().lines[idx_spectrum].offset = gain_apply * self.MPWidget.getFigure().gca().lines[idx_spectrum].offset + offest_apply

        # redraw the plot
        self.MPWidget.draw()

    def remove_scale(self):
        # get the data from the plot
        spectra = []
        means = []
        stdevs = []
        gains = []
        offsets = []
        for line in self.MPWidget.getFigure().gca().lines:
            spectra.append(line.get_ydata())
            means.append(np.mean(line.get_ydata()))
            stdevs.append(np.std(line.get_ydata()))
            gains.append(line.gain)
            offsets.append(line.offset)

        # rescale the y data
        for i in range(len(self.MPWidget.getFigure().gca().lines)):
            gain_apply = 1 / gains[i]
            offest_apply = 0 - gain_apply * offsets[i]
            self.MPWidget.getFigure().gca().lines[i].set_ydata(gain_apply * spectra[i] + offest_apply)
            self.MPWidget.getFigure().gca().lines[i].gain = 1
            self.MPWidget.getFigure().gca().lines[i].offset = 0

        self.MPWidget.draw()

    def onMouseDown(self, event):
        if (not self.MPWidget.toolbar.mode.value):  # check that no toolbar buttons are selected
            if event.button == 1:
                self.mousePressed = True

                # get the closest point in the plot
                yDelta = np.zeros(len(self.MPWidget.getFigure().gca().lines))
                locations = np.zeros([len(self.MPWidget.getFigure().gca().lines), 2])
                line_idx = 0
                for line in self.MPWidget.getFigure().gca().lines:
                    xDelta = np.abs(line.get_xdata() - event.xdata)
                    closest_idx = np.argmin(xDelta)
                    # get the data for the closest point
                    yDelta[line_idx] = np.abs(line.get_ydata()[closest_idx] - event.ydata)
                    locations[line_idx, 0] = line.get_xdata()[closest_idx]
                    locations[line_idx, 1] = line.get_ydata()[closest_idx]
                    line_idx = line_idx + 1
                idx_closest_pt = np.argmin(yDelta)
                x_cursor = locations[idx_closest_pt, 0]
                y_cursor = locations[idx_closest_pt, 1]
                self.select_spectrum_name = self.MPWidget.getFigure().gca().lines[idx_closest_pt]._label
                self.x_cursor = x_cursor
                self.y_cursor = y_cursor

                # set the x-y coordinates to the selected wl-val
                def format_coord(x, y):
                    return '[%s] Wl=%1.4f, Val=%1.4f' % (self.select_spectrum_name[:50], x, y)

                self.subplot.axes.format_coord = format_coord
                self.MPWidget.toolbar.set_message(format_coord(x_cursor, y_cursor))
                #Trying to add spectrum name next to cursor to shwo it is selected
                #QToolTip.showText(QPoint(0, 0), self.select_spectrum_name, self.MPWidget)

                # create the vertical and horizontal lines marking the point
                self.subplot.axvline(x=x_cursor, c='k', linewidth=0.5, label='_plot_marker_line')
                self.subplot.axhline(y=y_cursor, c='k', linewidth=0.5, label='_plot_marker_line')
                self.MPWidget.draw()
                # add circle at marker location

            if event.button == 3:

                # determine the location (NOTE: the y-position is approximated)
                x = event.x
                y = self.frameGeometry().height() - event.y - 150
                # open the spectrum copy-paste menu
                self.popMenu.exec_(self.mapToGlobal(QPoint(x,y)))


    def onMouseUp(self, event):
        if (not self.MPWidget.toolbar.mode.value):  # check that no toolbar buttons are selected
            self.mousePressed = False
            # revove current marker lines
            found_marker = 1
            while found_marker == 1:
                found_marker = 0
                searching = 0
                idx = 0
                while searching == 0:
                    if idx < len(self.MPWidget.getFigure().gca().lines):
                        if self.MPWidget.getFigure().gca().lines[idx]._label == '_plot_marker_line':
                            marker_idx = idx
                            found_marker = 1
                    else:
                        searching = 1
                    idx = idx + 1
                if found_marker == 1:
                    try:
                        self.MPWidget.getFigure().gca().lines.pop(marker_idx).remove()
                    except:
                        pass

            # set the x-y coordinates to the selected wl-val
            def format_coord(x, y):
                    return 'Wl=%1.4f, Val=%1.4f' % (x, y)

            self.subplot.axes.format_coord = format_coord
            self.MPWidget.toolbar.set_message(format_coord(event.xdata, event.ydata))

            self.MPWidget.draw()

    def onMouseMove(self, event):
        # check that no toolbar buttons are selected and that the mouse button it pressed
        #print(not self.subplot.figure.canvas.manager.toolbar.mode.value)
        if (not self.MPWidget.toolbar.mode.value) and self.mousePressed:
            # revove current marker lines
            found_marker = 1
            while found_marker == 1:
                found_marker = 0
                searching = 0
                idx = 0
                while searching == 0:
                    if idx < len(self.MPWidget.getFigure().gca().lines):
                        if self.MPWidget.getFigure().gca().lines[idx]._label == '_plot_marker_line':
                            marker_idx = idx
                            found_marker = 1
                    else:
                        searching = 1
                    idx = idx + 1
                if found_marker == 1:
                    try:
                        self.MPWidget.getFigure().gca().lines.pop(marker_idx).remove()
                    except:
                        pass

            # do nothing if the event x-y data is None (cursor is not on the plot)
            if event.xdata == None or event.xdata == None:
                return
            # get the closest point in the plot
            yDelta = np.zeros(len(self.MPWidget.getFigure().gca().lines))
            locations = np.zeros([len(self.MPWidget.getFigure().gca().lines), 2])
            line_idx = 0
            for line in self.MPWidget.getFigure().gca().lines:
                xDelta = np.abs(line.get_xdata() - event.xdata)
                closest_idx = np.argmin(xDelta)
                # get the data for the closest point
                yDelta[line_idx] = np.abs(line.get_ydata()[closest_idx] - event.ydata)
                locations[line_idx, 0] = line.get_xdata()[closest_idx]
                locations[line_idx, 1] = line.get_ydata()[closest_idx]
                line_idx = line_idx + 1
            idx_closest_pt = np.argmin(yDelta)
            x_cursor = locations[idx_closest_pt, 0]
            y_cursor = locations[idx_closest_pt, 1]

            if not (x_cursor == self.x_cursor and y_cursor == self.y_cursor):
                self.x_cursor = x_cursor
                self.y_cursor = y_cursor
                self.selected_spectrum = self.MPWidget.getFigure().gca().lines[idx_closest_pt]._label

                # set the x-y coordinates to the selected wl-val
                def format_coord(x, y):
                    return '[%s] Wl=%1.4f, Val=%1.4f' % (self.selected_spectrum[:50], x, y)

                self.subplot.axes.format_coord = format_coord

                # create the vertical and horizontal lines marking the point
                self.subplot.axvline(x=x_cursor, c='k', linewidth=0.5, label='_plot_marker_line')
                self.subplot.axhline(y=y_cursor, c='k', linewidth=0.5, label='_plot_marker_line')
                self.MPWidget.draw()

    def save_as_library(self):
        # get the data from the plot
        ax = self.MPWidget.getFigure().gca()
        lines = ax.lines
        names = []
        wl = lines[0].get_xdata()
        spectra = []
        for line in lines:
            if not line.get_label() == '_plot_marker_line':
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
        fname = QFileDialog.getSaveFileName(self, 'Save Spectral Library', '')
        if fname == '':
            return
        # save the file
        lib.save(fname, 'Library from image spectra')

    def save_as_csv(self):

        # get the data from the plot
        ax = self.MPWidget.getFigure().gca()
        lines = ax.lines
        names = []
        wl = lines[0].get_xdata()
        spectra = []
        for line in lines:
            if not line.get_label() == '_plot_marker_line':
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

        # create a dataframe from the spectra
        df = pd.DataFrame(np.transpose(np_spectra))
        # add column nemas
        df.columns = names
        # add the wavelengths as a column
        df['wavelength'] = wl

        # select output filename
        fname = QFileDialog.getSaveFileName(self, 'Save Spectral Library',
                                                     'lib.csv',
                                                     'CSV (*.csv)')
        if fname == '':
            return
        df.to_csv(fname,index=False)







    def replot_tight_from_mouseover(self,dummy):
        self.replot_tight()

    def replot_tight(self):
        self.MPWidget.getFigure().tight_layout()
        self.MPWidget.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    #app = QApplication.instance() # when running in Canopy
    form = specPlot()
    form.show()
    app.exec_()