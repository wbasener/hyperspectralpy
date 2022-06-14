import os
import spectralAdv.atmosphericConversions as atmpy
import numpy as np
from math import *
from spectral import *
from matplotlib.figure import Figure
from matplotlib.widgets import Cursor
import matplotlib.pyplot as plt
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from pyqtgraph.widgets.MatplotlibWidget import *
import pickle


# create a line to use as a seperator between sections of the GUI
class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        #self.setFrameShadow(QFrame.Sunken)


class BatchFileInfoDialog(QDialog):
    def __init__(self, parent=None):
        super(BatchFileInfoDialog, self).__init__(parent)

        # nice widget for editing the date
        self.Label_LineSuffix = QLabel('Suffix to add to filenames:')
        self.LineSuffix = QLineEdit(parent.batch_process_fname_suffix)
        self.Label_LineSubfolderName = QLabel('Folder name:')
        self.LineSubfolderName = QLineEdit(parent.batch_process_subfolder_name)

        # OK and Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.Label_LineSuffix)
        layout.addWidget(self.LineSuffix)
        layout.addWidget(self.Label_LineSubfolderName)
        layout.addWidget(self.LineSubfolderName)
        layout.addWidget(buttons)

    # get current date and time from the dialog
    def getSubfolderName(self):
        return self.LineSubfolderName.text()

    def getSuffix(self):
        return self.LineSuffix.text()

    # static method to create the dialog and return (date, time, accepted)
    @staticmethod
    def getFolderInfo(parent=None):
        dialog = BatchFileInfoDialog(parent)
        result = dialog.exec_()
        SubfolderName = dialog.getSubfolderName()
        Suffix = dialog.getSuffix()
        return (SubfolderName, Suffix, result == QDialog.Accepted)




class selectAtmGasPlotsDlg(QDialog):
    # signal to send back the new background removed spectrum
    updateData = pyqtSignal(dict)

    def __init__(self, atm_dict, parent=None):
        super(selectAtmGasPlotsDlg, self).__init__(parent)
        self.setWindowTitle("Select Gases to Plot")
        self.setGeometry(150, 150, 650, 450)
        self.atm_dict = atm_dict

        # list widget with list of images
        self.table_view = QTableWidget()
        self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        nCols = 3
        nRows = len(self.atm_dict)
        self.table_view.setRowCount(nRows)
        self.table_view.setColumnCount(nCols)
        self.table_view.setHorizontalHeaderLabels(['Gas Name', 'Plot Scale Factor', 'Column Density Modifier'])
        self.table_view.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.table_view.horizontalHeader().setStretchLastSection(True)  # stretch last column
        self.table_view.verticalHeader().hide()
        self.fill_table()

        # add buttons to layout
        vbox = QVBoxLayout()
        vbox.addWidget(self.table_view)
        self.setLayout(vbox)

    def fill_table(self):

        names = self.atm_dict.keys()
        idx = 0
        for name in names:
            # checkbox to select this gas
            chkBoxItem = QTableWidgetItem(name)
            rgb = self.hex_to_rgb(self.atm_dict[name]['color'])
            chkBoxItem.setForeground(QColor(rgb[0], rgb[1], rgb[2]))
            chkBoxItem.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled )
            chkBoxItem.setCheckState(Qt.Unchecked)
            self.table_view.setItem(idx, 0, chkBoxItem)
            # scale factor for this gas
            scaleFactorItem = QTableWidgetItem(str(self.atm_dict[name]['scale_factor']))
            self.table_view.setItem(idx, 1,scaleFactorItem )
            densietyFactorItem = QTableWidgetItem(str(0))
            self.table_view.setItem(idx, 2,densietyFactorItem )
            idx = idx + 1

        self.table_view.cellChanged.connect(self.data_changed)
        #self.table_view.itemClicked.connect(self.data_changed)

    def data_changed(self):
        checked_names = []
        scale_factors = []
        density_modifiers = []
        for idx in range(len(self.atm_dict)):
            # get the state of each checkbox
            # and prepare to send back to main GUi
            if self.table_view.item(idx,0).checkState() == 2:
                checked_names.append(self.table_view.item(idx,0).text())
                scale_factors.append(float(self.table_view.item(idx,1).text()))
                density_modifiers.append(float(self.table_view.item(idx,2).text()))

        atm_dict_selection = {'checked names': checked_names, 'scale factors': scale_factors, 'density modifiers': density_modifiers}
        self.updateData.emit(atm_dict_selection)

    def hex_to_rgb(self, value):
        value = value.lstrip('#')
        lv = len(value)
        return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))




class atmosphericConversionsGUI(QMainWindow):
    pasteSpectrumRequest = pyqtSignal(int)

    def __init__(self, settings=None, imageDir = None, libraryDir = None):
        super(atmosphericConversionsGUI, self).__init__()
        #self.setWindowModality(Qt.NonModal)
        self.settings = settings
        self.screen_width = self.settings.screen_width
        if self.screen_width > 3000:
            self.setGeometry(250, 150, 1800, 1600)  # (x_pos, y_pos, width, height)
        else:
            self.setGeometry(150, 50, 900, 800)  # (x_pos, y_pos, width, height)
        self.setWindowTitle("Atmospheric Conversion")
        # create data variables
        self.ok_atm_coeff, self.atm_coeff = atmpy.read_atmospheric_coefficients() # atmospheric coefficients from MODTRAN
        self.libraryDir = libraryDir # directory where user has recently loaded libraries
        self.imageDir = imageDir # directory where uses has recently loaded images
        self.wl = None # variable to hold wavelengths for the image to be converted
        self.im_input = None # image that will be converted, called the input image
        self.im_arr_input = None # input image data as an array
        self.mean_im_arr_input = None # mean of the input image
        self.mean_im_arr_output = None # mean of the output image (mean of input image after conversion)
        self.data_check = dict() # data check to indicate what data has been loaded
        self.data_check['image present'] = False # indicates if an input image has been loaded by the user
        self.pasteSpectrumRequestSentPixel = False # indicates if a paste request signal has been sent to the parent
        self.atm_plot_dict = {} # dictionary for plots of atmospheric gases

        # read the atmospheric gases library
        fname = 'atm_gas_dict.pkl'
        os.chdir(os.path.dirname(__file__))
        pkl_file = open(fname, 'rb')
        self.atm_dict = pickle.load(pkl_file)
        pkl_file.close()
        self.atm_dict_selection = {'checked names': [], 'scale factors': [], 'density modifiers': []}
        self.atm_dict_resampled = {}

        # Content for the GUI

        # Content - Image file selection
        self.label_image = QLabel('Image:')
        self.line_image_fname = QLineEdit('no file selected')
        self.btn_select_image = QPushButton('Select File')
        self.btn_select_image.clicked.connect(self.select_image)

        # Content - Converstion type selection
        self.label_conv_type = QLabel('Conversion Type:')
        self.btn_ref_to_rad = QRadioButton("Reflectance to Radiance")
        self.btn_ref_to_rad.setChecked(True)
        self.btn_rad_to_ref = QRadioButton("Radiance to Reflectance")
        # create a button group
        self.bg_conv_type = QButtonGroup()
        self.bg_conv_type.addButton(self.btn_ref_to_rad)
        self.bg_conv_type.addButton(self.btn_rad_to_ref)
        self.bg_conv_type.buttonClicked.connect(self.convert_all_spectra)
        # plot gases button
        self.btn_plot_gases = QPushButton('Plot Atmospheric Gases')
        self.btn_plot_gases.clicked.connect(self.select_atm_gases)

        # Content - Atmospheric parameter selection
        self.label_atm_parameters = QLabel('MODTRAN Options:')

        # Content - solar Zenith angle combobox
        self.label_cb_sza = QLabel('Solar Zenith Angle:')
        self.cb_sza = QComboBox()
        for deg in range(5, 90, 5):
            self.cb_sza.addItem(str(deg))
        self.cb_sza.currentIndexChanged.connect(self.convert_all_spectra)

        # Content - atmospheric combobox
        self.label_cb_atm = QLabel('Atmosphere:')
        self.cb_atm = QComboBox()
        self.cb_atm.addItems(["Tropical", "Midlat summer", "Midlat winter", "Subarc summer", "Subarc winter", "US standard 1976"])
        self.cb_atm.currentIndexChanged.connect(self.convert_all_spectra)

        # aerosol combobox
        self.label_cb_aerosol = QLabel('Aerosol:')
        self.cb_aerosol = QComboBox()
        self.cb_aerosol.addItems(["Rural: light pollution", "Rural: medium level pollution", "Rural: heavy pollution",
                                  "Urban: light pollution", "Urban: medium level pollution", "Urban: heavy pollution",
                                  "Desert: light pollution", "Desert: medium level pollution", "Desert: heavy pollution",
                                  "Maritime_Navy: light pollution", "Maritime_Navy: medium level pollution", "Maritime_Navy: heavy pollution"])
        self.cb_aerosol.currentIndexChanged.connect(self.convert_all_spectra)

        # water vapor combobox
        self.label_cb_watervapor = QLabel('Water Vapor:')
        self.cb_watervapor = QComboBox()
        for deg in range(5, 90, 5):
            self.cb_watervapor.addItem(str(deg))
        self.cb_watervapor.currentIndexChanged.connect(self.convert_all_spectra)

        # Content - Spectral Plot Section
        # add radio buttons to select plot type
        self.label_plot_type = QLabel('Select Plot:')
        self.btn_plot_input = QRadioButton("Mean Input Spectrum")
        self.btn_plot_input.setChecked(True)
        self.btn_plot_output = QRadioButton("Mean Output Spectrum")
        self.btn_plot_sel_input = QRadioButton("Selected Input Spectrum")
        self.btn_plot_sel_output = QRadioButton("Selected Output Spectrum")
        self.bg_plot_type = QButtonGroup()
        self.bg_plot_type.addButton(self.btn_plot_input)
        self.bg_plot_type.addButton(self.btn_plot_output)
        self.bg_plot_type.addButton(self.btn_plot_sel_input)
        self.bg_plot_type.addButton(self.btn_plot_sel_output)
        self.bg_plot_type.buttonClicked.connect(self.plot_type_changed)
        # checkbox for multiplot
        self.chk_multiplot = QCheckBox('Collect Multiple Output Plots')
        self.chk_multiplot.clicked.connect(self.chk_multiplot_clicked)

        # add the plots
        # build the mean input plot
        self.MPWidget_mean_spectrum_input = MatplotlibWidget()
        self.subplot_mean_spectrum_input = self.MPWidget_mean_spectrum_input.getFigure().add_subplot(111)
        if self.screen_width > 3000:
            self.subplot_mean_spectrum_input.axes.legend(fontsize=20)
            self.subplot_mean_spectrum_input.axes.xaxis.set_tick_params(labelsize=20)
            self.subplot_mean_spectrum_input.axes.yaxis.set_tick_params(labelsize=20)
        else:
            self.subplot_mean_spectrum_input.axes.legend()
        # Hide the right and top spines
        self.subplot_mean_spectrum_input.axes.spines['right'].set_visible(False)
        self.subplot_mean_spectrum_input.axes.spines['top'].set_visible(False)
        # build the mean output plot
        self.MPWidget_mean_spectrum_output = MatplotlibWidget()
        self.subplot_mean_spectrum_output = self.MPWidget_mean_spectrum_output.getFigure().add_subplot(111)
        if self.screen_width > 3000:
            self.subplot_mean_spectrum_output.axes.legend(fontsize=20)
            self.subplot_mean_spectrum_output.axes.xaxis.set_tick_params(labelsize=20)
            self.subplot_mean_spectrum_output.axes.yaxis.set_tick_params(labelsize=20)
        else:
            self.subplot_mean_spectrum_output.axes.legend()
        # Hide the right and top spines
        self.subplot_mean_spectrum_output.axes.spines['right'].set_visible(False)
        self.subplot_mean_spectrum_output.axes.spines['top'].set_visible(False)
        # build the selected spectra input plot
        self.MPWidget_selected_spectrum_input = MatplotlibWidget()
        self.subplot_selected_spectrum_input = self.MPWidget_selected_spectrum_input.getFigure().add_subplot(111)
        if self.screen_width > 3000:
            self.subplot_selected_spectrum_input.axes.legend(fontsize=20)
            self.subplot_selected_spectrum_input.axes.xaxis.set_tick_params(labelsize=20)
            self.subplot_selected_spectrum_input.axes.yaxis.set_tick_params(labelsize=20)
        else:
            self.subplot_selected_spectrum_input.axes.legend()
        # Hide the right and top spines
        self.subplot_selected_spectrum_input.axes.spines['right'].set_visible(False)
        self.subplot_selected_spectrum_input.axes.spines['top'].set_visible(False)
        # build the selected spectra output plot
        self.MPWidget_selected_spectrum_output = MatplotlibWidget()
        self.subplot_selected_spectrum_output = self.MPWidget_selected_spectrum_output.getFigure().add_subplot(111)
        if self.screen_width > 3000:
            self.subplot_selected_spectrum_output.axes.legend(fontsize=20)
            self.subplot_selected_spectrum_output.axes.xaxis.set_tick_params(labelsize=20)
            self.subplot_selected_spectrum_output.axes.yaxis.set_tick_params(labelsize=20)
        else:
            self.subplot_selected_spectrum_output.axes.legend()
        # Hide the right and top spines
        self.subplot_selected_spectrum_output.axes.spines['right'].set_visible(False)
        self.subplot_selected_spectrum_output.axes.spines['top'].set_visible(False)
        # initially show the input plot and hide the output plot
        self.MPWidget_mean_spectrum_input.show()
        self.MPWidget_mean_spectrum_output.hide()
        self.MPWidget_selected_spectrum_input.hide()
        self.MPWidget_selected_spectrum_output.hide()

        # content - buttons to paste and clear selected spectra plots
        self.btn_clear_pixel_spectra = QPushButton('Clear Spectra')
        self.btn_clear_pixel_spectra.clicked.connect(self.clear_pixel_spectra)
        self.btn_paste_pixel_spectrum = QPushButton('Paste Spectrum')
        self.btn_paste_pixel_spectrum.clicked.connect(self.paste_spectrum_request_pixel)
        self.btn_clear_pixel_spectra.hide()
        self.btn_paste_pixel_spectrum.hide()

        # Content - Apply to images buttons
        self.btn_convert_single_image = QPushButton('Convert Single Image')
        self.btn_convert_batch_images = QPushButton('Batch Convert Images')
        self.btn_convert_single_image.clicked.connect(self.convert_single_image)
        self.btn_convert_batch_images.clicked.connect(self.convert_batch_images)

        # create the statusbar
        self.statusBar = QStatusBar()
        # add a progressbar to the statusbar
        self.progressBar = QProgressBar()
        self.statusBar.addPermanentWidget(self.progressBar)
        self.progressBar.setGeometry(30, 40, 200, 25)
        self.progressBar.setValue(0)
        # set the staus bar
        self.setStatusBar(self.statusBar)

        # add layout
        vBox = QVBoxLayout() # main vBox layout
        # Image Selection
        hBox_image_selection = QHBoxLayout()
        hBox_image_selection.addWidget(self.label_image)
        hBox_image_selection.addWidget(self.line_image_fname)
        hBox_image_selection.addWidget(self.btn_select_image)
        vBox.addLayout(hBox_image_selection)
        vBox.addWidget(QHLine())
        # Conversion type seleciton
        hBox_conversion_type_selection = QHBoxLayout()
        hBox_conversion_type_selection.addWidget(self.label_conv_type)
        hBox_conversion_type_selection.addWidget(self.btn_ref_to_rad)
        hBox_conversion_type_selection.addWidget(self.btn_rad_to_ref)
        hBox_conversion_type_selection.addWidget(self.btn_plot_gases)
        hBox_conversion_type_selection.addStretch()
        vBox.addLayout(hBox_conversion_type_selection)
        # Parameter Selection
        hBox_parameter_selection = QHBoxLayout()
        hBox_parameter_selection.addWidget(self.label_atm_parameters)
        hBox_parameter_selection.addWidget(self.label_cb_sza)
        hBox_parameter_selection.addWidget(self.cb_sza)
        hBox_parameter_selection.addWidget(self.label_cb_atm)
        hBox_parameter_selection.addWidget(self.cb_atm)
        hBox_parameter_selection.addWidget(self.label_cb_aerosol)
        hBox_parameter_selection.addWidget(self.cb_aerosol)
        hBox_parameter_selection.addWidget(self.label_cb_watervapor)
        hBox_parameter_selection.addWidget(self.cb_watervapor)
        hBox_parameter_selection.addStretch()
        vBox.addLayout(hBox_parameter_selection)
        vBox.addWidget(QHLine())
        # Plot area
        hBox_plot_type_selection = QHBoxLayout()
        hBox_plot_type_selection.addWidget(self.label_plot_type)
        hBox_plot_type_selection.addWidget(self.btn_plot_input)
        hBox_plot_type_selection.addWidget(self.btn_plot_output)
        hBox_plot_type_selection.addWidget(self.btn_plot_sel_input)
        hBox_plot_type_selection.addWidget(self.btn_plot_sel_output)
        hBox_plot_type_selection.addStretch()
        hBox_plot_type_selection.addWidget(self.chk_multiplot)
        vBox.addLayout(hBox_plot_type_selection)
        vBox_plot = QVBoxLayout()
        vBox_plot.addWidget(self.MPWidget_mean_spectrum_input)
        vBox_plot.addWidget(self.MPWidget_mean_spectrum_output)
        vBox_plot.addWidget(self.MPWidget_selected_spectrum_input)
        vBox_plot.addWidget(self.MPWidget_selected_spectrum_output)
        vBox.addLayout(vBox_plot)
        vBox.addWidget(QHLine())
        # Convert Images Buttons
        hBox_convert_images = QHBoxLayout()
        hBox_convert_images.addWidget(self.btn_paste_pixel_spectrum)
        hBox_convert_images.addWidget(self.btn_clear_pixel_spectra)
        hBox_convert_images.addStretch()
        hBox_convert_images.addWidget(self.btn_convert_single_image)
        hBox_convert_images.addWidget(self.btn_convert_batch_images)
        vBox.addLayout(hBox_convert_images)

        # create the central widget and set its layout
        self.widget_central = QWidget()
        self.widget_central.setLayout(vBox)
        self.setCentralWidget(self.widget_central)

    def convert_all_spectra(self):
        self.convert_selected_spectra()
        self.convert_mean_spectrum()

    def convert_selected_spectra(self):
        # do nothing if there are no pasted lines
        lines = self.MPWidget_selected_spectrum_input.getFigure().gca().lines
        if len(lines)==0:
            return

        self.subplot_selected_spectrum_output.axes.clear()

        # get the parameters for conversion
        if self.btn_ref_to_rad.isChecked():
            conversion_type = 'ref_to_rad'
        else:
            conversion_type = 'rad_to_ref'
        solar_zenith_angle = int(self.cb_sza.currentText())
        atmospheric_index = self.cb_atm.currentIndex()
        aerosol_index = self.cb_aerosol.currentIndex()

        self.atm_parameters_text = '-SZA' + self.cb_sza.currentText() + '-' + self.cb_atm.currentText() + '-' + self.cb_aerosol.currentText()

        # convert each spectrum in the input plot and add the result to the output plot
        first_iteration_check = True
        for line in lines:
            if line._label != 'atm_gas':
                spectrum = line.get_ydata()
                wl = line.get_xdata()

                # do the converstion
                ok, converted_spectrum = atmpy.convert_spectrum(spectrum, wl, self.atm_coeff,
                                                                conversion_type, solar_zenith_angle,
                                                                atmospheric_index, aerosol_index,
                                                                self.atm_dict_resampled, self.atm_dict_selection)

                self.subplot_selected_spectrum_output.plot(wl, converted_spectrum,
                                                          marker='.',
                                                          label=line._label+self.atm_parameters_text,
                                                          linewidth=1)
                if self.settings.screen_width > 3000:
                    self.subplot_selected_spectrum_output.axes.legend(fontsize=20)
                else:
                    self.subplot_selected_spectrum_output.axes.legend()

                # get the yrange to match all the plotted spectra
                yrange_line = self.get_plot_min_max(wl, converted_spectrum)
                if first_iteration_check == True:
                    first_iteration_check = False
                    yrange = yrange_line
                else:
                    yrange[0] = np.min((yrange[0], yrange_line[0]))
                    yrange[1] = np.max((yrange[1], yrange_line[1]))

        if self.btn_rad_to_ref.isChecked():
            if self.screen_width > 3000:
                self.subplot_selected_spectrum_output.axes.legend(fontsize=20)
                self.subplot_selected_spectrum_output.set_xlabel('Wavelength', fontsize=30)
                self.subplot_selected_spectrum_output.set_ylabel('Reflectance', fontsize=30)
            else:
                self.subplot_selected_spectrum_output.axes.legend()
                self.subplot_selected_spectrum_output.set_xlabel('Wavelength')
                self.subplot_selected_spectrum_output.set_ylabel('Reflectance')
        else:
            if self.screen_width > 3000:
                self.subplot_selected_spectrum_output.axes.legend(fontsize=20)
                self.subplot_selected_spectrum_output.set_xlabel('Wavelength', fontsize=30)
                self.subplot_selected_spectrum_output.set_ylabel('Radiance', fontsize=30)
            else:
                self.subplot_selected_spectrum_output.axes.legend()
                self.subplot_selected_spectrum_output.set_xlabel('Wavelength')
                self.subplot_selected_spectrum_output.set_ylabel('Radiance')

            self.subplot_selected_spectrum_output.axes.set_ylim(yrange)
        # plot selected atmospheric gases
        self.plot_atm_gases(self.MPWidget_selected_spectrum_output, self.subplot_selected_spectrum_output)
        # draw the plot
        self.MPWidget_selected_spectrum_output.draw()

        # return if no image is present
        if self.data_check['image present'] == False:
            return
        self.update_plot()



    def convert_mean_spectrum(self):
        # return if no image is present
        if self.data_check['image present'] == False:
            return

        # get the parameters for conversion
        if self.btn_ref_to_rad.isChecked():
            conversion_type = 'ref_to_rad'
        else:
            conversion_type = 'rad_to_ref'
        solar_zenith_angle = int(self.cb_sza.currentText())
        atmospheric_index = self.cb_atm.currentIndex()
        aerosol_index = self.cb_aerosol.currentIndex()

        # do the converstion
        ok, self.mean_im_arr_output = atmpy.convert_spectrum(self.mean_im_arr_input, self.wl,
                                                             self.atm_coeff, conversion_type, solar_zenith_angle,
                                                             atmospheric_index, aerosol_index,
                                                             self.atm_dict_resampled, self.atm_dict_selection)

        self.atm_parameters_text = '-SZA'+self.cb_sza.currentText()+'-'+self.cb_atm.currentText()+'-'+self.cb_aerosol.currentText()

        if ok == False:
            return

        self.update_plot()


    def update_plot(self):

        try:
            if self.wl == None:
                return
        except:
            pass

        # Case 1: reflectance input and radiance output
        if self.btn_ref_to_rad.isChecked():
            # plot the input spectrum
            self.subplot_mean_spectrum_input.axes.clear()
            self.subplot_mean_spectrum_input.plot(self.wl, self.mean_im_arr_input,
                                            color='b',
                                            marker='.',
                                            label='Input Reflectance',
                                            linewidth=1)
            if self.screen_width > 3000:
                self.subplot_mean_spectrum_input.axes.legend(fontsize=20)
                self.subplot_mean_spectrum_input.set_xlabel('Wavelength', fontsize=30)
                self.subplot_mean_spectrum_input.set_ylabel('Reflectance', fontsize=30)
            else:
                self.subplot_mean_spectrum_input.axes.legend()
                self.subplot_mean_spectrum_input.set_xlabel('Wavelength')
                self.subplot_mean_spectrum_input.set_ylabel('Reflectance')
            # plot selected atmospheric gases
            self.plot_atm_gases(self.MPWidget_mean_spectrum_input, self.subplot_mean_spectrum_input)
            # draw the plot
            self.MPWidget_mean_spectrum_input.draw()

            # plot the output spectrum/spectra
            if not self.chk_multiplot.isChecked():
                self.subplot_mean_spectrum_output.axes.clear()
                self.subplot_mean_spectrum_output.plot(self.wl, self.mean_im_arr_output,
                                                color='r',
                                                marker='.',
                                                label='Output Radiance'+self.atm_parameters_text,
                                                linewidth=1)
            else:
                self.subplot_mean_spectrum_output.plot(self.wl, self.mean_im_arr_output,
                                                marker='.',
                                                label='Output Reflectance'+self.atm_parameters_text,
                                                linewidth=1)
            if self.screen_width > 3000:
                self.subplot_mean_spectrum_output.axes.legend(fontsize=20)
                self.subplot_mean_spectrum_output.set_xlabel('Wavelength', fontsize=30)
                self.subplot_mean_spectrum_output.set_ylabel('Radiance', fontsize=30)
            else:
                self.subplot_mean_spectrum_output.axes.legend()
                self.subplot_mean_spectrum_output.set_xlabel('Wavelength')
                self.subplot_mean_spectrum_output.set_ylabel('Radiance')
            # plot selected atmospheric gases
            self.plot_atm_gases(self.MPWidget_mean_spectrum_output, self.subplot_mean_spectrum_output)
            # draw the plot
            self.MPWidget_mean_spectrum_output.draw()

        # Case 2: radiance input and reflectance output
        if self.btn_rad_to_ref.isChecked():
            self.subplot_mean_spectrum_input.axes.clear()
            self.subplot_mean_spectrum_input.plot(self.wl, self.mean_im_arr_input,
                                            color='r',
                                            marker='.',
                                            label='Input Radiance',
                                            linewidth=1)
            if self.screen_width > 3000:
                self.subplot_mean_spectrum_input.axes.legend(fontsize=20)
                self.subplot_mean_spectrum_input.set_xlabel('Wavelength', fontsize=30)
                self.subplot_mean_spectrum_input.set_ylabel('Radiance', fontsize=30)
            else:
                self.subplot_mean_spectrum_input.axes.legend()
                self.subplot_mean_spectrum_input.set_xlabel('Wavelength')
                self.subplot_mean_spectrum_input.set_ylabel('Radiance')
            # plot selected atmospheric gases
            self.plot_atm_gases(self.MPWidget_mean_spectrum_input, self.subplot_mean_spectrum_input)
            # draw the plot
            self.MPWidget_mean_spectrum_input.draw()

            # plot the radiance output
            if not self.chk_multiplot.isChecked():
                self.subplot_mean_spectrum_output.axes.clear()
                self.subplot_mean_spectrum_output.plot(self.wl, self.mean_im_arr_output,
                                                color='b',
                                                marker='.',
                                                label='Output Reflectance'+self.atm_parameters_text,
                                                linewidth=1)
                # get the y-range for the single spectrum
                yrange = self.get_plot_min_max(self.wl, self.mean_im_arr_output)
            else:
                self.subplot_mean_spectrum_output.plot(self.wl, self.mean_im_arr_output,
                                                marker='.',
                                                label='Output Reflectance'+self.atm_parameters_text,
                                                linewidth=1)
                # get the yrange to match all the plotted spectra
                first_iteration_check = True
                lines = self.MPWidget_mean_spectrum_output.getFigure().gca().lines
                for line in lines:
                    spectrum = line.get_ydata()
                    wl = line.get_xdata()
                    yrange_line = self.get_plot_min_max(wl, spectrum)
                    if first_iteration_check == True:
                        first_iteration_check = False
                        yrange = yrange_line
                    else:
                        yrange[0] = np.min((yrange[0],yrange_line[0]))
                        yrange[1] = np.max((yrange[1],yrange_line[1]))

            if self.screen_width > 3000:
                self.subplot_mean_spectrum_output.axes.legend(fontsize=20)
                self.subplot_mean_spectrum_output.set_xlabel('Wavelength', fontsize=30)
                self.subplot_mean_spectrum_output.set_ylabel('Reflectance', fontsize=30)
            else:
                self.subplot_mean_spectrum_output.axes.legend()
                self.subplot_mean_spectrum_output.set_xlabel('Wavelength')
                self.subplot_mean_spectrum_output.set_ylabel('Reflectance')

            self.subplot_mean_spectrum_output.axes.set_ylim(yrange)
            # plot selected atmospheric gases
            self.plot_atm_gases(self.MPWidget_mean_spectrum_output, self.subplot_mean_spectrum_output)
            # draw the plot
            self.MPWidget_mean_spectrum_output.draw()

    def update_selected_spectra_plots(self):
        lines = self.MPWidget_selected_spectrum_input.getFigure().gca().lines
        self.subplot_selected_spectrum_input.axes.clear()
        for line in lines:
            if line._label != 'atm_gas':
                self.subplot_selected_spectrum_input.plot(line._x,line._y,
                                  color = line._color,
                                  label = line._label,
                                  marker='.',
                                  linewidth = 1)
        if self.btn_rad_to_ref.isChecked():
            if self.screen_width > 3000:
                self.subplot_selected_spectrum_input.axes.legend(fontsize=20)
                self.subplot_selected_spectrum_input.set_xlabel('Wavelength', fontsize=30)
                self.subplot_selected_spectrum_input.set_ylabel('Radiance', fontsize=30)
            else:
                self.subplot_selected_spectrum_input.axes.legend()
                self.subplot_selected_spectrum_input.set_xlabel('Wavelength')
                self.subplot_selected_spectrum_input.set_ylabel('Radiance')
        else:
            if self.screen_width > 3000:
                self.subplot_selected_spectrum_input.axes.legend(fontsize=20)
                self.subplot_selected_spectrum_input.set_xlabel('Wavelength', fontsize=30)
                self.subplot_selected_spectrum_input.set_ylabel('Reflectance', fontsize=30)
            else:
                self.subplot_selected_spectrum_input.axes.legend()
                self.subplot_selected_spectrum_input.set_xlabel('Wavelength')
                self.subplot_selected_spectrum_input.set_ylabel('Reflectance')
        # plot selected atmospheric gases
        self.plot_atm_gases(self.MPWidget_selected_spectrum_input, self.subplot_selected_spectrum_input)
        # draw the plot
        self.MPWidget_selected_spectrum_input.draw()

        lines = self.MPWidget_selected_spectrum_output.getFigure().gca().lines
        self.subplot_selected_spectrum_output.axes.clear()
        for line in lines:
            if line._label != 'atm_gas':
                self.subplot_selected_spectrum_output.plot(line._x,line._y,
                                  color = line._color,
                                  label = line._label,
                                  marker='.',
                                  linewidth = 1)
        if self.btn_rad_to_ref.isChecked():
            if self.screen_width > 3000:
                self.subplot_selected_spectrum_output.axes.legend(fontsize=20)
                self.subplot_selected_spectrum_output.set_xlabel('Wavelength', fontsize=30)
                self.subplot_selected_spectrum_output.set_ylabel('Radiance', fontsize=30)
            else:
                self.subplot_selected_spectrum_output.axes.legend()
                self.subplot_selected_spectrum_output.set_xlabel('Wavelength')
                self.subplot_selected_spectrum_output.set_ylabel('Radiance')
        else:
            if self.screen_width > 3000:
                self.subplot_selected_spectrum_output.axes.legend(fontsize=20)
                self.subplot_selected_spectrum_output.set_xlabel('Wavelength', fontsize=30)
                self.subplot_selected_spectrum_output.set_ylabel('Reflectance', fontsize=30)
            else:
                self.subplot_selected_spectrum_output.axes.legend()
                self.subplot_selected_spectrum_output.set_xlabel('Wavelength')
                self.subplot_selected_spectrum_output.set_ylabel('Reflectance')
        # plot selected atmospheric gases
        self.plot_atm_gases(self.MPWidget_selected_spectrum_output, self.subplot_selected_spectrum_output)
        # draw the plot
        self.MPWidget_selected_spectrum_output.draw()

    def select_atm_gases(self):
        #if hasattr(self,'editDataDlg') == False:
        self.selectAtmGasPlotsDlg = selectAtmGasPlotsDlg(self.atm_dict, self)
        self.selectAtmGasPlotsDlg.updateData.connect(self.update_atm_plot)
        self.selectAtmGasPlotsDlg.show()
        self.selectAtmGasPlotsDlg.raise_()
        self.selectAtmGasPlotsDlg.activateWindow()

    def update_atm_plot(self, atm_dict_selection):
        self.atm_dict_selection = atm_dict_selection
        self.convert_all_spectra()
        #self.convert_mean_spectrum()
        #self.update_selected_spectra_plots()

    def plot_atm_gases(self, MPWidget, subplot):

        if self.data_check['image present'] == False:
            return

        lines = MPWidget.getFigure().gca().lines
        for line in lines:
            if line._label == 'atm_gas':
                line.remove()

        # plot selected atmospheric gases
        if len(self.atm_dict_selection['checked names']) > 0:

            yrange = subplot.get_ylim()
            xrange = subplot.get_xlim()
            for name,scale_factor in zip(self.atm_dict_selection['checked names'],self.atm_dict_selection['scale factors']):
                plot_gas_resampled = True

                if plot_gas_resampled == True:

                    # scale and plot
                    atm_s = self.atm_dict_resampled[name]
                    atm_s = yrange[0] + (yrange[1]-yrange[0])*atm_s**scale_factor

                    # plot using the color and scale factor from the atm gas parameters dict if available
                    atm_color = self.atm_dict[name]['color']
                    subplot.plot(self.wl, atm_s, color=atm_color, label = 'atm_gas', alpha=0.5)
                    subplot.fill_between(self.wl, atm_s, yrange[1] * np.ones(len(atm_s)), color=atm_color, alpha=0.3)
                else:
                    # convert atm wl if needed
                    if np.mean(self.wl) > 100:
                        #convert atmospheric gas spectra to nanometers
                        atm_wl = self.atm_dict[name]['wl']*1000
                    else:
                        atm_wl = self.atm_dict[name]['wl']
                    # trim wavelenghts to match range of plot
                    min_idx = np.argmin(abs(atm_wl - np.min(self.wl)))
                    max_idx = np.argmin(abs(atm_wl - np.max(self.wl)))
                    atm_wl = atm_wl[min_idx:max_idx]

                    # scale and plot
                    atm_s = self.atm_dict[name]['transmission'][min_idx:max_idx]
                    atm_s = yrange[0] + (yrange[1]-yrange[0])*atm_s**scale_factor

                    # plot using the color and scale factor from the atm gas parameters dict if available
                    atm_color = self.atm_dict[name]['color']
                    subplot.plot(atm_wl, atm_s, color=atm_color, label = 'atm_gas', alpha=0.5)

            subplot.set_ylim(yrange)
            subplot.set_xlim(xrange)

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
        if type(fname_image) is tuple:
          fname_image = fname_image[0]
        fname_image_orig = fname_image
        fname_image, ok = self.is_image_file(fname_image)
        if not ok:
            QMessageBox.warning(self, "File is not valid ENVI image",
                                "File Name: %s" % (os.path.basename(fname_image)))

        self.line_image_fname.setText(fname_image_orig)
        # read image data to variables
        self.im_input = envi.open(fname_image + '.hdr')
        self.im_input = self.apply_bbl(self.im_input)

        self.im_arr_input = self.envi_load(self.im_input)
        self.data_check['image present'] = True
        self.mean_im_arr_input = np.mean(np.mean(self.im_arr_input, 0), 0).flatten()
        self.wl = np.asarray(self.im_input.bands.centers).flatten()
        self.convert_mean_spectrum()

        # convert to microns if needed
        if np.mean(self.wl)>100:
            self.wl = self.wl/1000.

        self.atm_dict_resampled = atmpy.resample_atm_dict(self.atm_dict,self.wl)

    def chk_multiplot_clicked(self):
        self.subplot_mean_spectrum_output.axes.clear()
        self.convert_selected_spectra()

    def clear_pixel_spectra(self):
        self.subplot_selected_spectrum_input.axes.clear()
        # plot selected atmospheric gases
        self.plot_atm_gases(self.MPWidget_selected_spectrum_input, self.subplot_selected_spectrum_input)
        # draw the plot
        self.MPWidget_selected_spectrum_input.draw()

        self.subplot_selected_spectrum_output.axes.clear()
        # plot selected atmospheric gases
        self.plot_atm_gases(self.MPWidget_selected_spectrum_output, self.subplot_selected_spectrum_output)
        # draw the plot
        self.MPWidget_selected_spectrum_output.draw()

    def paste_spectrum_request_pixel(self):
            self.pasteSpectrumRequestSentPixel = True
            self.pasteSpectrumRequest.emit(1)

    def paste_spectrum(self, pasted_spectrum):
        for key in pasted_spectrum.keys():

            pasted_spectrum_Line2D = pasted_spectrum[key]

            if self.pasteSpectrumRequestSentPixel:
                self.subplot_selected_spectrum_input.plot(pasted_spectrum_Line2D._x,pasted_spectrum_Line2D._y,
                                  color = pasted_spectrum_Line2D._color,
                                  label = pasted_spectrum_Line2D._label,
                                  marker='.',
                                  linewidth = 1)
        if self.btn_rad_to_ref.isChecked():
            if self.screen_width > 3000:
                self.subplot_selected_spectrum_input.axes.legend(fontsize=20)
                self.subplot_selected_spectrum_input.set_xlabel('Wavelength', fontsize=30)
                self.subplot_selected_spectrum_input.set_ylabel('Radiance', fontsize=30)
            else:
                self.subplot_selected_spectrum_input.axes.legend()
                self.subplot_selected_spectrum_input.set_xlabel('Wavelength')
                self.subplot_selected_spectrum_input.set_ylabel('Radiance')
        else:
            if self.screen_width > 3000:
                self.subplot_selected_spectrum_input.axes.legend(fontsize=20)
                self.subplot_selected_spectrum_input.set_xlabel('Wavelength', fontsize=30)
                self.subplot_selected_spectrum_input.set_ylabel('Reflectance', fontsize=30)
            else:
                self.subplot_selected_spectrum_input.axes.legend()
                self.subplot_selected_spectrum_input.set_xlabel('Wavelength')
                self.subplot_selected_spectrum_input.set_ylabel('Reflectance')
        # plot selected atmospheric gases
        self.plot_atm_gases(self.MPWidget_selected_spectrum_input, self.subplot_selected_spectrum_input)
        # draw the plot
        self.MPWidget_selected_spectrum_input.draw()

        # record that the request for paste spectrum has been completed
        self.pasteSpectrumRequestSentEndmember = False
        self.pasteSpectrumRequestSentPixel = False

        # convert the input spectra and plot the results in the output plot
        self.convert_selected_spectra()

    def plot_type_changed(self):
        if self.btn_plot_input.isChecked():
            self.MPWidget_mean_spectrum_input.show()
            self.MPWidget_mean_spectrum_output.hide()
            self.MPWidget_selected_spectrum_input.hide()
            self.MPWidget_selected_spectrum_output.hide()
            self.btn_clear_pixel_spectra.hide()
            self.btn_paste_pixel_spectrum.hide()
        if self.btn_plot_output.isChecked():
            self.MPWidget_mean_spectrum_input.hide()
            self.MPWidget_mean_spectrum_output.show()
            self.MPWidget_selected_spectrum_input.hide()
            self.MPWidget_selected_spectrum_output.hide()
            self.btn_clear_pixel_spectra.hide()
            self.btn_paste_pixel_spectrum.hide()
        if self.btn_plot_sel_input.isChecked():
            self.MPWidget_mean_spectrum_input.hide()
            self.MPWidget_mean_spectrum_output.hide()
            self.MPWidget_selected_spectrum_input.show()
            self.MPWidget_selected_spectrum_output.hide()
            self.btn_clear_pixel_spectra.show()
            self.btn_paste_pixel_spectrum.show()
        if self.btn_plot_sel_output.isChecked():
            self.MPWidget_mean_spectrum_input.hide()
            self.MPWidget_mean_spectrum_output.hide()
            self.MPWidget_selected_spectrum_input.hide()
            self.MPWidget_selected_spectrum_output.show()
            self.btn_clear_pixel_spectra.hide()
            self.btn_paste_pixel_spectrum.hide()

    def get_plot_min_max(self, wl, spectrum):
        # This function computes a min and max excluding extreme outliers.
        # This is done by first selecting all y-values for points away from water bands
        # then computing the mean and standard deviation for these y-values
        # all y-values outside a 3 standard deviation window around the mean are considered outliers
        # and the min and max is computed from the remaining values.

        # get the wavelenghts in micrometers
        if np.mean(wl) > 100:
            wl_mu = wl #wavelengths in micrometers
        else:
            wl_mu = wl*1000 #wavelengths in micrometers

        # get y-values in 0-1200 mu range
        idx = np.where(wl_mu < 1000)
        vals = spectrum[idx]
        # get y-values in >2050 mu range
        idx = np.where(wl_mu > 2050)
        vals = np.concatenate((vals,spectrum[idx]))
        # remove nans from vals
        vals = [x for x in vals if not np.isnan(x)]
        # finish if there are no non-nan values
        if len(vals) == 0:
            return [0,1]

        # compute mean and standard deviation
        m = np.mean(vals)
        sd = np.nanstd(vals)
        # compute thresholds
        lower_thresh = m-3*sd
        upper_thresh = m+3*sd

        good_vals = [x for x in spectrum if (x > lower_thresh and x < upper_thresh)]
        ymin = np.min(good_vals)
        ymax = np.max(good_vals)
        return [ymin, ymax]




    def convert_single_image(self):

        if self.data_check['image present'] == False:
            msg = QMessageBox()
            msg.setWindowTitle("Warning")
            msg.setIcon(QMessageBox.Critical)
            msg.setText("An image must be selected first.")
            retval = msg.exec_()
            return

        # get the parameters for conversion
        if self.btn_ref_to_rad.isChecked():
            conversion_type = 'ref_to_rad'
        else:
            conversion_type = 'rad_to_ref'
        solar_zenith_angle = int(self.cb_sza.currentText())
        atmospheric_index = self.cb_atm.currentIndex()
        aerosol_index = self.cb_aerosol.currentIndex()

        # select output filename
        #create default output filename
        # remove .suffix if present and add atm conversion parameters
        fname_suffix = self.atm_parameters_text.replace(':', '') + '-' + conversion_type[7:]
        fname_out_default = os.path.splitext(self.im_input.filename)[0] + fname_suffix

        fname_out = QFileDialog.getSaveFileName(self, "Output Filename", fname_out_default)
        if fname_out == '':
            return

        # do the converstion
        ok, im_arr_output = atmpy.convert_image(self.im_arr_input, self.wl, self.atm_coeff,
                            conversion_type, solar_zenith_angle, atmospheric_index, aerosol_index)
        if ok == False:
            msg = QMessageBox()
            msg.setWindowTitle("Warning")
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Atmospheric conversion failed for unknown reason.")
            retval = msg.exec_()
            return

        # Save the image
        envi.save_image(fname_out + '.hdr', im_arr_output.astype('float32'),
                        metadata=self.im_input.metadata, ext='',
                        force=True)


    def convert_batch_images(self):

        if self.data_check['image present'] == False:
            msg = QMessageBox()
            msg.setWindowTitle("Warning")
            msg.setIcon(QMessageBox.Critical)
            msg.setText("An image must be selected first.")
            retval = msg.exec_()
            return

        # get the parameters for conversion
        if self.btn_ref_to_rad.isChecked():
            conversion_type = 'ref_to_rad'
        else:
            conversion_type = 'rad_to_ref'
        solar_zenith_angle = int(self.cb_sza.currentText())
        atmospheric_index = self.cb_atm.currentIndex()
        aerosol_index = self.cb_aerosol.currentIndex()

        # prepare the default file suffix
        fname_suffix = self.atm_parameters_text.replace(':', '')+'-'+conversion_type[7:]

        # select output filename
        self.batch_process_fname_suffix = fname_suffix
        self.batch_process_subfolder_name = conversion_type
        fname_suffix, subfolderName, ok = BatchFileInfoDialog.getFolderInfo(self)

        # create the subfolder
        input_path = os.path.dirname(self.im_input.filename)
        output_path = os.path.join(input_path, subfolderName)
        # create the output directory if it does not exist
        if not(os.path.isdir(output_path)):
            os.mkdir(output_path)

        # deterimine all files in main folder
        filenames = os.listdir(input_path)

        # loop through all files


        self.statusBar.showMessage('Converting Batch of Images...')
        counter = 0
        counter_max = len(filenames)
        for filename in filenames:
            counter = counter + 1
            self.progressBar.setValue(100*counter/counter_max)
            if not (filename[-4:-1] == '.hd'):
                filename_full = os.path.join(input_path, filename)
                try:
                    # open the image
                    # read image data to variables
                    self.im_input = envi.open(filename_full + '.hdr')
                    self.im_input = self.apply_bbl(self.im_input)

                    self.im_arr_input = self.envi_load(self.im_input)
                    self.wl = np.asarray(self.im_input.bands.centers).flatten()

                    # do the converstion
                    ok, im_arr_output = atmpy.convert_image(self.im_arr_input, self.wl, self.atm_coeff,
                                                            conversion_type, solar_zenith_angle, atmospheric_index,
                                                            aerosol_index)

                    if ok:
                        fname_suffix = self.atm_parameters_text.replace(':', '') + '-' + conversion_type[7:]
                        fname_out_default = os.path.join(output_path,os.path.splitext(filename)[0]+fname_suffix)
                        # Save the image
                        envi.save_image(fname_out_default + '.hdr', im_arr_output.astype('float32'),
                                metadata=self.im_input.metadata, ext='',
                                force=True)
                except:
                    print('File not converted as image: '+filename)

        # reset the progress bar and status message
        self.progressBar.setValue(0)
        self.statusBar.showMessage('')


    def envi_load(self, im):
        # load the image using the envi command from spectralpy
        im_arr = im.load()

        # check for a reflectance scale factor
        # (which is used by ENVI, but is not in the spectralpy routine)
        if 'reflectance scale factor' in im.metadata.keys():
            # apply the reflectance scale factor if it exists and is valid
            try:
                im_arr = im_arr * float(im.metadata['reflectance scale factor'])
            except:
                pass

        # check for a bad bands list
        # (which is used by ENVI, but is not in the spectralpy routine)
        if 'bbl' in im.metadata.keys():
            # apply the bad bands list if it exists and is valid
            try:
                im_arr = im_arr[:, :, np.asarray(im.metadata['bbl']) == 1]
            except:
                pass
        return im_arr

    def is_image_file(self, im_fname):
        try:
            # try to open as ENVI file
            try:
                im = envi.open(im_fname + '.hdr')
                return im_fname, True
            except:
                # sometimes images are saved with ".img" or similar suffix that must be removed from header
                # this will also enable opening an image of the sued selects the header file
                im_fname_nosuffix = im_fname[:im_fname.rfind(".")]
                im = envi.open(im_fname_nosuffix + '.hdr', im_fname)
                return im_fname_nosuffix, True
        except:
            return im_fname, False

    def apply_bbl(self, im):

        if 'bbl' in im.metadata.keys():
            # apply the bad bands list if it exists and is valid
            try:
                im.bands.centers = [im.bands.centers[i] for i in np.where(im.metadata['bbl'])[0]]
                im.nbands = len(im.bands.centers)
                shape = list(im.shape)
                shape[2] = len(im.bands.centers)
                im.shape = tuple(shape)
                if 'band names' in im.metadata.keys():
                    try:
                        im.metadata['band names'] = [im.metadata['band names'][i] for i in
                                                     np.where(im.metadata['bbl'])[0]]
                    except:
                        print('Applying bad bands list to band names failed.')
            except:
                pass
        return im


if __name__ == '__main__':
    app = QApplication(sys.argv)
    #app = QApplication.instance() # when running in Canopy
    win = atmosphericConversionGUI()
    win.show()
    app.exec_()