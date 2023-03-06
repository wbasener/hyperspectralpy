from __future__ import division
import time
import sys
import os
import csv
from math import *
import matplotlib
import matplotlib.pyplot as plt
#matplotlib.use('Qt4Agg')
from spectral import *
from spectralAdv import *
import rasterio as rio
import rasterio
from rasterio.plot import show
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
from matplotlib.path import Path
import matplotlib.colors as cm
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


class ROI_struc:
    def __init__(self):
        self.name = ""
        self.polygons = []
        self.image = 0
        self.pixels = 0
        self.bands = 0

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
        self.settings = settings
        self.setWindowTitle("[%d] Image Viewer: %s" % (key, os.path.basename(im_fname)))
        self.setGeometry(150, 150, 1200, 1000)
        if self.settings.screen_width > 3000:
            self.setGeometry(150, 150, 1200, 1000)  # (x_pos, y_pos, width, height)
        else:
            self.setGeometry(50, 50, 1000, 700)  # (x_pos, y_pos, width, height)
        self.key = key
        self.sounds = sounds
        self.im_dirname = im_dirname   
        self.im_fname = im_fname
        self.im = im
        self.im_arr = im_arr
        self.im_list = None
        self.image_type = None
        self.stretch = {'type': 's2pct', 'type_prev': '',
                        'min': [0,0,0], 'min_prev': [-1,-1,-1],
                        'max': [1,1,1],  'max_prev': [-1,-1,-1]}
        self.scale = 1
        self.spectral_plot_offset = 200
        self.mouse_event = mouse_event_struc()
        self.pixmapIndex = 0
        self.crosshairState = False
        self.ignoreBlackRegions = True
        self.lastVerticalScrollbarPos = 0
        self.lastHorizontalScrollbarPos = 0
        # variables for ROIs
        self.ROI_im_dict = {}
        self.ROI_polygons = []
        self.ROI_polygons_Im = []
        self.ROI_colors = []
        self.ROI_Id_nums = []
        self.colors = [cm.to_hex(plt.cm.tab20(i)) for i in range(20)]

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
        w = 2*fm.width('+')
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
        self.rb_stretch_2pct_dark=QRadioButton("2%-100%")
        self.rb_stretch_group.addButton(self.rb_stretch_2pct_dark)
        self.rb_stretch_01=QRadioButton("0-1")
        self.rb_stretch_group.addButton(self.rb_stretch_01)
        self.rb_stretch_range=QRadioButton("range")
        self.rb_stretch_group.addButton(self.rb_stretch_range)

        self.btn_ROIs = QPushButton("Collect ROIs")
        self.btn_ROIs.setCheckable(True)
        self.btn_new_ROI = QPushButton("New ROI")
        self.btn_save_ROIs = QPushButton("Save ROIs")

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

        # list widget for selecting ROIs
        self.ROI_table = QTableWidget()
        self.ROI_table.setSelectionMode(QAbstractItemView.SingleSelection)
        nCols = 4
        nRows = 1
        self.ROI_table.setRowCount(nRows)
        self.ROI_table.setColumnCount(nCols)
        self.ROI_table.setHorizontalHeaderLabels(['Name', 'Color', '# Pixels','ROI Id num'])
        self.ROI_Id_num_count = 0
        self.ROI_table.hideColumn(3)
        # Set row contents
        # default start name
        self.ROI_table.setItem(0, 0, QTableWidgetItem("ROI "+str(0)))
        # start with red color
        item = QTableWidgetItem('  ')
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        item.setBackground(QColor(250, 50, 50))
        self.current_color = QColor(250, 50, 50)
        self.ROI_table.setItem(0, 1, item)
        # start with 0 pixels
        item = QTableWidgetItem("0")
        item.setFlags(item.flags() ^ Qt.ItemIsEditable ^ Qt.ItemIsSelectable)
        self.ROI_table.setItem(0, 2, item)
        # start with unique Id num
        self.ROI_table.setItem(0, 3, QTableWidgetItem("ROI_num_"+str(self.ROI_Id_num_count)))
        self.ROI_Id_num_count = self.ROI_Id_num_count + 1
        self.ROI_table.itemSelectionChanged.connect(self.ROI_table_item_selected)
        self.ROI_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.ROI_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.ROI_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.ROI_table.setStyleSheet("background-color: LightGrey;")
        self.ROI_table.setMaximumWidth(600)
        # create variable to hold polygons
        self.polygon = QPolygonF()
        self.polygon_points = []
        self.polygonIm = QPolygon()
        self.polygonIm_points = []
        
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
        self.rb_stretch_2pct_dark.clicked.connect(self.update_image_2pct_dark)
        self.rb_stretch_01.clicked.connect(self.update_image_01)
        self.rb_stretch_range.clicked.connect(self.update_image_range)
        self.btn_ROIs.clicked.connect(self.actionCollectROIs)
        self.btn_new_ROI.clicked.connect(self.actionNewROI)
        self.btn_save_ROIs.clicked.connect(self.saveROIs)
        self.rb_disp_type_pan.clicked.connect(self.switched_display_type_pan)
        self.rb_disp_type_rgb.clicked.connect(self.switched_display_type_rgb)
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
        self.hbox.addWidget(self.rb_stretch_2pct_dark)
        self.hbox.addWidget(self.rb_stretch_01)
        self.hbox.addWidget(self.rb_stretch_range)
        self.hbox.addWidget(self.btn_ROIs)
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
        w_vbox_disp_type = int(1.5*fm.width('X_Pan_X_RGB'))
        self.widget_vbox_disp_type.setMaximumWidth(w_vbox_disp_type)

        # grid layout for toggle_linked_image_btn
        self.widget_toggle_linked_image_btn=QWidget()
        self.vbox_toggle_linked_image_btn = QVBoxLayout()
        self.widget_toggle_linked_image_btn.setLayout(self.vbox_toggle_linked_image_btn)
        self.vbox_toggle_linked_image_btn.addWidget(self.toggle_linked_image_btn)
        fm = self.label_cursor_val_disp_red.fontMetrics()
        w = int(1.4*fm.width('Linked Image'))
        self.widget_toggle_linked_image_btn.setMaximumWidth(w)
        self.widget_toggle_linked_image_btn.setVisible(False)
        
        # hbox for bottom row
        self.hbox_bottom_row = QHBoxLayout()
        self.hbox_bottom_row.addWidget(self.widget_vbox_disp_type)
        self.hbox_bottom_row.addWidget(self.widget_toggle_linked_image_btn)
        self.hbox_bottom_row.addWidget(self.widget_rgb)
        self.hbox_bottom_row.addWidget(self.widget_pan)

        # Center Area for image and ROI Table
        self.hbox_center = QHBoxLayout()
        self.hbox_center.addWidget(self.scrollImage)
        self.vbox_ROIs = QVBoxLayout()
        # create the frame object.
        self.box_ROIs_frame = QFrame()
        self.hbox_ROI_buttons = QHBoxLayout()
        self.hbox_ROI_buttons.addWidget(self.btn_new_ROI)
        self.hbox_ROI_buttons.addWidget(self.btn_save_ROIs)
        self.vbox_ROIs.addLayout(self.hbox_ROI_buttons)
        self.vbox_ROIs.addWidget(self.ROI_table)
        self.box_ROIs_frame.setLayout(self.vbox_ROIs)
        self.hbox_center.addWidget(self.box_ROIs_frame)
        self.box_ROIs_frame.setMaximumWidth(600)
        self.box_ROIs_frame.hide()
        
        # vbox for image and hbox
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addLayout(self.hbox)
        self.layout.addLayout(self.hbox_center)
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
        # if image is a tif"
        if (os.path.splitext(self.im_fname)[-1]=='.tif') or (os.path.splitext(self.im_fname)[-1]=='.tiff'):
            self.im = rasterio.open(self.im_fname)
            self.im_dirname = os.path.dirname(self.im_fname)
            self.setWindowTitle("[%d] Image Viewer: %s" % (self.key, os.path.basename(self.im_fname)))

            im_arr_temp = self.im.read()
            [nbands,nrows,ncols] = np.shape(im_arr_temp)
            self.im_arr = np.zeros((nrows,ncols,nbands))
            if (nbands == 3): # bands are in reverse wavelength order - RGB for viewing
                self.im_arr[:,:,0] = im_arr_temp[2,:,:]
                self.im_arr[:,:,1] = im_arr_temp[1,:,:]
                self.im_arr[:,:,2] = im_arr_temp[0,:,:]
            else:
                for i in range(nbands):
                    self.im_arr[:,:,i] = im_arr_temp[i,:,:]
            self.im.nrows = nrows
            self.im.ncols = ncols
            self.im.nbands = nbands
            self.wl = self.im.descriptions
            self.units = 'nm'
            if (self.im.count == 3):
                self.wl = [450,550,650]
            if (self.im.count == 4):
                self.wl = [450,550,650,750]
            if (self.im.count == 8):
                self.wl = [440,490,530,565,610,670,705,865]


        # otherwise - this should be a ENVI file:
        else:
            try:
                self.im = envi.open(self.im_fname+'.hdr')
            except:
                # sometimes images are saved with ".img" or similar suffix that must be removed from header
                im_fname_nosuffix = self.im_fname[:self.im_fname.rfind(".")]
                self.im = envi.open(im_fname_nosuffix+'.hdr', self.im_fname)

            self.im_dirname = os.path.dirname(self.im_fname)
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

        # set basic image pixe coordinates values for ROIs (coordinates for all points in points_vstack)
        x, y = np.meshgrid(np.arange(self.im.ncols), np.arange(self.im.nrows))  # make a canvas with coordinates
        x, y = x.flatten(), y.flatten()
        self.points_vstack = np.vstack((x, y)).T
        self.ROI_im_dict["ROI_num_"+str(0)] = np.full((self.im.nrows * self.im.ncols,), False)
        
    def update_image_2pct(self):
        self.stretch['type'] = 's2pct'
        self.update_image()

    def update_image_2pct_dark(self):
        self.stretch['type'] = 's2pctDrk'
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
        self.draw_polygons()

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
        self.pm = QPixmap.fromImage(self.qi).scaled(int(self.scale*self.rgb_arr.shape[1]), int(self.scale*self.rgb_arr.shape[0]))
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
        self.draw_polygons()

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
            self.corsshairX_pm = int((self.corsshairX_qi+0.5)*self.scale)
            self.corsshairY_pm = int((self.corsshairY_qi+0.5)*self.scale)
            top_left_x = int(self.corsshairX_pm - 0.5*self.scale)
            top_left_y = int(self.corsshairY_pm - 0.5*self.scale)

            # paint the crosshair:
            self.pm = QPixmap.fromImage(self.qi).scaled(int(self.scale*self.rgb_arr.shape[1]), int(self.scale*self.rgb_arr.shape[0]))
            painter = QPainter()
            painter.begin(self.pm)
            painter.setPen(QPen(QColor(255, 0, 0)))
            painter.drawLine(self.corsshairX_pm, 0, self.corsshairX_pm, int(self.im.nrows*self.scale))
            painter.drawLine(0, self.corsshairY_pm, int(self.im.ncols*self.scale), self.corsshairY_pm)
            painter.drawRect(top_left_x, top_left_y, int(self.scale), int(self.scale))
            self.imageLabel.setPixmap(self.pm)
            painter.end()

    def updatePixelmap(self, calling_function_name):
        print(calling_function_name)
        print(np.random.normal())
        if self.crosshairState == True:
            deltaX = self.corsshair_xOffset - self.scrollImage.horizontalScrollBar().value()
            deltaY = self.corsshair_yOffset - self.scrollImage.verticalScrollBar().value()
            self.pm = QPixmap.fromImage(self.qi).scaled(int(self.scale*self.rgb_arr.shape[1]), int(self.scale*self.rgb_arr.shape[0]))
            painter = QPainter()
            painter.begin(self.pm)
            painter.setPen(QPen(QColor(255, 0, 0)))
            painter.drawLine(self.corsshairX_pm-deltaX, 0, self.corsshairX_pm-deltaX, self.im.nrows*self.scale)
            painter.drawLine(0, self.corsshairY_pm-deltaY, self.im.ncols*self.scale, self.corsshairY_pm-deltaY)
            self.imageLabel.setPixmap(self.pm)
            painter.end()
        else:
            self.pm = QPixmap.fromImage(self.qi).scaled(int(self.scale*self.rgb_arr.shape[1]), int(self.scale*self.rgb_arr.shape[0]))
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

            # set new scroll bar positions
            self.scrollImage.horizontalScrollBar().setValue(xOffset + deltaX)
            self.scrollImage.verticalScrollBar().setValue(yOffset + deltaY)
            self.mouse_event.moved = self.mouse_event.moved + np.sqrt(deltaX**2 + deltaY**2)
            self.pm = QPixmap.fromImage(self.qi).scaled(int(self.scale*self.rgb_arr.shape[1]), int(self.scale*self.rgb_arr.shape[0]))
            self.imageLabel.setPixmap(self.pm)
            # emit signal so that linked imageViewers can update their view parameters
            self.viewerParametersChanged.emit(self.key)
            self.draw_polygons()
        elif event.buttons() == Qt.RightButton:
            pass

    def wheel(self, event):
        try:
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
            self.draw_polygons()
        except:
            # Sometimes too many mouse wheels seem to overwhelm the buffer, so this is an attept to catch that
            pass

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
            if self.btn_ROIs.isChecked():
                self.close_polygon()
            else:
                self.show_origonal_image(event)
            return

        if (self.mouse_event.moved == 0) or ((self.mouse_event.moved < 6) and (time.time() - self.timePressed < 0.5)):

            if self.btn_ROIs.isChecked():
                # Build an ROI polygon:

                # check if a row is selected:
                if (len(self.ROI_table.selectedItems()) > 0):
                    item = self.ROI_table.selectedItems()[0]
                    row = item.row()

                    # ADDING A POLYGON
                    # Get the location
                    x = event.pos().x() # x in cuuren pixel_map coords
                    y = event.pos().y() # y in cuuren pixel_map coords
                    x_im = int(floor(x / self.scale)) # x in image coords
                    y_im = int(floor(y / self.scale)) # y in image coords
                    # add the new point to the polygon points
                    self.polygon_points.append([x,y])
                    self.polygon.append(QPointF(x,y))
                    self.polygonIm_points.append([int(x_im),int(y_im)])
                    self.polygonIm.append(QPoint(int(x_im),int(y_im)))
                    self.make_ROI_table_unselectable()
                    self.draw_polygon_line()
                else:
                    # User clicked on image with ROI selection checked
                    # but without a row in the ROI table selected.
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Information)
                    # setting message for Message Box
                    msg.setText("A row in the ROI table must be selected to draw an ROI.")
                    # setting Message box window title
                    msg.setWindowTitle("Select row in ROI table.")
                    # declaring buttons on Message Box
                    msg.setStandardButtons(QMessageBox.Ok )
                    retval = msg.exec_()
            else:
                self.add_crosshair(event.pos().x(), event.pos().y())
                x = int(floor(event.pos().x()/self.scale))
                y = int(floor(event.pos().y()/self.scale))
                if not hasattr(self, 'spectral_plot'):
                    # This is the case if not spectral plot has been made
                    self.spectral_plot = spectraViewer.specPlot(parent=self, settings=self.settings, x=x, y=y,
                        wl=self.wl,
                        marker='o',
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
                        marker='o',
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
                    self.spectral_plot.subplot.plot(self.wl,self.im_arr[y,x,:].flatten(), label='row: '+str(y)+', col: '+str(x), marker='o', linewidth=1)
                    self.spectral_plot.addGainOffset('row: '+str(y)+', col: '+str(x))
                    if self.settings.screen_width > 3000:
                        self.spectral_plot.subplot.axes.legend(fontsize=20)
                    else:
                        self.spectral_plot.subplot.axes.legend()
                    self.spectral_plot.MPWidget.draw()
        self.mouse_event.moved = 0

    def close_polygon(self):
        # paint the polygon:
        self.ROI_polygons.append(self.polygon)
        self.ROI_polygons_Im.append(self.polygonIm)
        self.ROI_colors.append(self.current_color)
        self.ROI_Id_nums.append(self.current_ROI_Id_num)

        print("count...")
        # determine pixels inside this polygon
        p = Path(self.polygonIm_points)  # make a polygon
        grid = p.contains_points(self.points_vstack)  # determine the points (coordinates listed in vstack) inside this polygon
        # This is how you make a 2d mask from the grid: mask = grid.reshape(self.im.ncols, self.im.nrows)
        # add these pixel locations to the set of all locations for this ROI
        self.ROI_im_dict[self.current_ROI_Id_num.text()] = self.ROI_im_dict[self.current_ROI_Id_num.text()]+grid
        # set the number of points for this ROI
        item = self.ROI_table.selectedItems()[0]
        row = item.row()
        self.ROI_table.setItem(row, 2, QTableWidgetItem(str(np.sum(self.ROI_im_dict[self.current_ROI_Id_num.text()]))))

        # Reset current polygon
        self.polygon = QPolygonF()
        self.polygon_points = []
        self.polygonIm = QPolygon()
        self.polygonIm_points = []
        # Make the ROI table active (selectable) again
        self.make_ROI_table_selectable()
        self.draw_polygons()

    def draw_polygons(self):
        if self.btn_ROIs.isChecked():
            self.pm = QPixmap.fromImage(self.qi).scaled(self.scale * self.rgb_arr.shape[1],
                                                        self.scale * self.rgb_arr.shape[0])
            painter = QPainter()
            painter.begin(self.pm)
            for (polygon,color) in zip(self.ROI_polygons, self.ROI_colors):
                painter.setPen(QPen(color))
                painter.setBrush(QBrush(color, Qt.VerPattern))
                painter.drawPolygon(polygon)
            painter.setBrush(QBrush(self.current_color, Qt.NoBrush))
            painter.setPen(QPen(self.current_color))
            for p in self.polygon_points:
                # these are the x,y - coords in pixel space in the QPixmap
                x_pm = (int(floor(p[0] / self.scale)) + 0.5) * self.scale
                y_pm = (int(floor(p[1] / self.scale)) + 0.5) * self.scale
                painter.drawRect(x_pm-0.5*self.scale, y_pm-0.5*self.scale, self.scale, self.scale)
            for idx in range(len(self.polygon_points)-1):
                x1_pm = (int(floor(self.polygon_points[idx][0] / self.scale)) + 0.5) * self.scale
                y1_pm = (int(floor(self.polygon_points[idx][1] / self.scale)) + 0.5) * self.scale
                x2_pm = (int(floor(self.polygon_points[idx+1][0] / self.scale)) + 0.5) * self.scale
                y2_pm = (int(floor(self.polygon_points[idx+1][1] / self.scale)) + 0.5) * self.scale
                painter.drawLine(x1_pm, y1_pm, x2_pm, y2_pm)
            self.imageLabel.setPixmap(self.pm)
            painter.end()
        else:
            pass

    def draw_polygon_line(self):
        # paint the polygon:
        self.pm = QPixmap.fromImage(self.qi).scaled(self.scale * self.rgb_arr.shape[1],
                                                    self.scale * self.rgb_arr.shape[0])
        painter = QPainter()
        painter.begin(self.pm)
        try:
            # use the color of the selected row
            item = self.ROI_table.selectedItems()[0]
            row = item.row()
            item = self.ROI_table.item(row, 1)
            self.current_color = item.background().color()
            self.current_ROI_Id_num = self.ROI_table.item(row, 3)
        except:
            # no row is selected.  Use the most recent color
            pass
        painter.setPen(QPen(self.current_color))
        for p in self.polygon_points:
            # these are the x,y - coords in pixel space in the QPixmap
            x_pm = (int(floor(p[0] / self.scale)) + 0.5) * self.scale
            y_pm = (int(floor(p[1] / self.scale)) + 0.5) * self.scale
            painter.drawRect(x_pm-0.5*self.scale, y_pm-0.5*self.scale, self.scale, self.scale)
        for idx in range(len(self.polygon_points)-1):
            x1_pm = (int(floor(self.polygon_points[idx][0] / self.scale)) + 0.5) * self.scale
            y1_pm = (int(floor(self.polygon_points[idx][1] / self.scale)) + 0.5) * self.scale
            x2_pm = (int(floor(self.polygon_points[idx+1][0] / self.scale)) + 0.5) * self.scale
            y2_pm = (int(floor(self.polygon_points[idx+1][1] / self.scale)) + 0.5) * self.scale
            painter.drawLine(x1_pm, y1_pm, x2_pm, y2_pm)
        # draw polygons
        for (polygon,color) in zip(self.ROI_polygons, self.ROI_colors):
            painter.setPen(QPen(color))
            painter.setBrush(QBrush(color, Qt.VerPattern))
            painter.drawPolygon(polygon)
        self.imageLabel.setPixmap(self.pm)
        painter.end()

    def compute_ROI_colors(self):
        Idx = 0
        for ID_num in self.ROI_Id_nums:
            # find the table row for the given ROI
            item = self.ROI_table.findItems(ID_num.text(), Qt.MatchContains)
            row = item[0].row()
            item = self.ROI_table.item(row, 1)
            self.ROI_colors[Idx] = item.background().color()
            Idx = Idx + 1

    def compute_ROI_pixelmap_locations(self):
        if self.btn_ROIs.isChecked():
            for (polygon, polygonIm) in zip(self.ROI_polygons,self.ROI_polygons_Im):
                for (point, pointIm) in zip(polygon, polygonIm):
                    point.setX(pointIm.x()*self.scale)
                    point.setY(pointIm.y()*self.scale)
            self.polygon = QPolygonF()
            self.polygon_points = []
            for pointIm in self.polygonIm_points:
                x_im = pointIm[0]
                y_im = pointIm[1]
                x = x_im * self.scale
                y = y_im * self.scale
                self.polygon_points.append([x, y])
                self.polygon.append(QPointF(x, y))

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
        self.pm = QPixmap.fromImage(self.qi).scaled(int(self.scale*self.rgb_arr.shape[1]), int(self.scale*self.rgb_arr.shape[0]))
        self.imageLabel.setPixmap(self.pm)
        self.imageLabel.mouseReleaseEvent  = self.plotSpectrum
        self.imageLabel.mousePressEvent = self.mousePress
        self.imageLabel.mouseMoveEvent = self.mouseMove
        self.imageLabel.wheelEvent = self.wheel
        self.scrollImage.setWidget(self.imageLabel)
        self.imageLabel.eventFilter = self.eventFilter
        self.compute_ROI_pixelmap_locations()
        self.draw_polygons()

    def actionZoomOut(self):
        if self.scrollImage.verticalScrollBar().isVisible():
            self.scale *= 1./1.2
            # create the rgb image
            self.imageLabel = QLabel()
            self.imageLabel.setMouseTracking(True)
            self.pm = QPixmap.fromImage(self.qi).scaled(int(self.scale*self.rgb_arr.shape[1]), int(self.scale*self.rgb_arr.shape[0]))
            self.imageLabel.setPixmap(self.pm)
            self.imageLabel.mouseReleaseEvent  = self.plotSpectrum
            self.imageLabel.mousePressEvent = self.mousePress
            self.imageLabel.mouseMoveEvent = self.mouseMove
            self.imageLabel.wheelEvent = self.wheel
            self.scrollImage.setWidget(self.imageLabel)
        self.imageLabel.eventFilter = self.eventFilter
        self.compute_ROI_pixelmap_locations()
        self.draw_polygons()

    def actionZoomInFromButton(self):
        self.scale *= 1.2
        # create the rgb image
        self.imageLabel = QLabel()
        self.imageLabel.setMouseTracking(True)
        self.pm = QPixmap.fromImage(self.qi).scaled(int(self.scale*self.rgb_arr.shape[1]), int(self.scale*self.rgb_arr.shape[0]))
        self.imageLabel.setPixmap(self.pm)
        self.imageLabel.mouseReleaseEvent  = self.plotSpectrum
        self.imageLabel.mousePressEvent = self.mousePress
        self.imageLabel.mouseMoveEvent = self.mouseMove
        self.imageLabel.wheelEvent = self.wheel
        self.scrollImage.setWidget(self.imageLabel)
        self.imageLabel.eventFilter = self.eventFilter
        # emit signal so that linked imageViewers can update their view parameters
        self.viewerParametersChanged.emit(self.key)
        self.compute_ROI_pixelmap_locations()
        self.draw_polygons()

    def actionZoomOutFromButton(self):
        if self.scrollImage.verticalScrollBar().isVisible():
            self.scale *= 1./1.2
            # create the rgb image
            self.imageLabel = QLabel()
            self.imageLabel.setMouseTracking(True)
            self.pm = QPixmap.fromImage(self.qi).scaled(int(self.scale*self.rgb_arr.shape[1]), int(self.scale*self.rgb_arr.shape[0]))
            self.imageLabel.setPixmap(self.pm)
            self.imageLabel.mouseReleaseEvent  = self.plotSpectrum
            self.imageLabel.mousePressEvent = self.mousePress
            self.imageLabel.mouseMoveEvent = self.mouseMove
            self.imageLabel.wheelEvent = self.wheel
            self.scrollImage.setWidget(self.imageLabel)
            # emit signal so that linked imageViewers can update their view parameters
            self.viewerParametersChanged.emit(self.key)
        self.imageLabel.eventFilter = self.eventFilter
        self.compute_ROI_pixelmap_locations()
        self.draw_polygons()

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
            self.pm = QPixmap.fromImage(self.qi).scaled(int(self.scale*self.rgb_arr.shape[1]), int(self.scale*self.rgb_arr.shape[0]))
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
            self.pm = QPixmap.fromImage(self.qi).scaled(int(self.scale*self.rgb_arr.shape[1]), int(self.scale*self.rgb_arr.shape[0]))
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
        # only recompute the image if we need to (speed.memory optimization)
        recomputeImage = False
        if (self.stretch['type_prev'] != self.stretch['type']):
            self.stretch['type_prev'] = self.stretch['type']
            recomputeImage = True
        if (self.stretch['type'] == 'slinear'):
            for band_idx in range(3):
                if (self.stretch['min'][band_idx] != self.stretch['min_prev'][band_idx]):
                    self.stretch['min_prev'][band_idx] = self.stretch['min'][band_idx]
                    recomputeImage = True
                if (self.stretch['max'][band_idx] != self.stretch['max_prev'][band_idx]):
                    self.stretch['max_prev'][band_idx] = self.stretch['max'][band_idx]
                    recomputeImage = True

        nrows = self.im.nrows
        ncols = self.im.ncols
        nbands = self.im.nbands
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
        # Create a mask to not use black pixels in the stretch computation
        ImagePixelMax = np.max(rgbArray, axis=2)
        unmaskedPixels = np.where(ImagePixelMax[:, :] > 0)
        # Do not mask black pixels if all pixels are black
        # - This is an odd case, but we would just display a fully black image, not cause error
        if (len(unmaskedPixels[0])==0):
            self.ignoreBlackRegions = False
        for band_idx in range(3):
            # stretch band
            if self.ignoreBlackRegions:
                if self.stretch['type'] == 's2pct':
                    bottom = np.percentile(rgbArray[unmaskedPixels[0], unmaskedPixels[1], band_idx], 2)
                    top = np.percentile(rgbArray[unmaskedPixels[0], unmaskedPixels[1], band_idx], 99)
                elif self.stretch['type'] == 's2pctDrk':
                    bottom = np.percentile(rgbArray[unmaskedPixels[0], unmaskedPixels[1], band_idx], 2)
                    top = np.max(rgbArray[unmaskedPixels[0], unmaskedPixels[1], band_idx])
                elif self.stretch['type'] == 'srange':
                    bottom = np.min(rgbArray[unmaskedPixels[0], unmaskedPixels[1], band_idx])
                    top = np.max(rgbArray[unmaskedPixels[0], unmaskedPixels[1], band_idx])
                elif self.stretch['type'] == 'slinear':
                    bottom = self.stretch['min'][band_idx]
                    top = self.stretch['max'][band_idx]
                else:
                    bottom = 0.
                    top = 1.
            else:
                if self.stretch['type'] == 's2pct':
                    bottom = np.percentile(rgbArray[:, :, band_idx], 2)
                    top = np.percentile(rgbArray[:, :, band_idx], 99)
                elif self.stretch['type'] == 's2pctDrk':
                    bottom = np.percentile(rgbArray[:, :, band_idx], 2)
                    top = np.max(rgbArray[:, :, band_idx])
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

    def actionCollectROIs(self):
        if self.btn_ROIs.isChecked():
            self.box_ROIs_frame.show()
            self.setStyleSheet("background-color: DarkGrey;")
            self.compute_ROI_pixelmap_locations()
            self.draw_polygons()
        else:
            self.box_ROIs_frame.hide()
            self.setStyleSheet("background-color: LightGrey;")
            self.update_image()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.polygon = QPolygonF()
            self.polygon_points = []
            self.polygonIm = QPolygon()
            self.polygonIm_points = []
            self.compute_ROI_pixelmap_locations()
            self.draw_polygons()

    def actionNewROI(self):
        rowPosition = self.ROI_table.rowCount()
        self.ROI_table.insertRow(rowPosition)
        # Set row contents
        # set deafult ROI name
        self.ROI_table.setItem(rowPosition, 0, QTableWidgetItem("ROI "+str(rowPosition)))
        # start with new color
        item = QTableWidgetItem('  ')
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        rgb = self.hex_to_rgb(self.colors[rowPosition % 20])
        item.setBackground(QColor(rgb[0], rgb[1], rgb[2]))
        self.ROI_table.setItem(rowPosition, 1, item)
        # start with 0 pixels
        item = QTableWidgetItem("0")
        item.setFlags(item.flags() ^ Qt.ItemIsEditable ^ Qt.ItemIsSelectable)
        self.ROI_table.setItem(rowPosition, 2, item)
        # set the unique id num
        self.ROI_table.setItem(rowPosition, 3, QTableWidgetItem("ROI_num_"+str(self.ROI_Id_num_count)))
        self.ROI_im_dict["ROI_num_"+str(self.ROI_Id_num_count)] = np.full((self.im.nrows*self.im.ncols,), False)
        self.ROI_Id_num_count = self.ROI_Id_num_count + 1

    def saveROIs(self):
        # get output filename
        fname, extension = QFileDialog.getSaveFileName(self, "Choose output name", self.im_dirname+"/ROIs", "CSV (*.csv)")
        # return with no action if user selected "cancel" button
        if (len(fname)==0):
            return
        # create a 2d (#pixels x #bands) lis of the pixel spectra
        if self.im_list is None:
            self.im_list = np.reshape(self.im_arr, [self.im.nrows * self.im.ncols, self.im.nbands])
        # open the file in the write mode
        f = open(fname, 'w')
        # write a row of headers to the csv file
        row_headers = "Name, Color, Pixel_x, Pixel_y"
        for b in self.im.bands.centers:
            row_headers = row_headers+","+str(b)
        f.write(row_headers+"\n")
        for key in self.ROI_im_dict.keys():
            # get the spectra for this ROI
            spec = self.im_list[self.ROI_im_dict[key],:]
            # get the pixel locations for this ROI
            pixel_xy = self.points_vstack[self.ROI_im_dict[key],:]
            # get the row for this ROI
            item = self.ROI_table.findItems(key, Qt.MatchContains)[0]
            row = item.row()
            # get the color (red, green, blue, alpha) for this ROI
            color = self.ROI_table.item(row,1).background().color().name()
            # get the name for this ROI
            name = self.ROI_table.item(row, 0).text()
            for p_xy,spec_row in zip(pixel_xy,spec):
                f.write(name+","+color+","+np.array2string(p_xy,separator=",")[1:-1]+
                                ","+np.array2string(spec_row,separator=",",max_line_width=30000)[1:-1]+"\n")
        f.close()

    def saveROIsPickle(self):
        # Get the data and put it into a dataFrame to save with pickle

        # parse the ROI file for ROI metadata
        names = list(np.unique(df['Name']))  # empty list
        ROIs = {}  # empty dictionary
        for name in names:
            ROIs[name] = ROI_struc()
            ROIs[name].name = name
            df_subset = df.loc[df['Name'] == name]
            ROIs[name].color = np.asarray(hex_to_rgb(df_subset.iloc[0, 1]), dtype=float)
            ROIs[name].npts = df_subset.shape[0]
            ROIs[name].locs = df_subset.iloc[:, 2:4].to_numpy()
            ROIs[name].spectra = df_subset.iloc[:, 4:df_subset.shape[1]].to_numpy()
            ROIs[name].wl = np.asarray(df_subset.columns.values.tolist()[4:df_subset.shape[1]], dtype=float)

    def ROI_table_item_selected(self):
        try:
            # get the first selected item
            item = self.ROI_table.selectedItems()[0]
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
                    self.ROI_table.setItem(row, 1, item)
                self.ROI_table.clearSelection()
                self.compute_ROI_colors()
                self.draw_polygons()
        except:
            pass

    def hex_to_rgb(self, value):
        value = value.lstrip('#')
        lv = len(value)
        return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

    def make_ROI_table_unselectable(self):
        # This freezes the states of the ROI table while the user is creating a new ROI
        self.ROI_table.setEnabled(False)

    def make_ROI_table_selectable(self):
        # This un-freezes the states of the ROI table so the user can select cells, change colors, etc.
        self.ROI_table.setEnabled(True)

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