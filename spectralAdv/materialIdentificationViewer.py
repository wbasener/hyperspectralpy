import operator
import os
import sys
import pickle
import numpy as np
from math import *

from PyQt5 import QtWidgets
from spectral import *
from . import spectraViewer
from spectralAdv import specTools
from spectralAdv import materialIdentification
from spectralAdv import materialIdentificationTabs
from fuzzywuzzy import process
from fuzzywuzzy import fuzz
from matplotlib.figure import Figure
from matplotlib.widgets import Cursor
import matplotlib.pyplot as plt
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
#from pyqtgraph.widgets.MatplotlibWidget import *

import timeit
from pyqtgraph.widgets.MatplotlibWidget import *


class feature_struc:
    def __init__(self):
        self.xdata = []
        self.ydata = []
        self.color = None

# creating a custom MainWindow to collect resize events to redraw the material id plot
class MyMainWindow(QMainWindow):
    resized = pyqtSignal()
    def resizeEvent(self, event):
        self.resized.emit()
        QtWidgets.QMainWindow.resizeEvent(self, event)

class TableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        try: # sort after conversion to float, if possible
            result = float(self.text()) > float(other.text())
        except: # else we use the alphabetical conversion (that still handles some numerical vals)
            result = self.text() > other.text()
        return result
                
class materialIdentificationViewer(MyMainWindow):
    # outgoing signals for spectralViewer
    copiedSpectrum = pyqtSignal(dict)
    pasteSpectrum = pyqtSignal(dict)
    # outgoing signals
    openedLibraryInMaterialId = pyqtSignal(dict)
    openedImageInMaterialId = pyqtSignal(dict)
    pasteSpectrumRequest = pyqtSignal(int)

    def __init__(self, settings=None, imageDir = None, libraryDir = None, im = None, 
                 im_arr = None, spectrum=None, spectral_libraries = {}):
        #QWidget.__init__(self, *args)
        super(materialIdentificationViewer, self).__init__()
        self.setWindowModality(Qt.NonModal)
        self.settings = settings
        if self.settings.screen_width > 3000:
            self.setGeometry(550, 150, 2000, 1500)  # (x_pos, y_pos, width, height)
        else:
            self.setGeometry(250, 50, 1200, 800)  # (x_pos, y_pos, width, height)
        self.settings = settings
        self.setWindowTitle("Spectral Material Identification")
        self.resized.connect(self.resized_event_handler)
        # create data variables
        self.libraryDir = libraryDir
        self.imageDir = imageDir
        self.im = im
        self.im_arr = im_arr
        self.nEndmembers = 20
        self.spectrum = spectrum
        self.spectral_libraries = spectral_libraries
        self.material_id_mode = 'data_preperation'
        self.feature_match_mode = 'data_preperation'
        self.selected_library_spectrum = None
        self.selected_library_br_spectrum = None
        self.band_region_wl_ranges = []
        self.pasteSpectrumRequestSentPixel = False
        self.pasteSpectrumRequestSentEndmember = False
        self.mousePressedPixel = False
        self.mousePressedEndmember = False
        self.mousePressedLeft = False
        self.mousePressedRight = False
        self.right_zoom_pixel = False
        self.right_zoom_endmember = False
        self.feature_building_status = False
        self.feature_building_current_index = None
        # self.first_id_mousepress tracks if a pressed mouse button was the frist press (start a new band region) or
        # not (expand currently grabbed region)
        self.first_id_mousepress = True
        self.first_feature_match_plot = True
        # tracks which individual data checks are satisfied for material id
        self.data_check = {'pixel spectrum present':False, 'libraries selected':False, 'image present':False,
                           'pixel image wl match':False, 'endmembers present':False, 'pixel endmemebers wl match':False,
                           'pixel libraries wl consistent':False}
        self.material_id_data_check = False
        # tracks which individual data checks are satisfied for feature matching
        self.data_check_fm = {'pixel spectrum present':False, 'libraries selected':False, 'pixel libraries wl consistent':False}
        self.feature_match_data_check = False
        self.x_cursor_fm = 0
        self.y_cursor_fm = 0
        self.band_regions = {}
        self.features = {}

        # Create tabs
        self.tab_data = QWidget()
        self.tab_material_id = QWidget()
        self.tab_feature_match = QWidget()
        # build the material id tab
        materialIdentificationTabs.tab_data_content(self)
        materialIdentificationTabs.tab_data_layout(self)
        # build the data tab
        materialIdentificationTabs.tab_material_id_content(self)
        materialIdentificationTabs.tab_material_id_layout(self)
        # build the feature matching tab
        materialIdentificationTabs.tab_feature_match_content(self)
        materialIdentificationTabs.tab_feature_match_layout(self)

        # add tabs as the central widget
        self.widget_central = QTabWidget()
        self.widget_central.addTab(self.tab_data, "Data")
        self.widget_central.addTab( self.tab_material_id, "Material Id")
        self.widget_central.addTab( self.tab_feature_match, "Feature Match")
        self.widget_central.currentChanged.connect(self.tab_changed)

        # create the statusbar
        self.statusBar = QStatusBar()
        # add a progressbar to the statusbar
        self.progressBar = QProgressBar()
        self.statusBar.addPermanentWidget(self.progressBar)
        self.progressBar.setGeometry(30, 40, 200, 25)
        self.progressBar.setValue(0)
        # set the staus bar
        self.setStatusBar(self.statusBar)

        # set as central widget
        self.setCentralWidget(self.widget_central)
        self.show()

        # prepare thread to handle processing iamnge stats seperate from the GUI thread
        self.mainProcessingThread = self.mainProcessingThreadDef(self.im, self.im_arr, self.nEndmembers)
        self.mainProcessingThread.updateProgress.connect(self.updateProgress)
        self.mainProcessingThread.updatePC.connect(self.updatePC)
        self.mainProcessingThread.updateW.connect(self.updateW)
        self.mainProcessingThread.updateEndmembers.connect(self.updateEndmembers)

    def tab_changed(self):

        # if the current selected tab is material id
        if self.widget_central.currentIndex() == 1:
            # compute average pixel spectrum, is spectra are present and material_id is in data_preperation mode
            if (len(self.MPWidget_pixel.getFigure().gca().lines) > 0) and (self.material_id_mode == 'data_preperation'):
                self.wl = self.MPWidget_pixel.getFigure().gca().lines[0].get_xdata()
                self.average_pixel_spectrum = np.zeros(len(self.wl))
                for line in self.MPWidget_pixel.getFigure().gca().lines:
                    self.average_pixel_spectrum = self.average_pixel_spectrum + line.get_ydata()
                self.average_pixel_spectrum = self.average_pixel_spectrum/len(self.MPWidget_pixel.getFigure().gca().lines)

                # plot in pixel material id viewer
                self.subplot_material_id.axes.clear()
                self.subplot_material_id.plot(self.wl, self.average_pixel_spectrum,
                                            color='k',
                                            marker='.',
                                            label='Pixel Spectrum',
                                            linewidth=1)
                if self.settings.screen_width > 3000:
                    self.subplot_material_id.axes.legend(fontsize=20)
                else:
                    self.subplot_material_id.axes.legend()
                self.MPWidget_material_id.getFigure().tight_layout()
                self.MPWidget_material_id.draw()
                self.data_check['pixel spectrum present'] = True

                # add a band region
                fig = self.MPWidget_material_id.getFigure()  # gets the figure in a variable
                ax = self.subplot_material_id.axes  # get the axis in a variable
                self.background = fig.canvas.copy_from_bbox(ax.bbox)  # get everything currently plotted
                # use this is we want to create a band region spanning all bands when firt opened
                # or - default use all bands when no band region is present
                # if len(self.band_regions) == 0: # add a band region covering all bands if none is present
                #    self.add_band_region(np.min(self.wl), np.max(self.wl))
                if len(self.band_regions) > 0:
                    # this method tries to blit them
                    #for band_region_key in self.band_regions.keys():
                    #    ax.draw_artist(self.band_regions[band_region_key])  # adds the new band_region to the axes
                    #fig.canvas.blit(ax.bbox)  # re-draws just what is needed
                    # add the band regions
                    for band_region_key in self.band_regions.keys():
                        [l, r] = self.get_left_right(self.band_regions[band_region_key])
                        self.subplot_material_id.axvspan(l, r, facecolor='g', alpha=0.15)

                self.MPWidget_material_id.draw()

            else:
                self.subplot_material_id.axes.clear()
                self.MPWidget_material_id.draw()
                self.data_check['pixel spectrum present'] = False

            # validate the data (check that all the required data is present, wavelngths match, etc.)
            self.validate_data()

        # if the current selected tab is feature matching
        if self.widget_central.currentIndex() == 2:
            # compute average pixel spectrum, is spectra are present and material_id is in data_preperation mode
            if (len(self.MPWidget_pixel.getFigure().gca().lines) > 0) and (self.feature_match_mode == 'data_preperation'):
                self.wl = self.MPWidget_pixel.getFigure().gca().lines[0].get_xdata()
                self.average_pixel_spectrum = np.zeros(len(self.wl))
                for line in self.MPWidget_pixel.getFigure().gca().lines:
                    self.average_pixel_spectrum = self.average_pixel_spectrum + line.get_ydata()
                self.average_pixel_spectrum = self.average_pixel_spectrum / len(
                    self.MPWidget_pixel.getFigure().gca().lines)

                # plot in pixel material id viewer
                self.subplot_feature_match.axes.clear()
                self.subplot_feature_match.plot(self.wl, self.average_pixel_spectrum,
                                              color='k',
                                              marker='.',
                                              label='Pixel Spectrum',
                                              linewidth=1)

                # add the features
                for key in self.features.keys():
                    # plot the feature
                    x = self.features[key].xdata
                    y = self.features[key].ydata
                    c = self.features[key].color
                    self.subplot_feature_match.plot(x, y,
                                                    color=c,
                                                    marker='o',
                                                    markersize=15,
                                                    label='Feature ' + str(key),
                                                    linewidth=2,
                                                    alpha=0.5)

                if self.settings.screen_width > 3000:
                    self.subplot_feature_match.axes.legend(fontsize=20)
                else:
                    self.subplot_feature_match.axes.legend()
                self.MPWidget_feature_match.getFigure().tight_layout()
                self.MPWidget_feature_match.draw()
                self.data_check_fm['pixel spectrum present'] = True

                # add a band region
                fig = self.MPWidget_feature_match.getFigure()  # gets the figure in a variable
                ax = self.subplot_feature_match.axes  # get the axis in a variable
                self.background = fig.canvas.copy_from_bbox(ax.bbox)  # get everything currently plotted
                # use this is we want to create a band region spanning all bands when firt opened
                # or - default use all bands when no band region is present
                # if len(self.band_regions) == 0: # add a band region covering all bands if none is present
                #    self.add_band_region(np.min(self.wl), np.max(self.wl))
                if len(self.features) > 0:
                    # this method tries to blit them
                    # for band_region_key in self.band_regions.keys():
                    #    ax.draw_artist(self.band_regions[band_region_key])  # adds the new band_region to the axes
                    # fig.canvas.blit(ax.bbox)  # re-draws just what is needed
                    # add the band regions
                    for feature in self.features.keys():
                        pass
                        # plot the features

                self.MPWidget_feature_match.draw()

            else:
                self.subplot_feature_match.axes.clear()
                self.MPWidget_feature_match.draw()
                self.data_check_fm['pixel spectrum present'] = False

            # validate the data (check that all the required data is present, wavelngths match, etc.)
            self.validate_data_fm()

    def validate_data(self):
        # set parameters
        self.material_id_data_check = True
        validation_text = ''

        # check that a pixel spectrum is present
        if self.data_check['pixel spectrum present'] == True:
            validation_text = validation_text+'<p><font color="green">Pixel spectrum is present.</font> (pass)</p><p> </p>'
        else:
            self.material_id_data_check = False
            validation_text = validation_text+('<p><font color="red">Pixel spectrum not present.</font></p>'+
                                   '<p>(You must paste pixel spectrul to identify into the "Pixel Spectrum" plot on the Data Tab).</p><p> </p>')

        # check that libraries have been selected
        self.data_check['libraries selected'] = len(self.table_view.selectedIndexes())>0
        if self.data_check['libraries selected'] == True:
            validation_text = validation_text+'<p><font color="green">Libraries selected.</font> (pass)</p><p> </p>'
        else:
            self.material_id_data_check = False
            validation_text = validation_text+('<p><font color="red">Libraries not selected.</font></p>'+
                                   '<p>(You must open and select at least one library in the Data Tab.  Libraries are selected by clicking so they are highlighted.)</p><p> </p>')

        # check that an image is present to provide statistics and endmembers
        self.data_check['image present'] = (self.im is not None)
        if self.data_check['image present'] == True:
            validation_text = validation_text+'<p><font color="green">Image is present.</font> (pass)</p><p> </p>'
        else:
            validation_text = validation_text+('<p><font color="orange">Image is not present.</font></p>'+
                                   '<p>(Statistics-based metrics cannot be computed without an iamge.  Select an image file at the top of the data tab for full results.)</p><p> </p>')

        # check if endmembers are present
        self.data_check['endmembers present'] = (len(self.MPWidget_endmember.getFigure().gca().lines) > 0)
        if self.data_check['endmembers present'] == True:
            validation_text = validation_text+('<p><font color="green">Endmembers are present.</font> (pass - Manual endmembers will be used along with image endmembers for background removal.  Include 10+ endmembers from background pixels for best results.)</p><p> </p>')
        else:
            if self.data_check['image present'] == True:
                validation_text = validation_text+('<p><font color="orange">Endmembers not present.</font> (pass - Image endmembers will be used for background removal.  Include 10+ endmembers from background pixels for best results.)</p><p> </p>')
            else:
                validation_text = validation_text+('<p><font color="orange">Endmembers not present.</font> (pass - No background removal will be computed without an image or endmebers.)</p><p> </p>')

        # check that pixel wavelengths match the image (if both are present)
        if self.data_check['pixel spectrum present'] and self.data_check['image present']:
            self.data_check['pixel image wl match'] = False
            wl_pixel = self.MPWidget_pixel.getFigure().gca().lines[0].get_xdata()
            wl_image = self.im.bands.centers
            if len(wl_pixel) == len(wl_image):
                if np.sum(abs(wl_pixel-wl_image)) == 0:
                    self.data_check['pixel image wl match'] = True
            if self.data_check['pixel image wl match'] == True:
                validation_text = validation_text+'<p><font color="green">Pixel and image wavelengths match.</font> (pass)</p><p> </p>'
            else:
                self.material_id_data_check = False
                validation_text = validation_text+('<p><font color="red">Pixel and image wavelengths do not match.</font></p>'+
                                       '<p>(Usually pixel spectrum should come from the selected image.)</p><p> </p>')

        # check that pixel wavelengths match the endmembers (if both are present)
        if self.data_check['pixel spectrum present'] and self.data_check['endmembers present']:
            self.data_check['pixel endmemebers wl match'] = False
            wl_pixel = self.MPWidget_pixel.getFigure().gca().lines[0].get_xdata()
            wl_endmembers = self.MPWidget_endmember.getFigure().gca().lines[0].get_xdata()
            if len(wl_pixel) == len(wl_endmembers):
                if np.sum(abs(wl_pixel-wl_endmembers)) == 0:
                    self.data_check['pixel endmemebers wl match'] = True
            if self.data_check['pixel endmemebers wl match'] == True:
                validation_text = validation_text+'<p><font color="green">Pixel and endmembers wavelengths match.</font> (pass)</p><p> </p>'
            else:
                self.material_id_data_check = False
                validation_text = validation_text+('<p><font color="orange">Pixel and endmember wavelengths do not match.</font></p>'+
                                       '<p>(Endmembers will be resampled to match the pixel.)</p><p> </p>')

        # check that library wavelengths cover the range of the pixel (if both are present)
        if self.data_check['pixel spectrum present'] and self.data_check['libraries selected']:
            self.data_check['pixel libraries wl consistent'] = True
            pixel_wl = self.MPWidget_pixel.getFigure().gca().lines[0].get_xdata()
            selected_libraries_indices =  sorted(set(index.row() for index in self.table_view.selectedIndexes()))
            for rowIdx in selected_libraries_indices:
                library_file_name = self.table_view.item(rowIdx, 8).text()
                lib_wl = self.spectral_libraries[library_file_name].bands.centers
                lib_wl = [wl * float(self.table_view.item(rowIdx, 0).text()) for wl in lib_wl]
                if np.min(lib_wl) > np.min(pixel_wl):
                    self.data_check['pixel libraries wl consistent'] = False
                if np.max(lib_wl) < np.max(pixel_wl):
                    self.data_check['pixel libraries wl consistent'] = False
            if self.data_check['pixel libraries wl consistent'] == True:
                validation_text = validation_text+'<p><font color="green">Library wavelengths cover all pixel wavelengths.</font> (pass)</p><p> </p>'
            else:
                self.material_id_data_check = False
                validation_text = validation_text+('<p><font color="orange">Pixel wavelengths extend beyond some library wavelengths.</font></p>'+
                                       '<p>(Library resampling may cause innacuracies.  Check the libraries.)</p><p> </p>')

        if self.material_id_data_check == True:
            try:
                # disconnect the button clicked signal from all functions
                self.btn_compute_identification.clicked.disconnect()
            except:
                # if the button clicked signal was not connecte to any functions, this handles the error
                pass
            self.btn_compute_identification.clicked.connect(self.compute_identification)
            self.btn_compute_identification.setStyleSheet("background-color: #d2e0d3")
            validation_text = validation_text + ('<p><font color="green">The spectra are ready for material identificaiton.</font>  '+
                                                 'If desired, left-click on the plot to create or modify band subsets or '+
                                                 'right-click to remove band subsets.  The full spectral wavelengths '+
                                                 'will be used if no subsetss are created.</p>')
        else:
            try:
                self.btn_compute_identification.clicked.disconnect(self.compute_identification)
            except:
                pass
            self.btn_compute_identification.setStyleSheet("background-color: #d9aaaa")

        # set the data validation notificaiton text
        self.label_material_id_notifications.setText(validation_text)

    def populate_table(self):
        for key in self.spectral_libraries.keys():
            self.add_to_table(self.spectral_libraries[key])

    def add_to_table(self, lib):

        # check if the library is already present
        nRows = self.table_view.rowCount()
        vheaders = []
        fnames = []
        for i in range(nRows):
            vheaders.append(self.table_view.verticalHeaderItem(i).text())
            fnames.append(self.table_view.item(i,8).text())
        if lib.params.filename in fnames:
            rowID = fnames.index(lib.params.filename)
            self.table_view.selectRow(rowID)
            return

        # add the metadata for the new row
        self.table_view.insertRow(nRows)
        vheaders.append(os.path.basename(lib.params.filename))
        self.table_view.setVerticalHeaderLabels(vheaders)
        item0 = QTableWidgetItem("1")
        item0.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled )
        item1 = QTableWidgetItem("1")
        item1.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled )
        item2 = QTableWidgetItem("%d"%lib.params.nrows)
        item2.setFlags(Qt.ItemIsSelectable |  Qt.ItemIsEnabled )
        item3 = QTableWidgetItem("%d"%lib.params.ncols)
        item3.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled )
        item4 = QTableWidgetItem("0 - %d"%10**ceil(log10(np.median(lib.spectra))))
        item4.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled )
        item5 = QTableWidgetItem("%f - %f"%(np.min(lib.bands.centers),np.max(lib.bands.centers)))
        item5.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled )
        item6 = QTableWidgetItem("%f - %f"%(np.min(lib.spectra),np.max(lib.spectra)))
        item6.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled )
        item7 = QTableWidgetItem(os.path.dirname(os.path.abspath(lib.params.filename)))
        item7.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled )
        item8 = QTableWidgetItem(lib.params.filename)
        item8.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled )
        # put the items in the table
        self.table_view.setItem(nRows, 0, item0)
        self.table_view.setItem(nRows, 1, item1)
        self.table_view.setItem(nRows, 2, item2)
        self.table_view.setItem(nRows, 3, item3)
        self.table_view.setItem(nRows, 4, item4)
        self.table_view.setItem(nRows, 5, item5)
        self.table_view.setItem(nRows, 6, item6)
        self.table_view.setItem(nRows, 7, item7)
        self.table_view.setItem(nRows, 8, item8)
        # compute the scale factor for the new row
        
        self.spectral_libraries[lib.params.filename] = lib
        self.compute_scale_factors(idx=nRows)

    def compute_scale_factors(self, idx=None):

        # if there are pixel spectra in the pixel plot
        if len(self.MPWidget_pixel.getFigure().gca().lines) > 0:
            # compute average pixel spectrum (that we want to rescale libraries to)
            pixel_wl = self.MPWidget_pixel.getFigure().gca().lines[0].get_xdata()
            self.average_pixel_spectrum = np.zeros(len(pixel_wl))
            for line in self.MPWidget_pixel.getFigure().gca().lines:
                self.average_pixel_spectrum = self.average_pixel_spectrum + line.get_ydata()
            self.average_pixel_spectrum = self.average_pixel_spectrum / len(self.MPWidget_pixel.getFigure().gca().lines)
            pixel_scale = 10**ceil(log10(np.median(self.average_pixel_spectrum)))

            if idx is None:
                nRows = self.table_view.rowCount()
                for rowIdx in range(nRows):

                    # add the scale factor for wl
                    library_file_name = self.table_view.item(rowIdx, 8).text()
                    lib_wl = self.spectral_libraries[library_file_name].bands.centers
                    scale_factor_x = materialIdentification.get_wl_scale_factor(lib_wl,pixel_wl)
                    item0 = QTableWidgetItem(str(scale_factor_x))
                    item0.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
                    self.table_view.setItem(rowIdx, 0, item0)

                    # add the scale factor for y-values
                    library_scale_range = self.table_view.item(rowIdx, 4).text()
                    library_scale = int(library_scale_range[4:])
                    scale_factor_y = float(pixel_scale)/library_scale
                    item1 = QTableWidgetItem(str(scale_factor_y))
                    item1.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
                    self.table_view.setItem(rowIdx, 1, item1)
            else:

                # add the scale factor for wl
                library_file_name = self.table_view.item(idx, 8).text()
                lib_wl = self.spectral_libraries[library_file_name].bands.centers
                scale_factor_x = materialIdentification.get_wl_scale_factor(lib_wl,pixel_wl)
                item0 = QTableWidgetItem(str(scale_factor_x))
                item0.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
                self.table_view.setItem(idx, 0, item0)

                # add the scale factor for y-values
                library_scale_range = self.table_view.item(idx, 4).text()
                library_scale = int(library_scale_range[4:])
                scale_factor_y = float(pixel_scale)/library_scale
                item1 = QTableWidgetItem(str(scale_factor_y))
                item1.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
                self.table_view.setItem(idx, 1, item1)

    def select_image(self):
        # get file name from user and validity check
        if self.imageDir is None:
            fname_image = QFileDialog.getOpenFileName(self, "Choose an image")
        else:
            try:
                fname_image = QFileDialog.getOpenFileName(self, "Choose an image", self.imageDir)
            except:
                fname_image = QFileDialog.getOpenFileName(self, "Choose an image")
        if fname_image == '':
            return
        fname_image_orig = fname_image[0]
        fname_image, ok = specTools.is_image_file(fname_image_orig)
        if not ok:
            print(fname_image[0])
            print(fname_image[1])
            QMessageBox.warning(self,"File is not valid ENVI image",
                "File Name: %s"%(os.path.basename(fname_image)))

        self.statusBar.showMessage('Reading image data...')
        self.progressBar.setValue(20)
        self.line_image_fname.setText(fname_image_orig)
        # read image data to variables
        self.im = envi.open(fname_image+'.hdr')
        self.im = specTools.apply_bbl(self.im)
        
        self.im_arr = specTools.envi_load(self.im)
        self.data_check['image present'] = True

        # open the image in an imageViewer
        im_dict = {'fname_image':fname_image, 'im':self.im, 'im_arr':self.im_arr}
        self.openedImageInMaterialId.emit(im_dict)

        singelThread = False
        if singelThread == True:
            # compute the statistics
            nEndmembers = 20
            self.statusBar.showMessage('Computing image statistics...')
            self.progressBar.setValue(40)
            self.pc = specTools.compute_screened_pca(self.im_arr,False)
            self.statusBar.showMessage('Computing whitening matrix...')
            self.progressBar.setValue(60)
            self.W = specTools.compute_whitening(self.pc,False)
            self.statusBar.showMessage('Computing image endmembers...')
            self.progressBar.setValue(80)
            image = specTools.image_struc()
            image.im = self.im
            image.arr = self.im_arr
            self.endmembers = specTools.SMACC_endmembers(image, nEndmembers)
            self.progressBar.setValue(100)
            self.statusBar.clearMessage()
            self.progressBar.setValue(0)
        else:
            self.mainProcessingThread = self.mainProcessingThreadDef(self.im, self.im_arr, self.nEndmembers)
            self.mainProcessingThread.updateProgress.connect(self.updateProgress)
            self.mainProcessingThread.updatePC.connect(self.updatePC)
            self.mainProcessingThread.updateW.connect(self.updateW)
            self.mainProcessingThread.updateEndmembers.connect(self.updateEndmembers)
            self.mainProcessingThread.start()

    class mainProcessingThreadDef(QThread):

        # These are the signals that will be emitted during the processing.
        updateProgress = pyqtSignal(str, int)
        updatePC = pyqtSignal(object)
        updateW = pyqtSignal(object)
        updateEndmembers = pyqtSignal(object)

        # You can do any extra things in this init you need.
        def __init__(self, im, im_arr, nEndmembers):
            QThread.__init__(self)
            self.im = im
            self.im_arr = im_arr
            self.nEndmembers = nEndmembers

        # A QThread is run by calling it's start() function, which calls this run()
        # function in it's own "thread".
        def run(self):

            self.updateProgress.emit('Computing image statistics...', 40)
            self.pc = specTools.compute_screened_pca(self.im_arr,False)
            self.updatePC.emit(self.pc)

            self.updateProgress.emit('Computing whitening matrix...', 60)
            self.W = specTools.compute_whitening(self.pc,False)
            self.updateW.emit(self.W)

            self.updateProgress.emit('Computing image endmembers...', 80)
            image = specTools.image_struc()
            image.im = self.im
            image.arr = self.im_arr
            self.endmembers = specTools.SMACC_endmembers(image, self.nEndmembers)
            self.updateEndmembers.emit(self.endmembers)

            self.updateProgress.emit('', 0)

    def updatePC(self, pc):
        self.pc = pc

    def updateW(self, W):
        self.W = W

    def updateEndmembers(self, endmembers):
        self.endmembers = endmembers

    def updateProgress(self, text, number):
        if number > 0:
            self.statusBar.showMessage(text)
            self.progressBar.setValue(number)
        else:
            self.progressBar.setValue(100)
            self.statusBar.clearMessage()
            self.progressBar.setValue(0)
        print('progress has been set.')

    def clear_results(self):
        # set the mode back to data preperation
        self.material_id_mode = 'data_preperation'

        # create data variables
        self.selected_library_spectrum = None
        self.selected_library_br_spectrum = None
        self.band_region_wl_ranges = []
        self.pasteSpectrumRequestSentPixel = False
        self.pasteSpectrumRequestSentEndmember = False
        self.mousePressedPixel = False
        self.mousePressedEndmember = False
        self.mousePressedLeft = False
        self.mousePressedRight = False
        self.right_zoom_pixel = False
        self.right_zoom_endmember = False
        self.data_check = {'pixel spectrum present':False, 'libraries selected':False, 'image present':False,
                           'pixel image wl match':False, 'endmembers present':False, 'pixel endmemebers wl match':False,
                           'pixel libraries wl consistent':False}
        self.material_id_data_check = False        

        # clear the results table
        self.material_id_results_table.itemSelectionChanged.disconnect()
        self.material_id_results_table.clearSelection()
        self.material_id_results_table.setRowCount(0)
        self.material_id_results_table.itemSelectionChanged.connect(self.selection_changed)

        # reset the view as if the tab changed
        self.tab_changed()

        # set clear results button to standard color
        self.btn_clear_results.setStyleSheet("background-color: %s" % self.unclikcked_button_color.name())


    def select_library(self):
        # Get the library name
        lib, ok = specTools.select_library(self, prompt="Choose a library")
        if ok:
            self.libraryDir = os.path.dirname(os.path.abspath(lib.params.filename))
        else: return
        # emit signal that this library is opened
        lib_dict = {'lib': lib}
        self.openedLibraryInMaterialId.emit(lib_dict)
        # add the data to the table and spectral_libraries dict
        self.add_to_table(lib)

    def clear_pixel_spectra(self):
        self.subplot_pixel.axes.clear()
        self.MPWidget_pixel.draw()

    def clear_endmember_spectra(self):
        self.subplot_endmember.axes.clear()
        self.MPWidget_endmember.draw()

    def paste_spectrum_request_pixel(self):
            self.pasteSpectrumRequestSentPixel = True
            self.pasteSpectrumRequest.emit(1)

    def paste_spectrum_request_endmember(self):
            self.pasteSpectrumRequestSentEndmember = True
            self.pasteSpectrumRequest.emit(1)

    def paste_spectrum(self, pasted_spectrum):
        for key in pasted_spectrum.keys():

            pasted_spectrum_Line2D = pasted_spectrum[key]

            if self.pasteSpectrumRequestSentEndmember:
                self.subplot_endmember.plot(pasted_spectrum_Line2D._x,pasted_spectrum_Line2D._y,
                                  color = pasted_spectrum_Line2D._color,
                                  label = pasted_spectrum_Line2D._label,
                                  linestyle = pasted_spectrum_Line2D._linestyle,
                                  linewidth = pasted_spectrum_Line2D._linewidth)
                if self.settings.screen_width > 3000:
                    self.subplot_endmember.axes.legend(fontsize=20)
                else:
                    self.subplot_endmember.axes.legend()
                self.MPWidget_endmember.draw()
            elif self.pasteSpectrumRequestSentPixel:
                self.subplot_pixel.plot(pasted_spectrum_Line2D._x,pasted_spectrum_Line2D._y,
                                  color = pasted_spectrum_Line2D._color,
                                  label = pasted_spectrum_Line2D._label,
                                  linestyle = pasted_spectrum_Line2D._linestyle,
                                  linewidth = pasted_spectrum_Line2D._linewidth)
                if self.settings.screen_width > 3000:
                    self.subplot_endmember.axes.legend(fontsize=20)
                else:
                    self.subplot_endmember.axes.legend()
                self.MPWidget_pixel.draw()
                # recompute the library scale factors
                self.compute_scale_factors()
            else:
                try:
                    self.spectral_plot.paste_spectrum(pasted_spectrum)
                except:
                    pass

        # record that the request for paste spectrum has been completed
        self.pasteSpectrumRequestSentEndmember = False
        self.pasteSpectrumRequestSentPixel = False

    def copy_spectrum(self, copied_spectrum):
        # emit the signal to send data back
        self.copiedSpectrum.emit(copied_spectrum)

    def paste_spectrum_request(self):
        # emit the signal to send data back
        self.pasteSpectrumRequest.emit(1)

    def paste_spectrum_spectralViewer(self, pasted_spectrum):
        self.pasteSpectrum_spectralViewer.emit(pasted_spectrum)

    def open_in_spectralViewer(self):
        if self.data_check['pixel spectrum present'] == False: # if no pixel spectrum is present, do nothing
            return

        self.id_wl = self.MPWidget_material_id.getFigure().gca().lines[0].get_xdata()
        self.id_pixel_spectrum = self.MPWidget_material_id.getFigure().gca().lines[0].get_ydata()
        if not hasattr(self, 'spectral_plot'):
            # This is the case if not spectral plot has been made
            self.spectral_plot = spectraViewer.specPlot(parent=self, settings=self.settings)
            self.spectral_plot.setStyleSheet('QMainWindow{padding: 0px}')
            self.spectral_plot.copiedSpectrum.connect(self.copy_spectrum)
            self.spectral_plot.pasteSpectrumRequest.connect(self.paste_spectrum_request)
            #self.pasteSpectrum.connect(self.spectral_plot.paste_spectrum)
            self.spectral_plot.subplot.plot(self.id_wl,self.id_pixel_spectrum, label='Pixel Spectrum', color='k', marker='.', linewidth=1)
            try:
                self.spectral_plot.subplot.plot(self.id_wl,self.selected_library_spectrum, label=self.selected_library_name[0:70], color='r', linewidth=1)
                self.spectral_plot.subplot.plot(self.id_wl,self.selected_library_br_spectrum, label='Background Removed: '+self.selected_library_name[0:50], color='b', linewidth=1)
            except:
                pass
            if self.settings.screen_width > 3000:
                self.spectral_plot.subplot.axes.legend(fontsize=20)
            else:
                self.spectral_plot.subplot.axes.legend()
            self.spectral_plot.MPWidget.draw()
        elif self.spectral_plot.isHidden():
            # This is the case if not spectral plot has been made
            self.spectral_plot = spectraViewer.specPlot(parent=self, settings=self.settings)
            self.spectral_plot.setStyleSheet('QMainWindow{padding: 0px}')
            self.spectral_plot.copiedSpectrum.connect(self.copy_spectrum)
            self.spectral_plot.pasteSpectrumRequest.connect(self.paste_spectrum_request)
            #self.pasteSpectrum.connect(self.spectral_plot.paste_spectrum)
            self.spectral_plot.subplot.plot(self.id_wl,self.id_pixel_spectrum, label='Pixel Spectrum', color='k', marker='.', linewidth=1)
            try:
                self.spectral_plot.subplot.plot(self.id_wl,self.selected_library_spectrum, label=self.selected_library_name[0:70], color='r', marker='.', linewidth=1)
                self.spectral_plot.subplot.plot(self.id_wl,self.selected_library_br_spectrum, label='Background Removed: '+self.selected_library_name[0:50], color='b', marker='.', linewidth=1)
            except:
                pass
            if self.settings.screen_width > 3000:
                self.spectral_plot.subplot.axes.legend(fontsize=20)
            else:
                self.spectral_plot.subplot.axes.legend()
            self.spectral_plot.MPWidget.draw()
        else:
            try:
                self.spectral_plot.subplot.plot(self.id_wl,self.selected_library_spectrum, label=self.selected_library_name, color='g', marker='.', linewidth=1)
                self.spectral_plot.subplot.plot(self.id_wl,self.selected_library_br_spectrum, label='Background Removed: '+self.selected_library_name, color='b', marker='.', linewidth=1)
            except:
                pass
            if self.settings.screen_width > 3000:
                self.spectral_plot.subplot.axes.legend(fontsize=20)
            else:
                self.spectral_plot.subplot.axes.legend()
            self.spectral_plot.MPWidget.draw()

    def compute_identification(self):

        # get the band region wl ranges
        self.band_region_wl_ranges = []
        for band_region_key in self.band_regions.keys():
            [l, r] = self.get_left_right(self.band_regions[band_region_key])
            self.band_region_wl_ranges.append([np.min([l,r]),np.max([l,r])])
        # compute the identificaiton
        id_result = materialIdentification.single_material_identificaiton(self)

        # attach results to self
        # sets the wavelengths and pixel spectrum for all plots
        self.id_wl = self.MPWidget_material_id.getFigure().gca().lines[0].get_xdata()
        self.id_pixel_spectrum = self.MPWidget_material_id.getFigure().gca().lines[0].get_ydata()
        # sets the results
        self.spectra_names = id_result['spectra names']
        self.file_names = id_result['file names']
        self.ACE = id_result['ACE']
        self.spectral_fit = id_result['spectral fit']
        self.MF = id_result['MF']
        self.Corr = id_result['Corr']
        self.probability = id_result['probability']
        self.lib_spectra = id_result['lib spectra']
        self.background_removed_spectra_plot = id_result['background removed spectra plot']

        # add results to table
        self.add_results_to_table()

        # turn off the compute identificaiton button (until the user clears the results)
        try:
            self.btn_compute_identification.clicked.disconnect(self.compute_identification)
        except:
            pass
        self.btn_compute_identification.setStyleSheet("background-color: #d9aaaa")
        # color the clear results button green for emphasis
        self.btn_clear_results.setStyleSheet("background-color: #d2e0d3")
        self.material_id_mode = 'analysis'

    def add_results_to_table(self):

        # set up the number of rows
        nRows = len(self.spectra_names)
        self.material_id_results_table.setRowCount(nRows)

        # put the spectra names in the rows (sorting turned off while fililng table)
        self.material_id_results_table.setSortingEnabled(False)
        for row_idx in range(nRows):
            self.material_id_results_table.setItem(row_idx, 0, TableWidgetItem(self.spectra_names[row_idx]))
            self.material_id_results_table.setItem(row_idx, 1, TableWidgetItem('%.3f' % self.probability[row_idx]))
            self.material_id_results_table.setItem(row_idx, 2, TableWidgetItem('%.2f' % self.ACE[row_idx]))
            self.material_id_results_table.setItem(row_idx, 3, TableWidgetItem('%.2f' % self.spectral_fit[row_idx]))
            self.material_id_results_table.setItem(row_idx, 4, TableWidgetItem('%.2f' % self.Corr[row_idx]))
            self.material_id_results_table.setItem(row_idx, 5, TableWidgetItem('%.2f' % self.MF[row_idx]))
            self.material_id_results_table.setItem(row_idx, 6, TableWidgetItem(self.file_names[row_idx]))
            self.material_id_results_table.setItem(row_idx, 7, TableWidgetItem(str(row_idx)))
            self.material_id_results_table.setItem(row_idx, 8, TableWidgetItem(0))

        self.material_id_results_table.setHorizontalHeaderLabels(['Name','Probability','ACE','Subpixel Spectral Fit','Full Pixel Correlation','Abundnace','Library'])
        self.material_id_results_table.setSortingEnabled(True)

        # sort the table and select the top entry
        self.material_id_results_table.sortByColumn(2,Qt.AscendingOrder)
        self.material_id_results_table.selectRow(0)

        # set the size
        self.material_id_results_table.setColumnWidth(0, 800)

    def cell_was_clicked(self, row, column):
        self.plot_pixel_with_libray_spectra(row)

    def selection_changed(self):
        # get the row that was selected
        indices = self.material_id_results_table.selectedIndexes()
        if len(indices) > 0:
            row = indices[0].row()
            self.plot_pixel_with_libray_spectra(row)

    def plot_pixel_with_libray_spectra(self, row):
        # clear the axis
        self.subplot_material_id.axes.clear()

        # plot the library spectrum
        selected_spectrum_index = self.material_id_results_table.item(row, 7).text()
        self.selected_library_spectrum = self.lib_spectra[int(selected_spectrum_index)]
        self.selected_library_br_spectrum = self.background_removed_spectra_plot[int(selected_spectrum_index)]
        self.selected_library_name = self.spectra_names[int(selected_spectrum_index)]
        if self.selected_library_spectrum is not None:
            # plot the pixel spectrum
            self.subplot_material_id.plot(self.id_wl,self.id_pixel_spectrum,'k', marker='.', label='Pixel Spectrum', lw=1)
            self.subplot_material_id.plot(self.id_wl,self.selected_library_spectrum,'r', marker='.', label=self.selected_library_name[0:70], lw=1)
            self.subplot_material_id.plot(self.id_wl,self.selected_library_br_spectrum,'b', marker='.', label='Background Removed: '+self.selected_library_name[0:50], lw=1)
            # add the band regions
            for band_region_key in self.band_regions.keys():
                [l, r] = self.get_left_right(self.band_regions[band_region_key])
                self.subplot_material_id.axvspan(l, r, facecolor='g', alpha=0.05)
        else:
            # plot the pixel spectrum
            self.subplot_material_id.plot(self.id_wl,self.id_pixel_spectrum,'k', marker='.', label='Pixel Spectrum', lw=1)
            # add the band regions
            for band_region_key in self.band_regions.keys():
                [l, r] = self.get_left_right(self.band_regions[band_region_key])
                self.subplot_material_id.axvspan(l, r, facecolor='g', alpha=0.15)

        self.subplot_material_id.set_xlabel('Wavelength')
        if self.settings.screen_width > 3000:
            self.subplot_material_id.axes.legend(fontsize=20)
        else:
            self.subplot_material_id.axes.legend()
        self.MPWidget_material_id.getFigure().tight_layout()

        self.MPWidget_material_id.draw()

    def event_update_material_id_plot(self,dummy):
        # update the plot when cursor enters the plot and no menu tools (ie zoom/pan) are selected
        if self.MPWidget_material_id.toolbar._active is None:  # check that no toolbar buttons are selected
            self.update_material_id_plot()

    def update_material_id_plot(self):
        if self.data_check['pixel spectrum present']:
            # plot in pixel material id viewer
            self.subplot_material_id.axes.clear()
            if self.material_id_mode == 'analysis':
                # we are in analysis mode - so plot the pixel and selected_library_spectrum and band regions in light green
                # plot the pixel spectrum
                self.subplot_material_id.plot(self.id_wl, self.id_pixel_spectrum, 'k', marker='.',
                                              label='Pixel Spectrum', lw=1)
                self.subplot_material_id.plot(self.id_wl, self.selected_library_spectrum, 'r', marker='.',
                                              label=self.selected_library_name[0:70], lw=1)
                self.subplot_material_id.plot(self.id_wl, self.selected_library_br_spectrum, 'b', marker='.',
                                              label='Background Removed: '+self.selected_library_name[0:50], lw=1)
                if self.settings.screen_width > 3000:
                    self.subplot_material_id.axes.legend(fontsize=20)
                else:
                    self.subplot_material_id.axes.legend()
                self.MPWidget_material_id.getFigure().tight_layout()
                self.MPWidget_material_id.draw()

                # get the background
                fig = self.MPWidget_material_id.getFigure()  # gets the figure in a variable
                ax = self.subplot_material_id.axes  # get the axis in a variable
                self.background = fig.canvas.copy_from_bbox(ax.bbox)  # get everything currently plotted

                # add the band regions
                for band_region_key in self.band_regions.keys():
                    [l, r] = self.get_left_right(self.band_regions[band_region_key])
                    self.subplot_material_id.axvspan(l, r, facecolor='g', alpha=0.05)
            else:
                # we are in data preperation mode, so plot the averaged pixel spectrum with band selection regions
                # plot the pixel spectrum
                self.subplot_material_id.plot(self.wl, self.average_pixel_spectrum, 'k', marker='.',
                                              label='Pixel Spectrum', lw=1)
                if self.settings.screen_width > 3000:
                    self.subplot_material_id.axes.legend(fontsize=20)
                else:
                    self.subplot_material_id.axes.legend()
                self.MPWidget_material_id.getFigure().tight_layout()
                self.MPWidget_material_id.draw()

                # get the background
                fig = self.MPWidget_material_id.getFigure()  # gets the figure in a variable
                ax = self.subplot_material_id.axes  # get the axis in a variable
                self.background = fig.canvas.copy_from_bbox(ax.bbox)  # get everything currently plotted

                # add the band regions
                for band_region_key in self.band_regions.keys():
                    [l, r] = self.get_left_right(self.band_regions[band_region_key])
                    self.subplot_material_id.axvspan(l, r, facecolor='g', alpha=0.15)

            self.subplot_material_id.set_xlabel('Wavelength')
            if self.settings.screen_width > 3000:
                self.subplot_material_id.axes.legend(fontsize=20)
            else:
                self.subplot_material_id.axes.legend()

            self.MPWidget_material_id.getFigure().tight_layout()
            self.MPWidget_material_id.show()
            self.MPWidget_material_id.draw()

    def add_band_region(self, a, b):
        band_region = self.subplot_material_id.axvspan(a, b, facecolor='g', alpha=0.15)

        # find the smallest integer that is not currently a key
        key_found = False
        search_key = 0
        while key_found == False:
            if str(search_key) not in self.band_regions.keys():
                key_found = True
            else:
                search_key += 1
        self.band_regions[str(search_key)] = band_region
        return search_key

    def get_left_right(self, band_region):
        xy = band_region.get_xy()
        return [xy[0,0],xy[2,0]]

    def get_selected_region_keys(self, x):
        keys_for_selected_regions = []
        for key in self.band_regions.keys():
            band_region = self.band_regions[key]
            [l,r] = self.get_left_right(band_region)
            if (x > np.min([l,r])) and (x < np.max([l,r])):
                keys_for_selected_regions.append(key)
        return keys_for_selected_regions

    def get_closest_region(self, x):
        dist = 2*(np.max(self.wl) - np.min(self.wl))
        tol = 0.01*(np.max(self.wl) - np.min(self.wl))
        band_region_closest = None
        side = None
        xy = None
        in_region_check = False
        grabbed_edge_check = False
        for key in self.band_regions.keys():
            band_region = self.band_regions[key]
            [l,r] = self.get_left_right(band_region)
            if (x > np.min([l,r])-tol) and (x < np.max([l,r])+tol):
                in_region_check = True
                if (np.abs(x-l) < np.min([dist,tol])):
                    grabbed_edge_check = True
                    dist = np.abs(x-l)
                    band_region_closest = band_region
                    xy = band_region_closest.get_xy()
                    side = 'l'
                if (np.abs(x-r) < np.min([dist,tol])):
                    grabbed_edge_check = True
                    dist = np.abs(x-r)
                    band_region_closest = band_region
                    xy = band_region_closest.get_xy()
                    side = 'r'
        return in_region_check, grabbed_edge_check, band_region_closest, side, xy

    def onMouseDown(self, event):
        # if we are in data preperation mode, add delete band region if requested
        if self.material_id_mode == 'data_preperation':
            # check that no toolbar buttons are selected and that there is an average pixel spectrum present
            if self.MPWidget_material_id.toolbar._active is None and self.data_check['pixel spectrum present']:
                if event.button == 1:
                    self.mousePressedLeft = True

                    if self.first_id_mousepress:
                        # plot in pixel material id viewer
                        self.subplot_material_id.axes.clear()
                        self.subplot_material_id.plot(self.wl, self.average_pixel_spectrum,
                                                      color='k',
                                                      marker='.',
                                                      label='Pixel Spectrum',
                                                      linewidth=1)
                        if self.settings.screen_width > 3000:
                            self.subplot_material_id.axes.legend(fontsize=20)
                        else:
                            self.subplot_material_id.axes.legend()
                        self.MPWidget_material_id.getFigure().tight_layout()
                        self.MPWidget_material_id.draw()
                        fig = self.MPWidget_material_id.getFigure()  # gets the figure in a variable
                        ax = self.subplot_material_id.axes  # get the axis in a variable
                        self.background = fig.canvas.copy_from_bbox(ax.bbox)  # get everything currently plotted
                        self.subplot_material_id.set_xlabel('Wavelength')
                        if self.settings.screen_width > 3000:
                            self.subplot_material_id.axes.legend(fontsize=20)
                        else:
                            self.subplot_material_id.axes.legend()
                        self.MPWidget_material_id.getFigure().tight_layout()
                        self.MPWidget_material_id.draw()

                    [self.in_region_check, self.grabbed_edge_check, self.band_region_closest, self.side, self.xy] = self.get_closest_region(event.xdata)
                    # create a region if we are not in one
                    if self.in_region_check == False:
                        tol = 0.015 * (np.max(self.wl) - np.min(self.wl))
                        self.add_band_region(event.xdata-tol*0.01,event.xdata)
                        [self.in_region_check, self.grabbed_edge_check, self.band_region_closest, self.side, self.xy] = self.get_closest_region(
                            event.xdata)

                    if self.grabbed_edge_check:
                        self.MPWidget_material_id.setCursor(Qt.SplitHCursor)
                        [left,right] = self.get_left_right(self.band_region_closest)
                        if self.side == 'l':
                            self.xy[0,0] = event.xdata
                            self.xy[1,0] = event.xdata
                            self.xy[4,0] = event.xdata
                            self.band_region_closest.set_xy(self.xy)
                        else:
                            self.xy[2,0] = event.xdata
                            self.xy[3,0] = event.xdata
                            self.band_region_closest.set_xy(self.xy)

                        if self.first_id_mousepress:
                            self.MPWidget_material_id.draw()
                        else:
                            fig = self.MPWidget_material_id.getFigure()
                            ax = self.subplot_material_id.axes  # get the axis in a variable
                            fig.canvas.restore_region(self.background)
                            # draw and blit the band regions
                            for band_region_key in self.band_regions.keys():
                                ax.draw_artist(self.band_regions[band_region_key])  # adds the band_region to the axes
                            fig.canvas.blit(ax.bbox) # re-draws just what is needed

                        self.MPWidget_material_id.setCursor(Qt.SplitHCursor)
                    self.first_id_mousepress = False

                if event.button == 3:

                    # deleted the selected band regions
                    for key in self.get_selected_region_keys(event.xdata):
                        del self.band_regions[key]
                    # redraw the plot (first background, then bands regions using blit)
                    fig = self.MPWidget_material_id.getFigure()
                    ax = self.subplot_material_id.axes  # get the axis in a variable
                    fig.canvas.restore_region(self.background)
                    # draw and blit the band regions
                    for band_region_key in self.band_regions.keys():
                        ax.draw_artist(self.band_regions[band_region_key])  # adds the band_region to the axes
                    fig.canvas.blit(ax.bbox)  # re-draws just what is needed

                    self.mousePressedRight = True
                    self.MPWidget_material_id.setCursor(Qt.ForbiddenCursor)

    def onMouseUp(self, event):
        # if we are in data preperation mode, handle the button event
        if self.material_id_mode == 'data_preperation':
            if self.MPWidget_material_id.toolbar._active is None:  # check that no toolbar buttons are selected
                self.mousePressedLeft = False
                self.mousePressedRight = False
                self.grabbed_edge_check = False
                self.MPWidget_material_id.setCursor(Qt.ArrowCursor)

    def onMouseMove(self, event):
        # if we are in data preperation mode, handle the button event for modifying a region
        if self.material_id_mode == 'data_preperation':
            # check that no toolbar buttons are selected and that the left mouse button it pressed
            if self.MPWidget_material_id.toolbar._active is None and self.mousePressedLeft:

                # if no edge is grabbed, see if we are close enough to an edge to grab one
                if self.grabbed_edge_check == False:
                    [self.in_region_check, self.grabbed_edge_check, self.band_region_closest, self.side,
                     self.xy] = self.get_closest_region(event.xdata)

                if self.grabbed_edge_check == True:
                    [left, right] = self.get_left_right(self.band_region_closest)
                    if self.side == 'l':
                        self.xy[0, 0] = event.xdata
                        self.xy[1, 0] = event.xdata
                        self.xy[4, 0] = event.xdata
                        self.band_region_closest.set_xy(self.xy)
                    else:
                        self.xy[2, 0] = event.xdata
                        self.xy[3, 0] = event.xdata
                        self.band_region_closest.set_xy(self.xy)

                    fig = self.MPWidget_material_id.getFigure()
                    ax = self.subplot_material_id.axes  # get the axis in a variable
                    fig.canvas.restore_region(self.background)
                    # draw and blit the band regions
                    for band_region_key in self.band_regions.keys():
                        ax.draw_artist(self.band_regions[band_region_key])  # adds the band_region to the axes
                    fig.canvas.blit(ax.bbox)  # re-draws just what is needed

    def resized_event_handler(self):
        self.update_material_id_plot()

    def search_and_sort_spectra_names(self):
        nRows = self.material_id_results_table.rowCount()
        if nRows > 0:
            query, ok = QInputDialog.getText(self, "Enter words to search for", "Query words:", QLineEdit.Normal, "")
            if not ok:
                return
            self.material_id_results_table.sortItems(1, order=Qt.AscendingOrder)
            query = query.lower()
            snames = [self.material_id_results_table.item(idx,0).text().lower() for idx in range(nRows)]
            matchScores = specTools.fuzzy_string_match(query, snames)
            for row_idx in range(nRows):
                self.material_id_results_table.setItem(row_idx, 8, TableWidgetItem('%.3f' % matchScores[row_idx])  )
            self.material_id_results_table.sortItems(8, order=Qt.AscendingOrder)








### - Feature Building / Matching Code - ###



    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.feature_building_status = False
            self.MPWidget_feature_match.setCursor(QCursor(Qt.ArrowCursor))
            self.cursor = Cursor(self.subplot_feature_match.axes, useblit=True, color='blue', linewidth=1)
            self.MPWidget_feature_match.draw()

    def validate_data_fm(self):
        # set parameters
        self.feature_match_data_check = True
        validation_text_fm = ''

        # check that a pixel spectrum is present
        if self.data_check_fm['pixel spectrum present'] == True:
            validation_text_fm = validation_text_fm+'<p><font color="green">Pixel spectrum is present.</font> (pass)</p><p> </p>'
        else:
            self.feature_match_data_check = False
            validation_text_fm = validation_text_fm+('<p><font color="red">Pixel spectrum not present.</font></p>'+
                                   '<p>(You must paste pixel spectrul to identify into the "Pixel Spectrum" plot on the Data Tab).</p><p> </p>')

        # check that libraries have been selected
        self.data_check_fm['libraries selected'] = len(self.table_view.selectedIndexes())>0
        if self.data_check_fm['libraries selected'] == True:
            validation_text_fm = validation_text_fm+'<p><font color="green">Libraries selected.</font> (pass)</p><p> </p>'
        else:
            self.feature_match_data_check = False
            validation_text_fm = validation_text_fm+('<p><font color="red">Libraries not selected.</font></p>'+
                                   '<p>(You must open and select at least one library in the Data Tab.  Libraries are selected by clicking so they are highlighted.)</p><p> </p>')

        # check that library wavelengths cover the range of the pixel (if both are present)
        if self.data_check_fm['pixel spectrum present'] and self.data_check_fm['libraries selected']:
            self.data_check_fm['pixel libraries wl consistent'] = True
            pixel_wl = self.MPWidget_pixel.getFigure().gca().lines[0].get_xdata()
            selected_libraries_indices =  sorted(set(index.row() for index in self.table_view.selectedIndexes()))
            for rowIdx in selected_libraries_indices:
                library_file_name = self.table_view.item(rowIdx, 8).text()
                lib_wl = self.spectral_libraries[library_file_name].bands.centers
                lib_wl = [wl * float(self.table_view.item(rowIdx, 0).text()) for wl in lib_wl]
                if np.min(lib_wl) > np.min(pixel_wl):
                    self.data_check_fm['pixel libraries wl consistent'] = False
                if np.max(lib_wl) < np.max(pixel_wl):
                    self.data_check_fm['pixel libraries wl consistent'] = False
            if self.data_check_fm['pixel libraries wl consistent'] == True:
                validation_text_fm = validation_text_fm+'<p><font color="green">Library wavelengths cover all pixel wavelengths.</font> (pass)</p><p> </p>'
            else:
                self.feature_match_data_check = False
                validation_text_fm = validation_text_fm+('<p><font color="orange">Pixel wavelengths extend beyond some library wavelengths.</font></p>'+
                                       '<p>(Library resampling may cause innacuracies.  Check the libraries.)</p><p> </p>')

        # modify the compute feature check button as needed
        if self.feature_match_data_check == True:
            try:
                # disconnect the button clicked signal from all functions
                self.btn_compute_identification_fm.clicked.disconnect()
            except:
                # if the button clicked signal was not connecte to any functions, this handles the error
                pass
            self.btn_compute_identification_fm.clicked.connect(self.compute_feature_matching)
            self.btn_compute_identification_fm.setStyleSheet("background-color: #d2e0d3")
            validation_text_fm = validation_text_fm + ('<p><font color="green">The spectra are ready for feature matching.</font>  '+
                                                 'Left-click on the plot to pick a point to start a feature, then '+
                                                 'left-click again for each subsequent point on the feature and  '+
                                                 'right-click or pres ESC to complete the feature.</p>')
        else:
            try:
                self.btn_compute_identification_fm.clicked.disconnect(self.compute_feature_matching)
            except:
                pass
            self.btn_compute_identification_fm.setStyleSheet("background-color: #d9aaaa")

        # set the data validation notificaiton text
        self.label_feature_match_notifications.setText(validation_text_fm)

    def clear_results_fm(self):
        # set the mode back to data preperation
        self.feature_match_mode = 'data_preperation'
        self.feature_building_status = False
        self.MPWidget_feature_match.setCursor(QCursor(Qt.ArrowCursor))
        self.cursor = Cursor(self.subplot_feature_match.axes, useblit=True, color='blue', linewidth=1)
        self.MPWidget_feature_match.draw()

        # create data variables
        self.selected_library_spectrum_fm = None
        self.selected_library_br_spectrum_fm = None
        self.pasteSpectrumRequestSentPixel = False
        self.pasteSpectrumRequestSentEndmember = False
        self.mousePressedPixel = False
        self.mousePressedEndmember = False
        self.mousePressedLeft = False
        self.mousePressedRight = False
        self.right_zoom_pixel = False
        self.right_zoom_endmember = False
        self.data_check_fm = {'pixel spectrum present':False, 'libraries selected':False, 'pixel libraries wl consistent':False}
        self.feature_match_data_check = False
        self.features = {}

        # clear the results table
        self.feature_match_results_table.itemSelectionChanged.disconnect()
        self.feature_match_results_table.clearSelection()
        self.feature_match_results_table.setRowCount(0)
        self.feature_match_results_table.setColumnCount(0)
        self.feature_match_results_table.itemSelectionChanged.connect(self.selection_changed)

        # reset the view as if the tab changed
        self.tab_changed()

        # set clear results button to standard color
        self.btn_clear_results_fm.setStyleSheet("background-color: %s" % self.unclikcked_button_color.name())

    def event_update_feature_match_plot(self,dummy):
        # update the plot when cursor enters the plot and no menu tools (ie zoom/pan) are selected
        if self.first_feature_match_plot == False:
            self.first_feature_match_plot = True
            if self.MPWidget_feature_match.toolbar._active is None:  # check that no toolbar buttons are selected
                self.update_feature_match_plot()

    def update_feature_match_plot(self):
        if self.data_check_fm['pixel spectrum present']:
            # plot in pixel material id viewer
            self.subplot_feature_match.axes.clear()
            if self.feature_match_mode == 'analysis':
                # we are in analysis mode - so plot the pixel and selected_library_spectrum and band regions in light green
                # plot the pixel spectrum
                self.subplot_feature_match.plot(self.id_wl, self.id_pixel_spectrum_fm, 'k', marker='.',
                                              label='Pixel Spectrum', lw=1)
                selected_library_spectrum_fm_plot = (self.selected_library_spectrum_fm - np.nanmean(self.selected_library_spectrum_fm))/np.nanstd(self.selected_library_spectrum_fm)
                selected_library_spectrum_fm_plot = selected_library_spectrum_fm_plot*np.nanstd(self.id_pixel_spectrum_fm) + np.nanmean(self.id_pixel_spectrum_fm)
                self.subplot_feature_match.plot(self.id_wl, selected_library_spectrum_fm_plot, 'r', marker='.',
                                              label=self.selected_library_name[0:70], lw=1)
                self.subplot_feature_match.plot(self.id_wl, self.selected_library_br_spectrum, 'b', marker='.',
                                              label='Background Removed: '+self.selected_library_name[0:50], lw=1)
                if self.settings.screen_width > 3000:
                    self.subplot_feature_match.axes.legend(fontsize=20)
                else:
                    self.subplot_feature_match.axes.legend()
                self.MPWidget_feature_match.getFigure().tight_layout()
                self.MPWidget_feature_match.draw()

                # get the background
                fig = self.MPWidget_feature_match.getFigure()  # gets the figure in a variable
                ax = self.subplot_feature_match.axes  # get the axis in a variable
                self.background = fig.canvas.copy_from_bbox(ax.bbox)  # get everything currently plotted

                # add the features
                for feature in self.features.keys():
                    pass
                    # TO DO - plot the features here
            else:
                # we are in data preperation mode, so plot the averaged pixel spectrum
                # plot the pixel spectrum
                self.subplot_feature_match.plot(self.wl, self.average_pixel_spectrum, 'k', marker='.',
                                              label='Pixel Spectrum', lw=1)
                if self.settings.screen_width > 3000:
                    self.subplot_feature_match.axes.legend(fontsize=20)
                else:
                    self.subplot_feature_match.axes.legend()
                self.MPWidget_feature_match.getFigure().tight_layout()
                self.MPWidget_feature_match.draw()

                # get the background
                fig = self.MPWidget_feature_match.getFigure()  # gets the figure in a variable
                ax = self.subplot_feature_match.axes  # get the axis in a variable
                self.background = fig.canvas.copy_from_bbox(ax.bbox)  # get everything currently plotted

                # add the features
                for key in self.features.keys():
                    # plot the feature
                    x = self.features[key].xdata
                    y = self.features[key].ydata
                    c = self.features[key].color
                    self.subplot_feature_match.plot(x, y,
                                                    color=c,
                                                    marker='o',
                                                    markersize=15,
                                                    label='Feature '+str(key),
                                                    linewidth=2,
                                                    alpha=0.5)

            self.subplot_feature_match.set_xlabel('Wavelength')
            if self.settings.screen_width > 3000:
                self.subplot_feature_match.axes.legend(fontsize=20)
            else:
                self.subplot_feature_match.axes.legend()

            self.MPWidget_feature_match.getFigure().tight_layout()
            self.MPWidget_feature_match.show()
            self.MPWidget_feature_match.draw()

    def onMouseDown_fm(self, event):

        # if we are in data preperation mode, add start feature building
        if self.feature_match_mode == 'data_preperation':
            # check that no toolbar buttons are selected and that there is an average pixel spectrum present
            if self.MPWidget_feature_match.toolbar._active is None and self.data_check_fm['pixel spectrum present']:
                if event.button == 3 or event.button == 1:

                    # find the wl that is closest to the clicked x-value
                    selected_idx = np.argmin(abs(self.wl - event.xdata))
                    selected_x = self.wl[selected_idx]
                    selected_y = self.average_pixel_spectrum[selected_idx]

                    # decide if starting a new feature here, or continuing one
                    # start a new one if needed
                    if self.feature_building_status == False:
                        self.cursor = Cursor(self.subplot_feature_match.axes, useblit=True, color='red', linewidth=1)
                        self.MPWidget_feature_match.setCursor(Qt.CrossCursor)
                        # start building a new feature
                        # get the index for the new feature
                        indices = list(self.features.keys())
                        if len(indices)==0:
                            new_index = 1
                        else:
                            new_index = -1
                            check_index = 1
                            while new_index == -1:
                                if check_index not in indices:
                                    new_index = check_index
                                else:
                                    check_index = check_index + 1

                        feature = feature_struc()
                        feature.xdata = np.asarray([])
                        feature.ydata = np.asarray([])
                        feature.idxdata = np.asarray([])
                        cmap = plt.get_cmap("tab10")
                        feature.color = plt.get_cmap("tab10")(new_index)

                        # start this new feature
                        self.feature_building_current_index = new_index
                        self.features[new_index] = feature

                        # set the attribute indicating that we are in feature building mode
                        self.feature_building_status = True

                    if event.button == 3:
                        self.feature_building_status = False
                        self.MPWidget_feature_match.setCursor(QCursor(Qt.ArrowCursor))
                        self.cursor = Cursor(self.subplot_feature_match.axes, useblit=True, color='blue', linewidth=1)

                    # add the xy coordinates to the list of coordinates for this feature
                    self.features[self.feature_building_current_index].xdata = np.append(self.features[self.feature_building_current_index].xdata, selected_x)
                    self.features[self.feature_building_current_index].ydata = np.append(self.features[self.feature_building_current_index].ydata, selected_y)
                    self.features[self.feature_building_current_index].idxdata = np.append(self.features[self.feature_building_current_index].idxdata, selected_idx)

                    x = self.features[self.feature_building_current_index].xdata
                    y = self.features[self.feature_building_current_index].ydata

                    line_is_present_in_plot = False
                    for line in self.MPWidget_feature_match.getFigure().gca().lines:
                        if line.get_label() == 'Feature '+str(self.feature_building_current_index):
                            line_is_present_in_plot = True
                            line.set_data(x, y)

                    if not line_is_present_in_plot:
                        # plot the feature
                        c = self.features[self.feature_building_current_index].color
                        self.subplot_feature_match.plot(x, y,
                                                        color=c,
                                                        marker='o',
                                                        markersize=15,
                                                        label='Feature '+str(self.feature_building_current_index),
                                                        linewidth=2,
                                                        alpha=0.5)
                        # update the legend
                        if self.settings.screen_width > 3000:
                            self.subplot_feature_match.axes.legend(fontsize=20)
                        else:
                            self.subplot_feature_match.axes.legend()

                    # draw the plot with the new feature points
                    self.MPWidget_feature_match.draw()

    def event_enter_feature_match_plot(self):
        if self.feature_building_status == True:
            self.cursor = Cursor(self.subplot_feature_match.axes, useblit=True, color='red', linewidth=1)
            self.MPWidget_feature_match.setCursor(Qt.CrossCursor)
        else:
            self.MPWidget_feature_match.setCursor(QCursor(Qt.ArrowCursor))
            self.cursor = Cursor(self.subplot_feature_match.axes, useblit=True, color='blue', linewidth=1)

    def event_exit_feature_match_plot(self):
        self.cursor = []

    def onMouseUp_fm(self, event):
        pass

    def remove_data_marker(self, event):
        pass

    def onMouseMove_fm(self, event):
        pass

    def onMouseMove_backup_fm(self, event):
        # do nothing if the event x-y data is None (cursor is not on the plot)
        if event.xdata == None or event.xdata == None:
            return

        # get the index for the closest wavelength in the plot
        xDelta = np.abs(self.wl - event.xdata)
        idx_closest_pt = np.argmin(xDelta)
        # get the x-y coordinates for the point on the plot with closest wavelength
        x_cursor = self.wl[idx_closest_pt]
        y_cursor = self.average_pixel_spectrum[idx_closest_pt]

        if not (x_cursor == self.x_cursor_fm and y_cursor == self.y_cursor_fm):
            self.x_cursor_fm = x_cursor
            self.y_cursor_fm = y_cursor
            print(x_cursor,y_cursor)
            try:
                self.data_marker.center = x_cursor, y_cursor
                self.MPWidget_feature_match.draw()
            except:
                self.data_marker = Circle((x_cursor, y_cursor), 100)
                self.subplot_feature_match.axes.add_artist(self.data_marker)
                self.data_marker.center = x_cursor, y_cursor
                self.MPWidget_feature_match.draw()

    def cell_was_clicked_fm(self, row, column):
        self.plot_pixel_with_libray_spectra_fm(row)

    def selection_changed_fm(self):
        # get the row that was selected
        print('changed')
        indices = self.feature_match_results_table.selectedIndexes()
        if len(indices) > 0:
            row = indices[0].row()
            self.plot_pixel_with_libray_spectra_fm(row)

    def plot_pixel_with_libray_spectra_fm(self, row):
        # clear the axis
        self.subplot_feature_match.axes.clear()

        # plot the library spectrum
        selected_spectrum_index_fm = self.feature_match_results_table.item(row, len(self.features.keys())+2).text()
        self.selected_library_spectrum_fm = self.lib_spectra[int(selected_spectrum_index_fm),:]
        self.selected_library_name_fm = self.spectra_names[int(selected_spectrum_index_fm)]

        # plot the pixel spectrum
        self.subplot_feature_match.plot(self.wl,self.average_pixel_spectrum,'k', marker='.', label='Pixel Spectrum', lw=1)
        selected_library_spectrum_fm_plot = (self.selected_library_spectrum_fm - np.nanmean(self.selected_library_spectrum_fm))/np.nanstd(self.selected_library_spectrum_fm)
        selected_library_spectrum_fm_plot = selected_library_spectrum_fm_plot*np.nanstd(self.average_pixel_spectrum) + np.nanmean(self.average_pixel_spectrum)
        self.subplot_feature_match.plot(self.wl,selected_library_spectrum_fm_plot,'r', marker='.', label=self.selected_library_name_fm[0:70], lw=1)

        # add the features
        for key in self.features.keys():
            # plot the feature
            x = self.features[key].xdata
            y = self.features[key].ydata
            c = self.features[key].color
            self.subplot_feature_match.plot(x, y,
                                            color=c,
                                            marker='o',
                                            markersize=15,
                                            label='Feature ' + str(key),
                                            linewidth=2,
                                            alpha=0.5)


        self.subplot_feature_match.set_xlabel('Wavelength')
        if self.settings.screen_width > 3000:
            self.subplot_feature_match.axes.legend(fontsize=20)
        else:
            self.subplot_feature_match.axes.legend()

        self.MPWidget_feature_match.getFigure().tight_layout()
        self.MPWidget_feature_match.show()
        self.MPWidget_feature_match.draw()


    def search_and_sort_spectra_names_fm(self):
        nRows = self.feature_match_results_table.rowCount()
        nCols = self.feature_match_results_table.columnCount()
        if nRows > 0:
            query, ok = QInputDialog.getText(self, "Enter words to search for", "Query words:", QLineEdit.Normal, "")
            if not ok:
                return
            self.feature_match_results_table.sortItems(1, order=Qt.AscendingOrder)
            query = query.lower()
            snames = [self.feature_match_results_table.item(idx,0).text().lower() for idx in range(nRows)]
            matchScores = specTools.fuzzy_string_match(query, snames)
            for row_idx in range(nRows):
                self.feature_match_results_table.setItem(row_idx, nCols-1, TableWidgetItem('%.3f' % matchScores[row_idx])  )
            self.feature_match_results_table.sortItems(nCols-1, order=Qt.AscendingOrder)



    def open_in_spectralViewer_fm(self):
        if self.data_check_fm['pixel spectrum present'] == False: # if no pixel spectrum is present, do nothing
            return

        self.fm_wl = self.MPWidget_feature_match.getFigure().gca().lines[0].get_xdata()
        self.fm_pixel_spectrum = self.MPWidget_feature_match.getFigure().gca().lines[0].get_ydata()
        if not hasattr(self, 'spectral_plot'):
            # This is the case if not spectral plot has been made
            self.spectral_plot = spectraViewer.specPlot(parent=self, settings=self.settings)
            self.spectral_plot.setStyleSheet('QMainWindow{padding: 0px}')
            self.spectral_plot.copiedSpectrum.connect(self.copy_spectrum)
            self.spectral_plot.pasteSpectrumRequest.connect(self.paste_spectrum_request)
            #self.pasteSpectrum.connect(self.spectral_plot.paste_spectrum)
            self.spectral_plot.subplot.plot(self.fm_wl,self.fm_pixel_spectrum, label='Pixel Spectrum', color='k', marker='.', linewidth=1)
            try:
                selected_library_spectrum_fm_plot = (self.selected_library_spectrum_fm - np.nanmean(self.selected_library_spectrum_fm))/np.nanstd(self.selected_library_spectrum_fm)
                selected_library_spectrum_fm_plot = selected_library_spectrum_fm_plot*np.nanstd(self.fm_pixel_spectrum) + np.nanmean(self.fm_pixel_spectrum)
                self.spectral_plot.subplot.plot(self.fm_wl,selected_library_spectrum_fm_plot, label=self.selected_library_name_fm[0:70], color='r', linewidth=1)
            except:
                pass
            if self.settings.screen_width > 3000:
                self.spectral_plot.subplot.axes.legend(fontsize=20)
            else:
                self.spectral_plot.subplot.axes.legend()
            self.spectral_plot.MPWidget.draw()
        elif self.spectral_plot.isHidden():
            # This is the case if not spectral plot has been made
            self.spectral_plot = spectraViewer.specPlot(parent=self, settings=self.settings)
            self.spectral_plot.setStyleSheet('QMainWindow{padding: 0px}')
            self.spectral_plot.copiedSpectrum.connect(self.copy_spectrum)
            self.spectral_plot.pasteSpectrumRequest.connect(self.paste_spectrum_request)
            #self.pasteSpectrum.connect(self.spectral_plot.paste_spectrum)
            self.spectral_plot.subplot.plot(self.fm_wl,self.fm_pixel_spectrum, label='Pixel Spectrum', color='k', marker='.', linewidth=1)
            try:
                selected_library_spectrum_fm_plot = (self.selected_library_spectrum_fm - np.nanmean(self.selected_library_spectrum_fm))/np.nanstd(self.selected_library_spectrum_fm)
                selected_library_spectrum_fm_plot = selected_library_spectrum_fm_plot*np.nanstd(self.fm_pixel_spectrum) + np.nanmean(self.fm_pixel_spectrum)
                self.spectral_plot.subplot.plot(self.fm_wl,selected_library_spectrum_fm_plot, label=self.selected_library_name_fm[0:70], color='r', marker='.', linewidth=1)
            except:
                pass
            if self.settings.screen_width > 3000:
                self.spectral_plot.subplot.axes.legend(fontsize=20)
            else:
                self.spectral_plot.subplot.axes.legend()
            self.spectral_plot.MPWidget.draw()
        else:
            try:
                selected_library_spectrum_fm_plot = (self.selected_library_spectrum_fm - np.nanmean(self.selected_library_spectrum_fm))/np.nanstd(self.selected_library_spectrum_fm)
                selected_library_spectrum_fm_plot = selected_library_spectrum_fm_plot*np.nanstd(self.fm_pixel_spectrum) + np.nanmean(self.fm_pixel_spectrum)
                self.spectral_plot.subplot.plot(self.fm_wl,selected_library_spectrum_fm_plot, label=self.selected_library_name_fm, color='g', marker='.', linewidth=1)
            except:
                pass
            if self.settings.screen_width > 3000:
                self.spectral_plot.subplot.axes.legend(fontsize=20)
            else:
                self.spectral_plot.subplot.axes.legend()
            self.spectral_plot.MPWidget.draw()

    def compute_feature_matching(self):

        # complete any feature that is process of building
        self.feature_building_status = False
        self.MPWidget_feature_match.setCursor(QCursor(Qt.ArrowCursor))
        self.cursor = Cursor(self.subplot_feature_match.axes, useblit=True, color='blue', linewidth=1)
        self.MPWidget_feature_match.draw()

        nCols = len(self.features.keys()) + 4
        nRows = 0
        self.feature_match_results_table.setRowCount(nRows)
        self.feature_match_results_table.setColumnCount(nCols)
        # hide the last column
        self.feature_match_results_table.setColumnHidden(nCols-1, True)
        self.feature_match_results_table.setColumnHidden(nCols-2, True)

        # add the feature match columns
        column_headers = ['Name', 'Net Match']
        item0 = QTableWidgetItem('Name')
        self.feature_match_results_table.setHorizontalHeaderItem(0, item0)
        self.feature_match_results_table.setColumnWidth(0, 800)
        item1 = QTableWidgetItem('Net Match')
        self.feature_match_results_table.setHorizontalHeaderItem(1, item1)
        self.feature_match_results_table.setColumnWidth(1, 200)

        col_idx = 2
        for key in self.features.keys():
            c = self.features[key].color
            item = QTableWidgetItem('Feature ' + str(key))
            item.setTextColor(QColor(int(c[0]*255), int(c[1]*255), int(c[2]*255) ))
            self.feature_match_results_table.setHorizontalHeaderItem(col_idx, item)
            self.feature_match_results_table.setColumnWidth(col_idx, 200)
            col_idx = col_idx + 1

        # compute the feature matching
        self.spectra_names, self.feature_match_scores, self.lib_spectra = materialIdentification.feature_matching(self)
        self.add_results_to_table_fm()


    def add_results_to_table_fm(self):

        # set up the number of rows
        nRows = np.shape(self.feature_match_scores)[0]
        self.feature_match_results_table.setRowCount(nRows)

        # put the spectra names in the rows (sorting turned off while fililng table)
        self.feature_match_results_table.setSortingEnabled(False)
        for row_idx in range(nRows):
            self.feature_match_results_table.setItem(row_idx, 0, TableWidgetItem(self.spectra_names[row_idx]))
            self.feature_match_results_table.setItem(row_idx, 1, TableWidgetItem('%.3f' % np.nanmean(self.feature_match_scores[row_idx,:])))
            for feature_idx in range(len(self.features)):
                self.feature_match_results_table.setItem(row_idx, feature_idx+2, TableWidgetItem('%.3f' % self.feature_match_scores[row_idx,feature_idx]))
            self.feature_match_results_table.setItem(row_idx, feature_idx+3, TableWidgetItem(str(row_idx)))

        self.feature_match_results_table.setSortingEnabled(True)

        # sort the table and select the top entry
        self.feature_match_results_table.sortByColumn(1,Qt.AscendingOrder)
        self.feature_match_results_table.selectRow(0)

        # set the size
        self.feature_match_results_table.setColumnWidth(0, 800)

    def export_selection_as_library_fm(self):

        selected_row_indices = self.feature_match_results_table.selectedIndexes()
        if len(selected_row_indices) == 0:
            return

        # iterated through selected cells, and create a list of the rows
        # since there may be more than one cell per row, we break when
        # we encounter a cell in the same row as the frist row in the list
        spectra_indices = []
        first_index = selected_row_indices[0].row()
        for index in selected_row_indices:
            if len(spectra_indices)> 0 and index.row() == first_index:
                break
            spectrum_index = self.feature_match_results_table.item(index.row(), len(self.features.keys())+2).text()
            spectra_indices.append(spectrum_index)

        print('need to save the library...')

        # create the numpy spectra array
        spectra = np.zeros([len(spectra_indices), len(self.wl)])
        spectra_names = []
        row = 0
        for idx in spectra_indices:
            spectra[row, :] = self.lib_spectra[int(idx),:]
            spectra_names.append(self.spectra_names[int(idx)])
            row = row + 1

        # create the header
        header = {}
        header['spectra names'] = spectra_names
        header['wavelength'] = self.wl
        # make the library
        lib = envi.SpectralLibrary(spectra, header, [])
        # select output filename
        fname = QFileDialog.getSaveFileName(self, 'Save Spectral Library', '')
        if fname == '':
            return
        # save the file
        lib.save(fname, 'Library from image spectra')





if __name__ == '__main__':
    app = QApplication(sys.argv)
    #app = QApplication.instance() # when running in Canopy
    win = materialIdentificationViewer()
    win.show()
    app.exec_()