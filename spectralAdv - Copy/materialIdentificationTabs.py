# This file contains the tabs layout and content for material identification
import operator
import os
import sys
import pickle
import numpy as np
from math import *
from spectral import *
from . import spectraViewer
from spectralAdv import specTools
from spectralAdv import materialIdentification
from fuzzywuzzy import process
from fuzzywuzzy import fuzz
from matplotlib.figure import Figure
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
#from pyqtgraph.widgets.MatplotlibWidget import *
import timeit
from pyqtgraph.widgets.MatplotlibWidget import *



### - Data Tab - ###

def tab_data_content(self):
    ##### Create data tab content #####

    # Image file selection
    self.label_image = QLabel('<b>Image:</b>')
    self.line_image_fname = QLineEdit('no file selected')
    self.btn_select_image = QPushButton('Select File')
    self.btn_select_image.clicked.connect(self.select_image)

    self.label_select_libraries = QLabel("<b>Identification Libraries:</b> (select in table below)")
    self.btn_select_library = QPushButton('Open library')
    self.btn_select_library.clicked.connect(self.select_library)
    # Library Table
    self.table_view = QTableWidget()
    #self.table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
    self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
    nCols = 9
    nRows = 0
    self.table_view.setRowCount(nRows)
    self.table_view.setColumnCount(nCols)
    self.table_view.setHorizontalHeaderLabels(['WL Scale Factor', 'Y Scale Factor','Num Spectra','Num Bands','Scale','Wavelengths','Range: min-max','Directory'])
    self.table_view.setColumnHidden(8, True)
    self.table_view.horizontalHeader().setStretchLastSection(True) # stretch last column
    self.table_view.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
    self.table_view.verticalHeader().setAlternatingRowColors(True)
    self.populate_table()


    #### spectra selection ####
    # build pixel spectrum plot
    self.label_pixel_spectrum = QLabel('<b>Pixel Spectrum:</b>')
    self.label_pixel_spectrum_sub = QLabel('paste from spectral plots, multiple spectra will be averaged')
    self.label_pixel_spectrum_sub.setWordWrap(True)
    self.btn_clear_pixel_spectra = QPushButton('Clear Spectra')
    self.btn_clear_pixel_spectra.clicked.connect(self.clear_pixel_spectra)
    self.btn_paste_pixel_spectrum = QPushButton('Paste Spectrum')
    self.btn_paste_pixel_spectrum.clicked.connect(self.paste_spectrum_request_pixel)
    try:
        self.MPWidget_pixel = MatplotlibWidgetBottomToolbar()
    except:
        self.MPWidget_pixel = MatplotlibWidget()
    self.subplot_pixel = self.MPWidget_pixel.getFigure().add_subplot(111)
    if self.settings.screen_width > 3000:
        self.subplot_pixel.axes.legend(fontsize=20)
        self.subplot_pixel.axes.xaxis.set_tick_params(labelsize=20)
        self.subplot_pixel.axes.yaxis.set_tick_params(labelsize=20)
    else:
        self.subplot_pixel.axes.legend()
    # Hide the right and top spines
    self.subplot_pixel.axes.spines['right'].set_visible(False)
    self.subplot_pixel.axes.spines['top'].set_visible(False)

    # build endmember spectrs plot
    self.label_endmember_spectrum = QLabel('<b>Manual Endmember Spectra:</b>')
    self.label_endmember_spectrum_sub = QLabel('paste from spectral plots')
    self.label_endmember_spectrum_sub.setWordWrap(True)
    self.btn_clear_endmember_spectra = QPushButton('Clear Spectra')
    self.btn_clear_endmember_spectra.clicked.connect(self.clear_endmember_spectra)
    self.btn_paste_endmember_spectrum = QPushButton('Paste Spectrum')
    self.btn_paste_endmember_spectrum.clicked.connect(self.paste_spectrum_request_endmember)
    try:
        self.MPWidget_endmember = MatplotlibWidgetBottomToolbar()
    except:
        self.MPWidget_endmember = MatplotlibWidget()
    self.subplot_endmember = self.MPWidget_endmember.getFigure().add_subplot(111)
    if self.settings.screen_width > 3000:
        #self.subplot_endmember.axes.legend(fontsize=20)
        self.subplot_endmember.axes.xaxis.set_tick_params(labelsize=20)
        self.subplot_endmember.axes.yaxis.set_tick_params(labelsize=20)
    else:
        pass
        #self.subplot_endmember.axes.legend()
    # Hide the right and top spines
    self.subplot_endmember.axes.spines['right'].set_visible(False)
    self.subplot_endmember.axes.spines['top'].set_visible(False)

def tab_data_layout(self):
    # add layout to data tab
    vBox = QVBoxLayout()
    # Image Selection
    hBox_image_selection = QHBoxLayout()
    hBox_image_selection.addWidget(self.label_image)
    hBox_image_selection.addWidget(self.line_image_fname)
    hBox_image_selection.addWidget(self.btn_select_image)
    vBox.addLayout(hBox_image_selection)
    vBox.addWidget(specTools.QHLine())

    # splitter to hold library and image spectra
    splitter = QSplitter(Qt.Vertical)
    # Library Selection
    library_selection_widget = QWidget()
    vBox_library_selection = QVBoxLayout()
    hBox_library_selection_label = QHBoxLayout()
    hBox_library_selection_label.addWidget(self.label_select_libraries)
    hBox_library_selection_label.addWidget(self.btn_select_library)
    hBox_library_selection_label.addStretch()
    vBox_library_selection.addLayout(hBox_library_selection_label)
    vBox_library_selection.addWidget(self.table_view)
    vBox_library_selection.addWidget(specTools.QHLine())
    library_selection_widget.setLayout(vBox_library_selection)
    splitter.addWidget(library_selection_widget)

    # Pixel and Endmember Selection
    pixel_endmember_selection_widget = QWidget()
    hBox_pixel_endmember_selection = QHBoxLayout()
    vBox_pixel_selection = QVBoxLayout()
    hBox_pixel_selection_label = QHBoxLayout()
    vbox_label = QVBoxLayout()
    vbox_label.addWidget(self.label_pixel_spectrum)
    vbox_label.addWidget(self.label_pixel_spectrum_sub)
    hBox_pixel_selection_label.addLayout(vbox_label)
    hBox_pixel_selection_label.addStretch()
    hBox_pixel_selection_label.addWidget(self.btn_paste_pixel_spectrum)
    hBox_pixel_selection_label.addWidget(self.btn_clear_pixel_spectra)
    vBox_pixel_selection.addLayout(hBox_pixel_selection_label)
    vBox_pixel_selection.addWidget(self.MPWidget_pixel)
    vBox_endmember_selection = QVBoxLayout()
    hBox_endmember_selection_label = QHBoxLayout()
    vbox_label = QVBoxLayout()
    vbox_label.addWidget(self.label_endmember_spectrum)
    vbox_label.addWidget(self.label_endmember_spectrum_sub)
    hBox_endmember_selection_label.addLayout(vbox_label)
    hBox_endmember_selection_label.addStretch()
    hBox_endmember_selection_label.addWidget(self.btn_paste_endmember_spectrum)
    hBox_endmember_selection_label.addWidget(self.btn_clear_endmember_spectra)
    vBox_endmember_selection.addLayout(hBox_endmember_selection_label)
    vBox_endmember_selection.addWidget(self.MPWidget_endmember)
    hBox_pixel_endmember_selection.addLayout(vBox_pixel_selection)
    hBox_pixel_endmember_selection.addWidget(specTools.QVLine())
    hBox_pixel_endmember_selection.addLayout(vBox_endmember_selection)
    pixel_endmember_selection_widget.setLayout(hBox_pixel_endmember_selection)
    splitter.addWidget(pixel_endmember_selection_widget)

    vBox.addWidget(splitter)
    # set as tab layout
    self.tab_data.setLayout(vBox)


### - Material Identification Tab - ###

def tab_material_id_content(self):
    # Create material id tab content
    # controls and notifications section
    self.btn_compute_identification = QPushButton('Compute Identificaiton')
    self.btn_clear_results = QPushButton('Clear Results')
    self.btn_clear_results.clicked.connect(self.clear_results)
    self.unclikcked_button_color = self.btn_compute_identification.palette().color(QPalette.Background)
    self.label_data_validation = QLabel('Data validation:')
    self.label_material_id_notifications = QTextEdit ()
    self.label_material_id_notifications.setText('Notifications here...')
    self.label_material_id_notifications.setLineWidth(5)
    self.label_material_id_notifications.setMaximumWidth(450)
    #self.label_material_id_notifications.setReadOnly()
    self.btn_search_and_sort_spectra_names = QPushButton('Sort Spectra by Text')
    self.btn_search_and_sort_spectra_names.clicked.connect(self.search_and_sort_spectra_names)

    # plot section
    try:
        self.MPWidget_material_id = MatplotlibWidgetBottomToolbar()
    except:
        self.MPWidget_material_id = MatplotlibWidget()
    self.subplot_material_id = self.MPWidget_material_id.getFigure().add_subplot(111)
    if self.settings.screen_width > 3000:
        self.subplot_material_id.axes.legend(fontsize=20)
        self.subplot_material_id.axes.xaxis.set_tick_params(labelsize=20)
        self.subplot_material_id.axes.yaxis.set_tick_params(labelsize=20)
    else:
        self.subplot_material_id.axes.legend()
    # Hide the right and top spines
    self.subplot_material_id.axes.spines['right'].set_visible(False)
    self.subplot_material_id.axes.spines['top'].set_visible(False)

    self.btn_open_in_spectralViewer = QPushButton('Open Spectral in Viewer')
    self.btn_open_in_spectralViewer.clicked.connect(self.open_in_spectralViewer)
    toolbar = self.MPWidget_material_id.getFigure().canvas.toolbar.addWidget(self.btn_open_in_spectralViewer)

    # click-drag functionality for plot

    # self.cid = self.subplot.figure.canvas.mpl_connect('draw_event', self.plot_changed)
    self.cid = self.MPWidget_material_id.getFigure().canvas.mpl_connect('button_press_event', self.onMouseDown)
    self.cid = self.MPWidget_material_id.getFigure().canvas.mpl_connect('button_release_event', self.onMouseUp)
    self.cid = self.MPWidget_material_id.getFigure().canvas.mpl_connect('motion_notify_event', self.onMouseMove)
    self.cid = self.MPWidget_material_id.getFigure().canvas.mpl_connect('axes_enter_event', self.event_update_material_id_plot)
    self.cid = self.MPWidget_material_id.getFigure().canvas.mpl_connect('resize_event', self.event_update_material_id_plot)

    # Library Table
    self.material_id_results_table = QTableWidget()
    self.material_id_results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    self.material_id_results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    nCols = 9
    nRows = 0
    self.material_id_results_table.setRowCount(nRows)
    self.material_id_results_table.setColumnCount(nCols)
    self.material_id_results_table.setHorizontalHeaderLabels(['Name','Probability','ACE','Subpixel Spectral Fit','Full Pixel Correlation','Abundnace','Library','Spectrum Index','Text Match Score'])

    self.material_id_results_table.horizontalHeader().setStretchLastSection(True) # stretch last column
    #self.material_id_results_table.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
    self.material_id_results_table.verticalHeader().setAlternatingRowColors(True)
    self.material_id_results_table.setSortingEnabled(True)
    self.material_id_results_table.verticalHeader().hide()
    self.material_id_results_table.setColumnHidden(7, True)
    self.material_id_results_table.setColumnHidden(8, True)
    for i in  range(1,6):
        self.material_id_results_table.horizontalHeader().setResizeMode(i, QtGui.QHeaderView.ResizeToContents)
    self.material_id_results_table.horizontalHeader().setDefaultSectionSize(50)
    # signal for selection changed
    self.material_id_results_table.itemSelectionChanged.connect(self.selection_changed)
    self.material_id_results_table.cellClicked.connect(self.cell_was_clicked)
    self.material_id_results_table.setColumnWidth(0, 800)

def tab_material_id_layout(self):

    # layout for top portion with notificaitons and plot
    hBoxlayout = QHBoxLayout()
    vBoxlayout_controls_notificaitons = QVBoxLayout()
    hBoxlayout_button = QHBoxLayout()
    hBoxlayout_button.addWidget(self.btn_compute_identification)
    hBoxlayout_button.addWidget(self.btn_clear_results)
    #hBoxlayout_button.addStretch()
    vBoxlayout_controls_notificaitons.addLayout(hBoxlayout_button)
    vBoxlayout_controls_notificaitons.addWidget(self.label_data_validation)
    vBoxlayout_controls_notificaitons.addWidget(self.label_material_id_notifications)
    vBoxlayout_controls_notificaitons.addWidget(self.btn_search_and_sort_spectra_names)
    hBoxlayout.addLayout(vBoxlayout_controls_notificaitons)
    hBoxlayout.addWidget(specTools.QVLine())
    vboxMPWidget_material_id = QVBoxLayout()
    hBoxlayout.addWidget(self.MPWidget_material_id)
    # widget to hold top portion with notificaitons and plot
    notification_plots_widget = QWidget()
    notification_plots_widget.setLayout(hBoxlayout)

    # bottom portion with results table
    vBoxlayout = QVBoxLayout()
    vBoxlayout.addWidget(self.material_id_results_table)
    # widget to hold top portion with notificaitons and plot
    notification_results_table_widget = QWidget()
    notification_results_table_widget.setLayout(vBoxlayout)

    # splitter to hold library and image spectra
    splitter = QSplitter(Qt.Vertical)
    splitter.addWidget(notification_plots_widget)
    splitter.addWidget(notification_results_table_widget)

    vBoxlayout = QVBoxLayout()
    vBoxlayout.addWidget(splitter)
    self.tab_material_id.setLayout(vBoxlayout)


### - Feature Building / Matching Tab - ###

def tab_feature_match_content(self):
    # Create feature matching tab content
    # controls and notifications section
    self.btn_compute_identification_fm = QPushButton('Match Features')
    self.btn_clear_results_fm = QPushButton('Clear Results')
    self.btn_clear_results_fm.clicked.connect(self.clear_results_fm)
    self.unclikcked_button_color_fm = self.btn_compute_identification_fm.palette().color(QPalette.Background)
    self.label_data_validation_fm = QLabel('Data validation:')
    self.label_feature_match_notifications = QTextEdit ()
    self.label_feature_match_notifications.setText('Notifications here...')
    self.label_feature_match_notifications.setLineWidth(5)
    self.label_feature_match_notifications.setMaximumWidth(450)
    #self.label_feature_match_notifications.setReadOnly()
    self.btn_search_and_sort_spectra_names_fm = QPushButton('Sort Spectra by Text')
    self.btn_search_and_sort_spectra_names_fm.clicked.connect(self.search_and_sort_spectra_names_fm)
    self.btn_export_selection_as_library_fm = QPushButton('Export Selection as Library')
    self.btn_export_selection_as_library_fm.clicked.connect(self.export_selection_as_library_fm)

    # plot section
    try:
        self.MPWidget_feature_match = MatplotlibWidgetBottomToolbar()
    except:
        self.MPWidget_feature_match = MatplotlibWidget()
    self.subplot_feature_match = self.MPWidget_feature_match.getFigure().add_subplot(111)
    if self.settings.screen_width > 3000:
        self.subplot_feature_match.axes.legend(fontsize=20)
        self.subplot_feature_match.axes.xaxis.set_tick_params(labelsize=20)
        self.subplot_feature_match.axes.yaxis.set_tick_params(labelsize=20)
    else:
        self.subplot_feature_match.axes.legend()
    # Hide the right and top spines
    self.subplot_feature_match.axes.spines['right'].set_visible(False)
    self.subplot_feature_match.axes.spines['top'].set_visible(False)

    self.btn_open_in_spectralViewer_fm = QPushButton('Open Spectral in Viewer')
    self.btn_open_in_spectralViewer_fm.clicked.connect(self.open_in_spectralViewer_fm)
    toolbar = self.MPWidget_feature_match.getFigure().canvas.toolbar.addWidget(self.btn_open_in_spectralViewer_fm)

    # click-drag functionality for plot

    # self.cid = self.subplot.figure.canvas.mpl_connect('draw_event', self.plot_changed)
    self.cid = self.MPWidget_feature_match.getFigure().canvas.mpl_connect('button_press_event', self.onMouseDown_fm)
    self.cid = self.MPWidget_feature_match.getFigure().canvas.mpl_connect('button_release_event', self.onMouseUp_fm)
    self.cid = self.MPWidget_feature_match.getFigure().canvas.mpl_connect('motion_notify_event', self.onMouseMove_fm)
    self.cid = self.MPWidget_feature_match.getFigure().canvas.mpl_connect('axes_enter_event', self.event_update_feature_match_plot)
    self.cid = self.MPWidget_feature_match.getFigure().canvas.mpl_connect('axes_enter_event', self.event_enter_feature_match_plot)
    self.cid = self.MPWidget_feature_match.getFigure().canvas.mpl_connect('axes_exit_event', self.event_exit_feature_match_plot)
    self.cid = self.MPWidget_feature_match.getFigure().canvas.mpl_connect('resize_event', self.event_update_feature_match_plot)
    #self.cid = self.MPWidget_feature_match.getFigure().canvas.mpl_connect('pick_event', self.onpick_fm)

    # Library Table
    self.feature_match_results_table = QTableWidget()
    self.feature_match_results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    self.feature_match_results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    nCols = 2
    nRows = 0
    self.feature_match_results_table.setRowCount(nRows)
    self.feature_match_results_table.setColumnCount(nCols)
    self.feature_match_results_table.setHorizontalHeaderLabels(['Name','Net Match'])

    self.feature_match_results_table.horizontalHeader().setStretchLastSection(True) # stretch last column
    #self.feature_match_results_table.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
    self.feature_match_results_table.verticalHeader().setAlternatingRowColors(True)
    self.feature_match_results_table.setSortingEnabled(True)
    self.feature_match_results_table.verticalHeader().hide()
    self.feature_match_results_table.setColumnHidden(7, True)
    self.feature_match_results_table.setColumnHidden(8, True)
    for i in  range(1,6):
        self.feature_match_results_table.horizontalHeader().setResizeMode(i, QtGui.QHeaderView.ResizeToContents)
    self.feature_match_results_table.horizontalHeader().setDefaultSectionSize(50)
    # signal for selection changed
    self.feature_match_results_table.itemSelectionChanged.connect(self.selection_changed_fm)
    self.feature_match_results_table.cellClicked.connect(self.cell_was_clicked_fm)
    self.feature_match_results_table.setColumnWidth(0, 800)

def tab_feature_match_layout(self):

    # layout for top portion with notificaitons and plot
    hBoxlayout = QHBoxLayout()
    vBoxlayout_controls_notificaitons = QVBoxLayout()
    hBoxlayout_button = QHBoxLayout()
    hBoxlayout_button.addWidget(self.btn_compute_identification_fm)
    hBoxlayout_button.addWidget(self.btn_clear_results_fm)
    #hBoxlayout_button.addStretch()
    vBoxlayout_controls_notificaitons.addLayout(hBoxlayout_button)
    vBoxlayout_controls_notificaitons.addWidget(self.label_data_validation)
    vBoxlayout_controls_notificaitons.addWidget(self.label_feature_match_notifications)
    vBoxlayout_controls_notificaitons.addWidget(self.btn_search_and_sort_spectra_names_fm)
    vBoxlayout_controls_notificaitons.addWidget(self.btn_export_selection_as_library_fm)
    hBoxlayout.addLayout(vBoxlayout_controls_notificaitons)
    hBoxlayout.addWidget(specTools.QVLine())
    vboxMPWidget_feature_match = QVBoxLayout()
    hBoxlayout.addWidget(self.MPWidget_feature_match)
    # widget to hold top portion with notificaitons and plot
    notification_plots_widget = QWidget()
    notification_plots_widget.setLayout(hBoxlayout)

    # bottom portion with results table
    vBoxlayout = QVBoxLayout()
    vBoxlayout.addWidget(self.feature_match_results_table)
    # widget to hold top portion with notificaitons and plot
    notification_results_table_widget = QWidget()
    notification_results_table_widget.setLayout(vBoxlayout)

    # splitter to hold library and image spectra
    splitter = QSplitter(Qt.Vertical)
    splitter.addWidget(notification_plots_widget)
    splitter.addWidget(notification_results_table_widget)

    vBoxlayout = QVBoxLayout()
    vBoxlayout.addWidget(splitter)
    self.tab_feature_match.setLayout(vBoxlayout)