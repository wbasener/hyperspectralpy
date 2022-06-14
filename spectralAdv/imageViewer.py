from __future__ import division
import time
import sys
import os
from math import *
import matplotlib
import matplotlib.pyplot as plt 
#matplotlib.use('Qt4Agg')
from spectral import *
from spectralAdv import *
from . import specTools
from . import spectraViewer
from . import imageViewerDialogs
from . import scatterplot2DViewer
from . import scatterplot3DViewer
from . import easterEggSounds
import numpy as np
from scipy.optimize import nnls
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
#from pyqtgraph.widgets.MatplotlibWidget import *

class fpaViewer(QDialog):
    def __init__(self, fpa_view=None, parent=None, xlabel='', ylabel=''):
        super(fpaViewer, self).__init__(parent)

        # a figure instance to plot on
        self.figure = Figure()

        # this is the Canvas Widget that displays the `figure`
        # it takes the `figure` instance as a parameter to __init__
        self.canvas = FigureCanvas(self.figure)

        # set the layout
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        # create an axis
        ax = self.figure.add_subplot(111)

        # plot data
        vFPAfig = plt.figure(figsize=(8, 4))
        ax = plt.subplot(111)
        im = ax.imshow(fpa_view, interpolation="none", cmap="gray")
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.tight_layout()
        vFPAfig.show()

        # refresh canvas
        self.canvas.draw()


class mouse_event_struc:
    def __init__(self):
        self.timePressed = 0
        self.moved = 0
        self.grabbedX = 0
        self.grabbedY = 0

class imageViewer(QMainWindow):
    # setup signal to send copied spectrum back
    copiedSpectrum = pyqtSignal(dict)
    pasteSpectrumRequest = pyqtSignal(int)
    pasteSpectrum = pyqtSignal(dict)
    changedBands = pyqtSignal(dict)
    viewerClosed = pyqtSignal(int)
    linkViewers = pyqtSignal(int)
    viewerParametersChanged = pyqtSignal(int)
    requestLinkedPixmap = pyqtSignal(int,int)

    def __init__(self, key=None, settings=None, sounds = None, im_dirname=None, im_fname=None, im=None, im_arr=None, parent=None):
        super(imageViewer, self).__init__(parent)
        self.setWindowTitle("[%d] Image Viewer: %s" % (key, os.path.basename(im_fname)))
        self.setGeometry(150, 350, 1000, 1000)
        self.settings = settings
        if self.settings.screen_width > 3000:
            self.setGeometry(150, 350, 1000, 1000)  # (x_pos, y_pos, width, height)
        else:
            self.setGeometry(50, 50, 500, 650)  # (x_pos, y_pos, width, height)
        self.key = key
        self.settings=settings
        self.sounds = sounds
        self.im_dirname = im_dirname   
        self.im_fname = im_fname
        self.im = im
        self.im_arr = im_arr
        self.im_list = None
        self.image_type = None
        self.stretch = {'type': 's2pct', 'min': [0,0,0], 'max': [1,1,1]}
        self.scale = 1
        self.spectral_plot_offset = 200
        self.mouse_event = mouse_event_struc()
        self.pixmapIndex = 0
        self.crosshairState = False
        self.lastVerticalScrollbarPos = 0
        self.lastHorizontalScrollbarPos = 0

        # menu bar actions
        # File menu
        selectImagesAction = QAction("Open new image",self)
        selectImagesAction.triggered.connect(self.load_and_set_image)
        exitAction = QAction("Close",self)
        exitAction.triggered.connect(self.closeEvent)
        # Stretch menu
        twoPctStretchAction = QAction("2% Stretch",self)
        twoPctStretchAction.triggered.connect(self.update_image_2pct)
        zeroOneStretchAction = QAction("0-1 Stretch",self)
        zeroOneStretchAction.triggered.connect(self.update_image_01)
        rangeStretchAction = QAction("Range Stretch",self)
        rangeStretchAction.triggered.connect(self.update_image_range)
        manualHistogramStretchAction = QAction("Interactive Stretch",self)
        manualHistogramStretchAction.triggered.connect(self.interactive_stretch)
        # Tools menu
        viewScatterplot2DAction = QAction("2D Scatterplot (slow)",self)
        viewScatterplot2DAction.triggered.connect(self.scatterplot2D)
        viewScatterplot3DAction = QAction("3D Scatterplot (fast)",self)
        viewScatterplot3DAction.triggered.connect(self.scatterplot3D)
        viewVerticalFPAAction = QAction("View mean in vertical direction",self)
        viewVerticalFPAAction.triggered.connect(self.view_vertical_fpa)
        viewHorizontalFPAAction = QAction("View mean in horizontal direction",self)
        viewHorizontalFPAAction.triggered.connect(self.view_horizontal_fpa)
        linkViewersAction = QAction("Link Viewers",self)
        linkViewersAction.triggered.connect(self.linkViewersFunction)

        # add the menu bar
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu("&File ")
        # For now - not having ability to select new image within the viewer
        #fileMenu.addAction(selectImagesAction)
        #fileMenu.addAction(exitAction)
        stretchMenu = mainMenu.addMenu("&Stretch ")
        stretchMenu.addAction(twoPctStretchAction)
        stretchMenu.addAction(zeroOneStretchAction)
        stretchMenu.addAction(rangeStretchAction)
        stretchMenu.addAction(manualHistogramStretchAction)
        settingsMenu = mainMenu.addMenu("&Tools ")
        settingsMenu.addAction(linkViewersAction)
        settingsMenu.addAction(viewScatterplot2DAction)
        settingsMenu.addAction(viewScatterplot3DAction)
        settingsMenu.addAction(viewVerticalFPAAction)
        settingsMenu.addAction(viewHorizontalFPAAction)
        
        # widgets:
        # zoom buttons
        transparent_background = "QWidget { border: rgba(0, 0, 0, 0); background-color: rgba(0, 0, 0, 0);}"
        fm = QLineEdit().fontMetrics()
        w = 1.2*fm.width('+')
        self.space = QLabel(' ')
        self.btn_plus = QPushButton("+")
        self.btn_plus.setMaximumWidth(w)
        self.btn_minus = QPushButton("-")
        self.btn_minus.setMaximumWidth(w)
        # stretch radio buttons
        self.label_stretch = QLabel('  Stretch:')        
        self.rb_stretch_group=QButtonGroup()
        self.rb_stretch_2pct=QRadioButton("2%")
        self.rb_stretch_group.addButton(self.rb_stretch_2pct)
        self.rb_stretch_01=QRadioButton("0-1")
        self.rb_stretch_group.addButton(self.rb_stretch_01)
        self.rb_stretch_range=QRadioButton("range")
        self.rb_stretch_group.addButton(self.rb_stretch_range)

        # display value (for data image type), row, and col or cursor
        self.label_cursor_val = QLabel('val:')
        self.label_comma1 = QLabel(',')
        self.label_comma2 = QLabel(',')
        self.label_cursor_val_disp_pan = QLineEdit(self)
        fm = self.label_cursor_val_disp_pan.fontMetrics()
        m = self.label_cursor_val_disp_pan.textMargins()
        c = self.label_cursor_val_disp_pan.contentsMargins()
        w_val = fm.width('-0.00') + m.left() + m.right() + c.left() + c.right()
        w = fm.width('1000')+m.left()+m.right()+c.left()+c.right()
        self.label_cursor_val_disp_pan.setReadOnly(True)
        self.label_cursor_val_disp_pan.setMaximumWidth(w_val + 8)
        self.label_cursor_val_disp_pan.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.label_cursor_val_disp_pan.setStyleSheet(transparent_background)

        self.label_cursor_val_disp_blue = QLineEdit(self)
        fm = self.label_cursor_val_disp_blue.fontMetrics()
        m = self.label_cursor_val_disp_blue.textMargins()
        c = self.label_cursor_val_disp_blue.contentsMargins()
        self.label_cursor_val_disp_blue.setReadOnly(True)
        self.label_cursor_val_disp_blue.setMaximumWidth(w_val + 8)
        self.label_cursor_val_disp_blue.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.label_cursor_val_disp_blue.setStyleSheet(transparent_background)

        self.label_cursor_val_disp_green = QLineEdit(self)
        fm = self.label_cursor_val_disp_green.fontMetrics()
        m = self.label_cursor_val_disp_green.textMargins()
        c = self.label_cursor_val_disp_green.contentsMargins()
        self.label_cursor_val_disp_green.setReadOnly(True)
        self.label_cursor_val_disp_green.setMaximumWidth(w_val + 8)
        self.label_cursor_val_disp_green.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.label_cursor_val_disp_green.setStyleSheet(transparent_background)

        self.label_cursor_val_disp_red = QLineEdit(self)
        fm = self.label_cursor_val_disp_red.fontMetrics()
        m = self.label_cursor_val_disp_red.textMargins()
        c = self.label_cursor_val_disp_red.contentsMargins()
        self.label_cursor_val_disp_red.setReadOnly(True)
        self.label_cursor_val_disp_red.setMaximumWidth(w_val + 8)
        self.label_cursor_val_disp_red.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.label_cursor_val_disp_red.setStyleSheet(transparent_background)

        self.label_cursor_row = QLabel('  row:')
        self.label_cursor_row_disp = QLineEdit(self)
        self.label_cursor_row_disp.setReadOnly(True)
        self.label_cursor_row_disp.setMaximumWidth(w + 8)
        self.label_cursor_row_disp.setStyleSheet(transparent_background)
        self.label_cursor_col = QLabel('col:')
        self.label_cursor_col_disp = QLineEdit(self)
        self.label_cursor_col_disp.setReadOnly(True)
        self.label_cursor_col_disp.setMaximumWidth(w + 8)
        self.label_cursor_col_disp.setStyleSheet(transparent_background)

        # scroll area
        self.scrollImage = QScrollArea()
        self.scrollImage.verticalScrollBar().valueChanged.connect(self.scrollBarChanged)
        self.scrollImage.horizontalScrollBar().valueChanged.connect(self.scrollBarChanged)
        # stretch radio buttons
        self.label_disp_type = QLabel('Display:')
        self.toggle_linked_image_btn = QPushButton('Toggle Image')
        self.rb_disp_type_group=QButtonGroup()
        self.rb_disp_type_pan=QRadioButton("Pan")
        self.rb_disp_type_group.addButton(self.rb_disp_type_pan)
        self.rb_disp_type_rgb=QRadioButton("RGB")
        self.rb_disp_type_group.addButton(self.rb_disp_type_rgb)   
        # rgb band selection comboboxes   
        self.label_red = QLabel('Red Band')
        self.label_green = QLabel('Green Band')
        self.label_blue = QLabel('Blue Band')
        self.cb_red = QComboBox()
        self.cb_red.setMinimumWidth(150)
        self.cb_green = QComboBox()
        self.cb_green.setMinimumWidth(150)
        self.cb_blue = QComboBox()  
        self.cb_blue.setMinimumWidth(150)
        # pan band selection comboboxes   
        self.label_pan = QLabel('Panchromatic Band')
        self.cb_pan = QComboBox()
        self.cb_pan.setMinimumWidth(150)
        
        # set the image
        if self.im == None:
            self.load_and_set_image()
        else:
            self.set_image()
        # set the layout
        self.set_layout_display()
                
        self.cb_blue.currentIndexChanged.connect(self.update_image)
        self.cb_green.currentIndexChanged.connect(self.update_image)
        self.cb_red.currentIndexChanged.connect(self.update_image)
        self.cb_pan.currentIndexChanged.connect(self.update_image)
        self.btn_plus.clicked.connect(self.actionZoomInFromButton)
        self.btn_minus.clicked.connect(self.actionZoomOutFromButton)
        self.rb_stretch_2pct.clicked.connect(self.update_image_2pct)
        self.rb_stretch_01.clicked.connect(self.update_image_01)
        self.rb_stretch_range.clicked.connect(self.update_image_range)
        self.rb_disp_type_pan.clicked.connect(self.switched_display_type_pan)
        self.rb_disp_type_rgb.clicked.connect(self.switched_display_type_rgb)
        #self.toggle_linked_image_btn.clicked.connect(self.toggle_linked_image)
        self.toggle_linked_image_btn.mousePressEvent = self.toggle_linked_image
        self.toggle_linked_image_btn.mouseReleaseEvent = self.show_origonal_image
        
        # update the image
        self.update_image()

    def set_layout_display(self):
        # hbox layout for top row
        self.hbox = QHBoxLayout()
        self.hbox.addWidget(self.space)
        self.hbox.addWidget(self.btn_plus)
        self.hbox.addWidget(self.btn_minus)
        self.hbox.addWidget(self.label_stretch)
        self.hbox.addWidget(self.rb_stretch_2pct)
        self.hbox.addWidget(self.rb_stretch_01)
        self.hbox.addWidget(self.rb_stretch_range)
        self.hbox.addStretch(1)
        self.hboxCursorInfo = QHBoxLayout()
        self.hboxCursorInfo.setSpacing(0)
        self.hboxCursorInfo.setContentsMargins(0, 0, 0, 0)
        if self.image_type == 'data':
            self.hboxCursorInfo.addWidget(self.label_cursor_val)
            self.hboxCursorInfo.addWidget(self.label_cursor_val_disp_pan)
            self.hboxCursorInfo.addWidget(self.label_cursor_val_disp_blue)
            self.hboxCursorInfo.addWidget(self.label_comma1)
            self.hboxCursorInfo.addWidget(self.label_cursor_val_disp_green)
            self.hboxCursorInfo.addWidget(self.label_comma2)
            self.hboxCursorInfo.addWidget(self.label_cursor_val_disp_red)
        self.hboxCursorInfo.addWidget(self.label_cursor_row)
        self.hboxCursorInfo.addWidget(self.label_cursor_row_disp)
        self.hboxCursorInfo.addWidget(self.label_cursor_col)
        self.hboxCursorInfo.addWidget(self.label_cursor_col_disp)
        self.hbox.addLayout(self.hboxCursorInfo)
        
        # grid layout for comboboxes and labels for rgb band selection        
        self.widget_rgb=QWidget()
        self.grid_rgb = QGridLayout()
        self.widget_rgb.setLayout(self.grid_rgb)
        self.grid_rgb.setSpacing(5)
        self.grid_rgb.addWidget(self.label_blue, 0, 0)
        self.grid_rgb.addWidget(self.cb_blue, 1, 0)  
        self.grid_rgb.addWidget(self.label_green, 0, 1)
        self.grid_rgb.addWidget(self.cb_green, 1, 1)   
        self.grid_rgb.addWidget(self.label_red, 0, 2)
        self.grid_rgb.addWidget(self.cb_red, 1, 2) 
            
        # grid layout for comboboxes and labels for pan band selection
        self.widget_pan=QWidget()
        self.grid_pan = QGridLayout()
        self.widget_pan.setLayout(self.grid_pan)
        self.grid_pan.setSpacing(5)
        self.grid_pan.addWidget(self.label_pan, 0, 0)
        self.grid_pan.addWidget(self.cb_pan, 1, 0)  
        
        # vbox layout for display type            
        self.hbox_disp_type = QHBoxLayout()
        self.hbox_disp_type.addWidget(self.rb_disp_type_pan)
        self.hbox_disp_type.addWidget(self.rb_disp_type_rgb)
        self.widget_vbox_disp_type=QWidget()
        self.vbox_disp_type = QVBoxLayout()
        self.widget_vbox_disp_type.setLayout(self.vbox_disp_type)
        self.vbox_disp_type.addWidget(self.label_disp_type)
        self.vbox_disp_type.addLayout(self.hbox_disp_type)
        fm = self.label_disp_type.fontMetrics()
        w_vbox_disp_type = 1.5*fm.width('X_Pan_X_RGB')
        self.widget_vbox_disp_type.setMaximumWidth(w_vbox_disp_type)

        # grid layout for toggle_linked_image_btn
        self.widget_toggle_linked_image_btn=QWidget()
        self.vbox_toggle_linked_image_btn = QVBoxLayout()
        self.widget_toggle_linked_image_btn.setLayout(self.vbox_toggle_linked_image_btn)
        self.vbox_toggle_linked_image_btn.addWidget(self.toggle_linked_image_btn)
        fm = self.label_cursor_val_disp_red.fontMetrics()
        w = 1.4*fm.width('Linked Image')
        self.widget_toggle_linked_image_btn.setMaximumWidth(w)
        self.widget_toggle_linked_image_btn.setVisible(False)
        
        # hbox for bottom row
        self.hbox_bottom_row = QHBoxLayout()
        self.hbox_bottom_row.addWidget(self.widget_vbox_disp_type)
        self.hbox_bottom_row.addWidget(self.widget_toggle_linked_image_btn)
        self.hbox_bottom_row.addWidget(self.widget_rgb)
        self.hbox_bottom_row.addWidget(self.widget_pan)
        
        # vbox for image and hbox
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addLayout(self.hbox)
        self.layout.addWidget(self.scrollImage)
        self.layout.addLayout(self.hbox_bottom_row)
        if self.band_select_method == 'rgb':
            self.widget_rgb.setVisible(True)
            self.widget_pan.setVisible(False)
            if self.image_type == 'data':
                self.label_cursor_val_disp_pan.setVisible(False)
                self.label_cursor_val_disp_blue.setVisible(True)
                self.label_comma1.setVisible(True)
                self.label_cursor_val_disp_green.setVisible(True)
                self.label_comma2.setVisible(True)
                self.label_cursor_val_disp_red.setVisible(True)
        else:
            self.widget_rgb.setVisible(False)
            self.widget_pan.setVisible(True)
            if self.image_type == 'data':
                self.label_cursor_val_disp_pan.setVisible(True)
                self.label_cursor_val_disp_blue.setVisible(False)
                self.label_comma1.setVisible(False)
                self.label_cursor_val_disp_green.setVisible(False)
                self.label_comma2.setVisible(False)
                self.label_cursor_val_disp_red.setVisible(False)

        # set the layout for the central widget
        self.widget_central=QWidget()
        self.widget_central.setLayout(self.layout)
        # set as central widget and dock widget
        self.setCentralWidget(self.widget_central)

    def set_image(self):
        # this function is for when the viewer is called with a pre-loaded image
        self.setWindowTitle("[%d] Image Viewer: %s" % (self.key, os.path.basename(self.im_fname)))
        if self.im_arr is None:
            self.im_arr = specTools.envi_load(self.im)
        [nrows,ncols,nbands] = np.shape(self.im_arr)

        # determine some of the metadata
        self.units = self.im.bands.band_unit
        if self.units is None:
            self.units =' '
        self.wl = self.im.bands.centers
        self.image_type = 'spectral'
        self.rb_disp_type_rgb.setChecked(True)
        self.rb_stretch_2pct.setChecked(True)
        self.band_select_method = 'rgb'
        self.stretch['type'] = 's2pct'
        if self.wl is None:
            self.band_select_method = 'pan'
            self.wl =range(1,nbands+1)
            self.image_type = 'data'
            self.rb_disp_type_rgb.setChecked(False)
            self.rb_disp_type_pan.setChecked(True)
            self.rb_stretch_2pct.setChecked(False)
            self.rb_stretch_range.setChecked(True)
            self.stretch['type'] = 'srange'
            try:
                self.bnames = self.im.metadata['band names']
            except:
                self.bnames = [s+' '+self.units for s in map(str, self.wl)]
        else:
            self.bnames = [s+' '+self.units for s in map(str, self.wl)]
        if len(self.wl) == 1:
            self.band_select_method = 'pan'
            self.image_type = 'pan'

        # add the band names to the comboboxes
        self.cb_red.addItems(self.bnames)
        self.cb_green.addItems(self.bnames)
        self.cb_blue.addItems(self.bnames)
        self.cb_pan.addItems(self.bnames)

        # set default red-green-blue
        self.rgbBands = compute_rgbBands(self.wl,self.image_type)
        self.cb_blue.setCurrentIndex(self.rgbBands[2])
        self.cb_green.setCurrentIndex(self.rgbBands[1])
        self.cb_red.setCurrentIndex(self.rgbBands[0])
        self.panBand = 0
        self.cb_pan.setCurrentIndex(self.panBand)
        
    def load_and_set_image(self):
        # Read the data files 
        # if self.imFName is not none and not a file, set it to none
        if self.im_fname is None:
            # if self.imFName is none, prompt user for filename
            # Get files from user (use the directory self.im_dirname if possible)
            if self.im_dirname is None:
                self.im_fname,ok = QFileDialog.getOpenFileName(self, "Choose an image")
            else:
                try:
                    self.im_fname,ok = QFileDialog.getOpenFileName(self, "Choose an image", self.im_dirname)
                except:
                    self.im_fname,ok = QFileDialog.getOpenFileName(self, "Choose an image")
            if not ok:
                return
        try:
            self.im = envi.open(self.im_fname+'.hdr')
        except:
            # sometimes images are saved with ".img" or similar suffix that must be removed from header
            im_fname_nosuffix = self.im_fname[:self.im_fname.rfind(".")]
            self.im = envi.open(im_fname_nosuffix+'.hdr', self.im_fname)

        self.setWindowTitle("[%d] Image Viewer: %s" % (self.key, os.path.basename(self.im_fname)))
        self.im = specTools.apply_bbl(self.im)
        self.im_arr = specTools.envi_load(self.im)
        [nrows,ncols,nbands] = np.shape(self.im_arr)
        
        # determine some of the metadata
        self.units = self.im.bands.band_unit
        if self.units is None:
            self.units =' '  
        self.wl = self.im.bands.centers  
        self.image_type = 'spectral'
        self.rb_disp_type_rgb.setChecked(True)
        self.rb_stretch_2pct.setChecked(True)
        self.band_select_method = 'rgb'
        self.stretch['type'] = 's2pct'
        if self.wl is None:
            self.band_select_method = 'pan'
            self.wl =range(1,nbands+1) 
            self.image_type = 'data'
            self.rb_disp_type_rgb.setChecked(False)
            self.rb_disp_type_pan.setChecked(True)
            self.rb_stretch_2pct.setChecked(False)
            self.rb_stretch_range.setChecked(True)
            self.stretch['type'] = 'srange'
            try:
                self.bnames = self.im.metadata['band names']
            except:
                self.bnames = [s+' '+self.units for s in map(str, self.wl)]
        else:
            self.bnames = [s+' '+self.units for s in map(str, self.wl)]
        if len(self.wl) == 1:
            self.band_select_method = 'pan'
            self.image_type = 'pan'
        
        # add the band names to the comboboxes
        self.cb_red.addItems(self.bnames)
        self.cb_green.addItems(self.bnames)
        self.cb_blue.addItems(self.bnames)
        self.cb_pan.addItems(self.bnames)
        
        # set default red-green-blue
        self.rgbBands = compute_rgbBands(self.wl,self.image_type)
        self.cb_blue.setCurrentIndex(self.rgbBands[2])
        self.cb_green.setCurrentIndex(self.rgbBands[1])
        self.cb_red.setCurrentIndex(self.rgbBands[0])
        self.panBand = 0
        self.cb_pan.setCurrentIndex(self.panBand)
        
    def update_image_2pct(self):
        self.stretch['type'] = 's2pct'
        self.update_image()
        
    def update_image_01(self):
        self.stretch['type'] = 's01'
        self.update_image()
        
    def update_image_range(self):
        self.stretch['type'] = 'srange'
        self.update_image()

    def interactive_stretch(self):

        if self.band_select_method == 'rgb':
            imArray = np.zeros((self.im.nrows, self.im.ncols, 3), 'float32')
            imArray[..., 0] = np.reshape(self.im_arr[:, :, int(self.rgbBands[0])], [self.im.nrows, self.im.ncols])
            imArray[..., 1] = np.reshape(self.im_arr[:, :, int(self.rgbBands[1])], [self.im.nrows, self.im.ncols])
            imArray[..., 2] = np.reshape(self.im_arr[:, :, int(self.rgbBands[2])], [self.im.nrows, self.im.ncols])
        else:
            imArray = np.zeros((self.im.nrows, self.im.ncols), 'float32')
            imArray= np.reshape(self.im_arr[:, :, int(self.panBand)], [self.im.nrows, self.im.ncols])

        self.interactiveStretch = imageViewerDialogs.interactiveStretch(settings=self.settings, imArray=imArray,
                                                  band_select_method=self.band_select_method, stretch=self.stretch,
                                                  parent=self)

        self.interactiveStretch.imageStretchChanged.connect(self.interactiveStretchChanged)

    def interactiveStretchChanged(self, stretch):
        for idx in range(3):
            stretch['min'][idx] = min([self.stretch['min'][idx],self.stretch['max'][idx]])
            stretch['max'][idx] = max([self.stretch['min'][idx],self.stretch['max'][idx]])
        self.stretch = stretch
        self.update_image()

    def update_image(self):
        yOffset = self.scrollImage.verticalScrollBar().value()
        xOffset = self.scrollImage.horizontalScrollBar().value()
        if self.band_select_method == 'rgb':
            # determine the band indices
            self.rgbBands = [self.cb_red.currentIndex(),self.cb_green.currentIndex(),self.cb_blue.currentIndex()]
            self.rgb_arr = self.compute_image_array(3)
        else:
            # determine the band indices
            self.panBand = self.cb_pan.currentIndex()
            self.rgb_arr = self.compute_image_array(1)
        self.rgb_arr_full = self.rgb_arr
        # create the rgb image
        self.imageLabel = QLabel()
        self.imageLabel.setMouseTracking(True)
        nRows = self.rgb_arr.shape[0]
        nCols = self.rgb_arr.shape[1]
        totalBytes = self.rgb_arr.size * self.rgb_arr.itemsize
        bytesPerLine = int(totalBytes/nRows)
        self.qi = QImage(self.rgb_arr.data, nCols, nRows, bytesPerLine, QImage.Format_RGB888)
        self.pm = QPixmap.fromImage(self.qi).scaled(self.scale*self.rgb_arr.shape[1], self.scale*self.rgb_arr.shape[0])
        self.imageLabel.setPixmap(self.pm)
        self.scrollImage.setWidget(self.imageLabel)
        self.scrollImage.verticalScrollBar().setValue(yOffset)
        self.scrollImage.horizontalScrollBar().setValue(xOffset)
        self.imageLabel.mouseReleaseEvent = self.plotSpectrum
        self.imageLabel.mousePressEvent = self.mousePress
        self.imageLabel.mouseMoveEvent = self.mouseMove
        self.imageLabel.wheelEvent = self.wheel

        # emit signal with the band indexes
        band_indexes = {}
        band_indexes['blue'] = self.cb_blue.currentIndex()
        band_indexes['green'] = self.cb_green.currentIndex()
        band_indexes['red'] = self.cb_red.currentIndex()
        self.changedBands.emit(band_indexes)

    def mousePress(self, event):
        # set the time at which the button was pressed
        self.timePressed = time.time()
        # get the event position
        self.grabbedX = event.pos().x()
        self.grabbedY = event.pos().y()
        self.button_pressed = event.buttons()
        if self.button_pressed == Qt.RightButton:
            self.toggle_linked_image(event)

    def add_crosshair(self, x, y):
            # toggle the crosshair status
            if self.crosshairState == False:
                self.crosshairState = True
            else:
                self.crosshairState = False
            # these are the x,y - coords in pixel space in the image
            self.corsshairX_qi = int(floor(x / self.scale))
            self.corsshairY_qi = int(floor(y / self.scale))
            # these are the x,y - coords in pixel space in the QPixmap
            self.corsshairX_pm = (self.corsshairX_qi+0.5)*self.scale
            self.corsshairY_pm = (self.corsshairY_qi+0.5)*self.scale
            top_left_x = self.corsshairX_pm - 0.5*self.scale
            top_left_y = self.corsshairY_pm - 0.5*self.scale

            # paint the crosshair:
            self.pm = QPixmap.fromImage(self.qi).scaled(self.scale*self.rgb_arr.shape[1], self.scale*self.rgb_arr.shape[0])
            painter = QPainter()
            painter.begin(self.pm)
            painter.setPen(QPen(QColor(255, 0, 0)))
            painter.drawLine(self.corsshairX_pm, 0, self.corsshairX_pm, self.im.nrows*self.scale)
            painter.drawLine(0, self.corsshairY_pm, self.im.ncols*self.scale, self.corsshairY_pm)
            painter.drawRect(top_left_x, top_left_y, self.scale, self.scale)
            self.imageLabel.setPixmap(self.pm)
            painter.end()

    def updatePixelmap(self, calling_function_name):
        print(calling_function_name)
        print(np.random.normal())
        if self.crosshairState == True:
            deltaX = self.corsshair_xOffset - self.scrollImage.horizontalScrollBar().value()
            deltaY = self.corsshair_yOffset - self.scrollImage.verticalScrollBar().value()
            self.pm = QPixmap.fromImage(self.qi).scaled(self.scale*self.rgb_arr.shape[1], self.scale*self.rgb_arr.shape[0])
            painter = QPainter()
            painter.begin(self.pm)
            painter.setPen(QPen(QColor(255, 0, 0)))
            painter.drawLine(self.corsshairX_pm-deltaX, 0, self.corsshairX_pm-deltaX, self.im.nrows*self.scale)
            painter.drawLine(0, self.corsshairY_pm-deltaY, self.im.ncols*self.scale, self.corsshairY_pm-deltaY)
            self.imageLabel.setPixmap(self.pm)
            painter.end()
        else:
            self.pm = QPixmap.fromImage(self.qi).scaled(self.scale*self.rgb_arr.shape[1], self.scale*self.rgb_arr.shape[0])
            self.imageLabel.setPixmap(self.pm)

    def mouseMove(self, event):
        if event.buttons() == Qt.NoButton:
            self.cursor_pos_x = event.pos().x()
            self.cursor_pos_y = event.pos().y()
            self.displayCursorCoordinates(event)
        elif event.buttons() == Qt.LeftButton:
            # get the change in event position
            deltaX = self.grabbedX - event.pos().x()
            deltaY = self.grabbedY - event.pos().y()
            # get the off set from the scroll bars
            yOffset = self.scrollImage.verticalScrollBar().value()
            xOffset = self.scrollImage.horizontalScrollBar().value()

            # development testing to incrememnt by multiples of the scale
            #newX = xOffset + deltaX
            #newY = yOffset + deltaY
            #if ((newX == self.lastHorizontalScrollbarPos) and
            #    (newY == self.lastHorizontalScrollbarPos)):
            #    return

            #self.lastVerticalScrollbarPos = 0
            #self.lastHorizontalScrollbarPos = 0

            # set new scroll bar positions
            self.scrollImage.horizontalScrollBar().setValue(xOffset + deltaX)
            self.scrollImage.verticalScrollBar().setValue(yOffset + deltaY)
            self.mouse_event.moved = self.mouse_event.moved + np.sqrt(deltaX**2 + deltaY**2)
            self.pm = QPixmap.fromImage(self.qi).scaled(self.scale*self.rgb_arr.shape[1], self.scale*self.rgb_arr.shape[0])
            self.imageLabel.setPixmap(self.pm)
            # emit signal so that linked imageViewers can update their view parameters
            self.viewerParametersChanged.emit(self.key)
        elif event.buttons() == Qt.RightButton:
            pass

    def wheel(self, event):
        # get the offset from the scroll bars
        xOffset = self.scrollImage.horizontalScrollBar().value()
        yOffset = self.scrollImage.verticalScrollBar().value()
        # get the deltas
        xDelta = event.pos().x() - xOffset
        yDelta = event.pos().y() - yOffset

        # zoom
        if event.angleDelta().y() > 0:
            self.actionZoomIn()
            deltaScale = 1.2
        else:
            self.actionZoomOut()
            deltaScale = 1./1.2

        # set new scroll bar positions
        self.scrollImage.verticalScrollBar().setValue(deltaScale*yOffset - yDelta*(1-deltaScale) )
        self.scrollImage.horizontalScrollBar().setValue(deltaScale*xOffset - xDelta*(1-deltaScale) )
        # emit signal so that linked imageViewers can update their view parameters
        self.viewerParametersChanged.emit(self.key)

    def displayCursorCoordinates(self, event):
        x = int(floor(event.pos().x()/self.scale))
        y = int(floor(event.pos().y()/self.scale))
        rspace = ' '*(4-len(str(y)))
        cspace = ' '*(4-len(str(x)))
        if self.image_type == 'data':
            if self.band_select_method == 'rgb':
                val = '%.2f'%self.im_arr[y,x,self.cb_blue.currentIndex()]
                self.label_cursor_val_disp_blue.setText(val)
                val = '%.2f'%self.im_arr[y,x,self.cb_green.currentIndex()]
                self.label_cursor_val_disp_green.setText(val)
                val = '%.2f'%self.im_arr[y,x,self.cb_red.currentIndex()]
                self.label_cursor_val_disp_red.setText(val)
            else:
                val = '%.2f'%self.im_arr[y,x,self.cb_pan.currentIndex()]
                self.label_cursor_val_disp_pan.setText(val)
            self.label_cursor_row_disp.setText(str(y))
            self.label_cursor_col_disp.setText(str(x))
        else:
            self.label_cursor_row_disp.setText(str(y))
            self.label_cursor_col_disp.setText(str(x))

    def plotSpectrum(self, event):
        try:
            easterEggSounds.play(self.sounds,'other')
        except:
            pass

        if self.button_pressed == Qt.RightButton:
            self.show_origonal_image(event)
            return

        if (self.mouse_event.moved == 0) or ((self.mouse_event.moved < 6) and (time.time() - self.timePressed < 0.5)):
            self.add_crosshair(event.pos().x(), event.pos().y())
            x = int(floor(event.pos().x()/self.scale))
            y = int(floor(event.pos().y()/self.scale))
            if not hasattr(self, 'spectral_plot'):
                # This is the case if not spectral plot has been made
                self.spectral_plot = spectraViewer.specPlot(parent=self, settings=self.settings, x=x, y=y,
                    wl=self.wl,
                    vals=self.im_arr[y,x,:].flatten(),
                    offset=self.spectral_plot_offset,
                    image_type=self.image_type)
                self.spectral_plot.setStyleSheet('QMainWindow{padding: 0px}')
                self.spectral_plot.copiedSpectrum.connect(self.copy_spectrum)
                self.spectral_plot.pasteSpectrumRequest.connect(self.paste_spectrum_request)
                self.pasteSpectrum.connect(self.spectral_plot.paste_spectrum)
                self.spectral_plot.setImageDisplayBand.connect(self.set_display_band)
                self.spectral_plot.MPWidget.draw()
            elif self.spectral_plot.isHidden():
                # This is the case if a spectral plot was made and then closed
                self.spectral_plot = spectraViewer.specPlot(parent=self, settings=self.settings, x=x, y=y,
                    wl=self.wl,
                    vals=self.im_arr[y,x,:].flatten(),
                    offset=self.spectral_plot_offset,
                    image_type=self.image_type)
                self.spectral_plot.setStyleSheet('QMainWindow{padding: 0px;}')
                self.spectral_plot.copiedSpectrum.connect(self.copy_spectrum)
                self.spectral_plot.pasteSpectrumRequest.connect(self.paste_spectrum_request)
                self.pasteSpectrum.connect(self.spectral_plot.paste_spectrum)
                self.spectral_plot.setImageDisplayBand.connect(self.set_display_band)
            else:
                # This is the case if a spectral plot is made and still open
                # generate the plot
                self.spectral_plot.subplot.plot(self.wl,self.im_arr[y,x,:].flatten(), label='row: '+str(y)+', col: '+str(x), linewidth=1)
                self.spectral_plot.addGainOffset('row: '+str(y)+', col: '+str(x))
                if self.settings.screen_width > 3000:
                    self.spectral_plot.subplot.axes.legend(fontsize=20)
                else:
                    self.spectral_plot.subplot.axes.legend()
                self.spectral_plot.MPWidget.draw()
        self.mouse_event.moved = 0

    def copy_spectrum(self, copied_spectrum):
        # emit the signal to send data back
        self.copiedSpectrum.emit(copied_spectrum)

    def paste_spectrum_request(self):
        # emit the signal to send data back
        self.pasteSpectrumRequest.emit(1)

    def paste_spectrum(self, pasted_spectrum):
        self.pasteSpectrum.emit(pasted_spectrum)
    
    def switched_display_type_pan(self):
        self.band_select_method = 'pan'
        self.widget_rgb.setVisible(False)
        self.widget_pan.setVisible(True)
        if self.image_type == 'data':
                self.label_cursor_val_disp_pan.setVisible(True)
                self.label_cursor_val_disp_blue.setVisible(False)
                self.label_comma1.setVisible(False)
                self.label_cursor_val_disp_green.setVisible(False)
                self.label_comma2.setVisible(False)
                self.label_cursor_val_disp_red.setVisible(False)
        self.update_image()
        
    def switched_display_type_rgb(self):
        self.band_select_method = 'rgb'
        self.widget_pan.setVisible(False)
        self.widget_rgb.setVisible(True)
        if self.image_type == 'data':
                self.label_cursor_val_disp_pan.setVisible(False)
                self.label_cursor_val_disp_blue.setVisible(True)
                self.label_comma1.setVisible(True)
                self.label_cursor_val_disp_green.setVisible(True)
                self.label_comma2.setVisible(True)
                self.label_cursor_val_disp_red.setVisible(True)
        self.update_image()

    def set_display_band(self, bandNum):
        self.panBand = bandNum
        self.cb_pan.setCurrentIndex(self.panBand)
        self.update_image()

    def set_display_bands(self, band_indices):
        self.cb_blue.setCurrentIndex(band_indices['blue'])
        self.cb_green.setCurrentIndex(band_indices['gereen'])
        self.cb_red.setCurrentIndex(band_indices['red'])
        self.update_image()
        
    def actionZoomIn(self):
        self.scale *= 1.2
        # create the rgb image
        self.imageLabel = QLabel()
        self.imageLabel.setMouseTracking(True)
        self.pm = QPixmap.fromImage(self.qi).scaled(self.scale*self.rgb_arr.shape[1], self.scale*self.rgb_arr.shape[0])
        self.imageLabel.setPixmap(self.pm)
        self.imageLabel.mouseReleaseEvent  = self.plotSpectrum
        self.imageLabel.mousePressEvent = self.mousePress
        self.imageLabel.mouseMoveEvent = self.mouseMove
        self.imageLabel.wheelEvent = self.wheel
        self.scrollImage.setWidget(self.imageLabel)
        self.imageLabel.eventFilter = self.eventFilter

    def actionZoomOut(self):
        if self.scrollImage.verticalScrollBar().isVisible():
            self.scale *= 1./1.2
            # create the rgb image
            self.imageLabel = QLabel()
            self.imageLabel.setMouseTracking(True)
            self.pm = QPixmap.fromImage(self.qi).scaled(self.scale*self.rgb_arr.shape[1], self.scale*self.rgb_arr.shape[0])
            self.imageLabel.setPixmap(self.pm)
            self.imageLabel.mouseReleaseEvent  = self.plotSpectrum
            self.imageLabel.mousePressEvent = self.mousePress
            self.imageLabel.mouseMoveEvent = self.mouseMove
            self.imageLabel.wheelEvent = self.wheel
            self.scrollImage.setWidget(self.imageLabel)
        self.imageLabel.eventFilter = self.eventFilter

    def actionZoomInFromButton(self):
        self.scale *= 1.2
        # create the rgb image
        self.imageLabel = QLabel()
        self.imageLabel.setMouseTracking(True)
        self.pm = QPixmap.fromImage(self.qi).scaled(self.scale*self.rgb_arr.shape[1], self.scale*self.rgb_arr.shape[0])
        self.imageLabel.setPixmap(self.pm)
        self.imageLabel.mouseReleaseEvent  = self.plotSpectrum
        self.imageLabel.mousePressEvent = self.mousePress
        self.imageLabel.mouseMoveEvent = self.mouseMove
        self.imageLabel.wheelEvent = self.wheel
        self.scrollImage.setWidget(self.imageLabel)
        self.imageLabel.eventFilter = self.eventFilter
        # emit signal so that linked imageViewers can update their view parameters
        self.viewerParametersChanged.emit(self.key)

    def actionZoomOutFromButton(self):
        if self.scrollImage.verticalScrollBar().isVisible():
            self.scale *= 1./1.2
            # create the rgb image
            self.imageLabel = QLabel()
            self.imageLabel.setMouseTracking(True)
            self.pm = QPixmap.fromImage(self.qi).scaled(self.scale*self.rgb_arr.shape[1], self.scale*self.rgb_arr.shape[0])
            self.imageLabel.setPixmap(self.pm)
            self.imageLabel.mouseReleaseEvent  = self.plotSpectrum
            self.imageLabel.mousePressEvent = self.mousePress
            self.imageLabel.mouseMoveEvent = self.mouseMove
            self.imageLabel.wheelEvent = self.wheel
            self.scrollImage.setWidget(self.imageLabel)
            # emit signal so that linked imageViewers can update their view parameters
            self.viewerParametersChanged.emit(self.key)
        self.imageLabel.eventFilter = self.eventFilter

    def resizeEvent(self, event):
        # catching the resizeEvent here to signal to resize all linked viewers when resize happens
        self.viewerParametersChanged.emit(self.key)
        try:
            info = super(self.Window, self).resizeEvent(event)
            return info
        except:
            return

    def scrollBarChanged(self):
        # Remove crossharis if present
        if self.crosshairState == True:
            self.pm = QPixmap.fromImage(self.qi).scaled(self.scale*self.rgb_arr.shape[1], self.scale*self.rgb_arr.shape[0])
            self.imageLabel.setPixmap(self.pm)
            self.crosshairState = False
        self.viewerParametersChanged.emit(self.key)

    def setViewParameters(self, view_parameters):
        # set the GUI size
        self.resize(view_parameters['width'],view_parameters['height'])
        if self.scale != view_parameters['scale']:
            # recreate the QImage if the scale is changed
            self.scale = view_parameters['scale']
            # create the rgb image
            self.imageLabel = QLabel()
            self.imageLabel.setMouseTracking(True)
            nRows = self.rgb_arr.shape[0]
            nCols = self.rgb_arr.shape[1]
            totalBytes = self.rgb_arr.size * self.rgb_arr.itemsize
            bytesPerLine = int(totalBytes/nRows)
            self.qi = QImage(self.rgb_arr.data, nCols, nRows, bytesPerLine, QImage.Format_RGB888)
            self.pm = QPixmap.fromImage(self.qi).scaled(self.scale*self.rgb_arr.shape[1], self.scale*self.rgb_arr.shape[0])
            self.imageLabel.setPixmap(self.pm)
            self.scrollImage.setWidget(self.imageLabel)
            self.imageLabel.mouseReleaseEvent = self.plotSpectrum
            self.imageLabel.mousePressEvent = self.mousePress
            self.imageLabel.mouseMoveEvent = self.mouseMove
            self.imageLabel.wheelEvent = self.wheel
        self.scrollImage.verticalScrollBar().setValue(view_parameters['verticalScrollBarValue'])
        self.scrollImage.horizontalScrollBar().setValue(view_parameters['horizontalScrollBarValue'])

    def getViewParameters(self):
        view_parameters = {}
        view_parameters['verticalScrollBarValue'] = self.scrollImage.verticalScrollBar().value()
        view_parameters['horizontalScrollBarValue'] = self.scrollImage.horizontalScrollBar().value()
        view_parameters['scale'] = self.scale
        view_parameters['width'] = self.geometry().width()
        view_parameters['height'] = self.geometry().height()
        return view_parameters

    def toggle_linked_image(self, event):
        # this is called on mousedown on button
        self.pixmapIndex = self.pixmapIndex + 1
        self.requestLinkedPixmap.emit(self.pixmapIndex, self.key)

    def show_liked_image(self, pixmap, pixmapIndex):
        # this is called by menu
        # this will put the linked image in pixmap into the viewer
        self.pixmapIndex = pixmapIndex
        self.imageLabel.setPixmap(pixmap)
        self.scrollImage.setWidget(self.imageLabel)
        self.imageLabel.mouseReleaseEvent = self.plotSpectrum
        self.imageLabel.mousePressEvent = self.mousePress
        self.imageLabel.mouseMoveEvent = self.mouseMove
        self.imageLabel.wheelEvent = self.wheel

    def show_origonal_image(self, event):
        # this is called on mouseup on button
        self.imageLabel.setPixmap(self.pm)
        self.scrollImage.setWidget(self.imageLabel)
        self.imageLabel.mouseReleaseEvent = self.plotSpectrum
        self.imageLabel.mousePressEvent = self.mousePress
        self.imageLabel.mouseMoveEvent = self.mouseMove
        self.imageLabel.wheelEvent = self.wheel

    def scatterplot2D(self):
        if self.im.nbands < 2:
            return

        # create list version of image if it does not exist
        if self.im_list is None:
            self.im_list =  np.reshape(self.im_arr,[self.im.nrows*self.im.ncols,self.im.nbands])
        # create list of displayed pixel colors
        self.pt_colors =  np.reshape(self.rgb_arr,[self.im.nrows*self.im.ncols,3])

        # This is the case if not spectral plot has been made
        self.scatterplot2DViewer = scatterplot2DViewer.scatterplot2DViewer(parent=self,
                                                    settings=self.settings,
                                                    bnames = self.bnames,
                                                    x_index = self.cb_blue.currentIndex(),
                                                    y_index = self.cb_green.currentIndex(),
                                                    pt_colors = self.pt_colors,
                                                    im_list = self.im_list)
        self.scatterplot2DViewer.changedBands.connect(self.set_display_bands)
        self.changedBands.connect(self.scatterplot2DViewer.set_display_bands)
        self.scatterplot2DViewer.show()
        #self.scatterplot2DViewer.scatterplot.show()

    def scatterplot3D(self):
        if self.im.nbands < 3:
            return

        # create list version of image if it does not exist
        if self.im_list is None:
            self.im_list =  np.reshape(self.im_arr,[self.im.nrows*self.im.ncols,self.im.nbands])
        # create list of displayed pixel colors
        self.pt_colors =  np.reshape(self.rgb_arr,[self.im.nrows*self.im.ncols,3])

        # This is the case if not spectral plot has been made
        self.scatterplot3DViewer = scatterplot3DViewer.scatterplot3DViewer(parent=self,
                                                    settings = self.settings,
                                                    bnames = self.bnames,
                                                    x_index = self.cb_blue.currentIndex(),
                                                    y_index = self.cb_green.currentIndex(),
                                                    z_index = self.cb_red.currentIndex(),
                                                    pt_colors = self.pt_colors,
                                                    im_list = self.im_list)
        self.scatterplot3DViewer.changedBands.connect(self.set_display_bands)
        self.changedBands.connect(self.scatterplot3DViewer.set_display_bands)
        self.scatterplot3DViewer.show()
        self.scatterplot3DViewer.scatterplot.show()

    def view_vertical_fpa(self):
        fpa_view = np.flip(np.rot90(np.mean(self.im_arr, axis=0)), 0)
        pltWindow_vertical_mean = plotDisplay.pltDisplay(title="Image Mean in Vertical Direction", width=1200, height=600,
                                            settings=None)
        ax = pltWindow_vertical_mean.figure.add_subplot(111)
        ax.imshow(fpa_view)
        pltWindow_vertical_mean.canvas.draw()
        pltWindow_vertical_mean.show()

    def view_horizontal_fpa(self):
        fpa_view = np.mean(self.im_arr, axis=1)
        pltWindow_horizontal_mean = plotDisplay.pltDisplay(title="Image Mean in Horizontal Direction", width=600, height=1800,
                                            settings=None)
        ax = pltWindow_horizontal_mean.figure.add_subplot(111)
        ax.imshow(fpa_view)
        pltWindow_horizontal_mean.canvas.draw()
        pltWindow_horizontal_mean.show()

    def not_supported(self):
        QMessageBox.information(self, "Not Supported","That functionality is not yet supported.")

    def closeEvent(self, event):
        self.viewerClosed.emit(self.key)
        event.accept()

    def linkViewersFunction(self):
        self.linkViewers.emit(self.key)

    def getNumRows(self):
        return self.im.nrows

    def getNumCols(self):
        return self.im.ncols

    def getFname(self):
        return os.path.basename(self.im_fname)

    def getPixmap(self):
        return self.pm

    def compute_image_array(self, nb):
        [nrows, ncols, nbands] = np.shape(self.im)
        max_val = 255.
        min_val = 0.
        if nb == 3:
            rgbArray = np.zeros((nrows, ncols, 3), 'float32')
            rgbArray[..., 0] = np.reshape(self.im_arr[:, :, int(self.rgbBands[0])], [nrows, ncols])
            rgbArray[..., 1] = np.reshape(self.im_arr[:, :, int(self.rgbBands[1])], [nrows, ncols])
            rgbArray[..., 2] = np.reshape(self.im_arr[:, :, int(self.rgbBands[2])], [nrows, ncols])
        else:
            rgbArray = np.zeros((nrows, ncols, 3), 'float32')
            rgbArray[..., 0] = np.reshape(self.im_arr[:, :, int(self.panBand)], [nrows, ncols])
            rgbArray[..., 1] = np.reshape(self.im_arr[:, :, int(self.panBand)], [nrows, ncols])
            rgbArray[..., 2] = np.reshape(self.im_arr[:, :, int(self.panBand)], [nrows, ncols])
        for band_idx in range(3):
            # stretch band
            if self.stretch['type'] == 's2pct':
                bottom = np.percentile(rgbArray[:, :, band_idx], 2)
                top = np.percentile(rgbArray[:, :, band_idx], 99)
            elif self.stretch['type'] == 'srange':
                bottom = np.min(rgbArray[:, :, band_idx])
                top = np.max(rgbArray[:, :, band_idx])
            elif self.stretch['type'] == 'slinear':
                bottom = self.stretch['min'][band_idx]
                top = self.stretch['max'][band_idx]
            else:
                bottom = 0.
                top = 1.

            self.stretch['min'][band_idx] = bottom
            self.stretch['max'][band_idx] = top
            rgbArray[rgbArray[:, :, band_idx] < bottom, band_idx] = bottom
            rgbArray[rgbArray[:, :, band_idx] > top, band_idx] = top
            rgbArray[..., band_idx] = (rgbArray[:, :, band_idx] - bottom) * max_val / (top - bottom)
        rgbArray[rgbArray < min_val] = min_val
        rgbArray[rgbArray >= max_val] = max_val
        return rgbArray.astype('uint8')

def compute_rgbBands(wl,image_type):
    wl = np.asarray(wl)
    if image_type == 'spectral':
        if np.mean(wl) < 10:
            # assuming units are microns
            if min(wl)<0.7:
                # image has visible wavelengths
                r = np.argmin(abs(wl-0.65))
                g = np.argmin(abs(wl-0.55))
                b = np.argmin(abs(wl-0.45))
            else:
                # image is nvir or swir only
                r = np.argmin(abs(wl-2.125))
                g = np.argmin(abs(wl-1.6))
                b = np.argmin(abs(wl-1.5))
        if np.mean(wl) > 10:
            # assuming units are nanometers
            if min(wl)<700:
                # image has visible wavelengths
                r = np.argmin(abs(wl-650))
                g = np.argmin(abs(wl-550))
                b = np.argmin(abs(wl-450))
            else:
                # image is nvir or swir only
                r = np.argmin(abs(wl-2125))
                g = np.argmin(abs(wl-1600))
                b = np.argmin(abs(wl-1500))
    else:
        r = 2
        g = 1
        b = 0
    rgbBands = np.asarray([int(r),int(g),int(b)])
    return rgbBands




if __name__ == "__main__":
    app = QApplication(sys.argv)
    #app = QApplication.instance() # when running in Canopy
    form = imageViewer(im_dirname='C:\\Users\\wfbsm\\Desktop\\specTools Tools\\images')
    form.show()
    app.exec_()