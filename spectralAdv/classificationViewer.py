from .specTools import *
from os import listdir
from os import remove
from os import path
from os.path import join
from sys import argv
from sys import exit
import csv
import shapefile
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from . import classificationResultsViewer
from . import classification
from . import specTools


class progressBar(QDialog):
    def __init__(self, title=None, text=None, parent=None):
        super(progressBar, self).__init__(parent)
        self.setGeometry(150, 150, 200, 100)
        self.setWindowTitle(title)
        # add label and progress bar
        self.text = QLabel()
        self.text.setText(text)
        self.progress = QProgressBar(self)
        # set the layout
        vbox = QVBoxLayout()
        vbox.addWidget(self.text)
        vbox.addWidget(self.progress)
        self.setLayout(vbox)
        #show it
        self.show()



class classAnalysisGUI(QMainWindow):
    def __init__(self, settings=None, imageDir=None, parent=None):
        super(classAnalysisGUI, self).__init__(parent)
        self.setWindowTitle("Class Analysis")
        self.setWindowIcon(QIcon('files_icon.ico'))
        self.setGeometry(150, 150, 500, 800)
        self.settings = settings
        self.imageDir = imageDir
        self.ROIdata = {}
        self.wl = []
        self.learners = {}
        self.validation = {}

        quitAction = QAction("Quit",self)
        quitAction.setShortcut("Ctrl+Q")
        quitAction.triggered.connect(self.cancel)
        openASCIIROIAction = QAction("Open ROI ASCII file",self)
        openASCIIROIAction.setShortcut("Ctrl+O")
        openASCIIROIAction.triggered.connect(self.choose_ROI_file)
        openWavelnengthAction = QAction("Open Image file with Wavelengths",self)
        openWavelnengthAction.triggered.connect(self.choose_WL_file)

        plotSelectedMeansAction = QAction("Plot Selected Class Means",self)
        plotSelectedMeansAction.triggered.connect(self.plot_selected_means)
        plotMeansAction = QAction("Plot All Class Means",self)
        plotMeansAction.triggered.connect(self.plot_all_means)

        classifyImageAction = QAction("Apply Classifier to an Image",self)
        classifyImageAction.triggered.connect(self.classify_image)

        # GUI Widgets
        self.ROIfileText = QLabel()
        self.ROIfileText.setText("No ROI file selected")
        self.IamgefileText = QLabel()
        self.IamgefileText.setText("No Image file selected")

        # list widget with table of ROIs
        self.table_view = QTableWidget()
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setRowCount(0)
        self.table_view.setColumnCount(4)
        self.table_view.setHorizontalHeaderLabels(['Name','Color','Num Points'])
        self.table_view.setColumnWidth(0, 325) # name
        self.table_view.setColumnWidth(1, 75) # color
        self.table_view.setColumnWidth(2, 75) # num pts
        self.table_view.setColumnWidth(3, 75) # ROI data
        self.table_view.setColumnHidden(3, True)
        self.table_view.horizontalHeader().setStretchLastSection(True) # stretch last column
        self.table_view.verticalHeader().setAlternatingRowColors(True)

        # add a horizontal seperator line
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)

        self.SelectAllMethodsCheckBox = QCheckBox('Select All Methods and Plots', self)
        self.SelectAllMethodsCheckBox.stateChanged.connect(self.SelectAllMethodsCheckBoxChanged)

        # add a horizontal seperator line
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)

        self.ClassMethodsSectionText = QLabel()
        self.ClassMethodsSectionText.setText("Select Calssification Methods:")
        self.LDAclassificationCheckBox = QCheckBox('Linear Discriminant Analysis', self)
        self.QDAclassificationCheckBox = QCheckBox('Quadratic Discriminant Analysis', self)
        self.RFclassificationCheckBox = QCheckBox('Random Forest', self)
        self.DTclassificationCheckBox = QCheckBox('Decision Tree', self)

        self.ScatterplotMethodsSectionText = QLabel()
        self.ScatterplotMethodsSectionText.setText("Select Scatterplot Methods:")
        self.ScatterplotPCACheckBox = QCheckBox('PCA Dimension Reduction Scatterplot', self)
        self.ScatterplotLDACheckBox = QCheckBox('LDA Dimension Reduction Scatterplot', self)

        # add a horizontal seperator line
        line3 = QFrame()
        line3.setFrameShape(QFrame.HLine)
        line3.setFrameShadow(QFrame.Sunken)

        # OK and Cancel buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.buttons.accepted.connect(self.full_analysis)
        self.buttons.rejected.connect(self.cancel)

        # Layout
        self.widget_central = QWidget()
        self.vbox = QVBoxLayout()
        self.widget_central.setLayout(self.vbox)
        self.vbox.addWidget(self.ROIfileText)
        self.vbox.addWidget(self.IamgefileText)
        self.vbox.addWidget(self.table_view)

        self.vbox.addSpacing(5)
        self.vbox.addWidget(self.SelectAllMethodsCheckBox)
        self.vbox.addSpacing(5)
        self.vbox.addWidget(line1)
        self.vbox.addWidget(self.ClassMethodsSectionText)
        self.vbox.addWidget(self.LDAclassificationCheckBox)
        self.vbox.addWidget(self.QDAclassificationCheckBox)
        self.vbox.addWidget(self.RFclassificationCheckBox)
        self.vbox.addWidget(self.DTclassificationCheckBox)

        self.vbox.addSpacing(10)
        self.vbox.addWidget(line2)
        self.vbox.addWidget(self.ScatterplotMethodsSectionText)
        self.vbox.addWidget(self.ScatterplotPCACheckBox)
        self.vbox.addWidget(self.ScatterplotLDACheckBox)

        self.vbox.addSpacing(10)
        self.vbox.addWidget(line3)
        self.vbox.addWidget(self.buttons)

        # set as central widget and dock widget
        self.setCentralWidget(self.widget_central)

        # Add Menubar
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu("&File ")
        fileMenu.addAction(openASCIIROIAction)
        fileMenu.addAction(openWavelnengthAction)
        fileMenu.addAction(quitAction)
        fileMenu = mainMenu.addMenu("&Plots ")
        fileMenu.addAction(plotSelectedMeansAction)
        fileMenu.addAction(plotMeansAction)
        fileMenu = mainMenu.addMenu("&Classify Image ")
        fileMenu.addAction(classifyImageAction)

    def not_supportrd(self):
        QMessageBox.information(self, "Not Supported","That functionality is not yet supported.")

    def select_ROIs_message(self):
        QMessageBox.information(self, "No ROIs Selected","At least two ROIs must be selected.\n  To Select all ROIs use the top-left box in the table.")

    def cancel(self):
        sys.exit()

    def plot_selected_means(self):
        # determine the eselected ROIs
        SelectedROIdata = {}
        selected_rows = sorted(set(index.row() for index in
                          self.table_view.selectedIndexes()))
        # return if not rows are selected
        if len(selected_rows) < 1:
            return
        # plot the class means
        fig, ax = plt.subplots()

        for rowIdx in selected_rows:
            key = self.table_view.item(rowIdx,3).text()
            spectra = self.ROIdata[key].spectra
            mean = np.mean(spectra,0)
            if len(self.wl) == len(mean):
                wl = self.wl
            else:
                print('Number Band Mismatch: ('+self.ROIdata[key].name+')')
                print('Number ROI Bands: '+str(len(mean)))
                print('Number Image Bands: '+str(len(self.wl)))
                wl = range(len(mean))
            ax.plot(wl, mean, label=self.ROIdata[key].name, color=self.ROIdata[key].color/255.)

            ax.set(xlabel='Wavelength',  title='Class Means')
        ax.legend()
        plt.show()

    def set_loading_progressbar(self, title, text):
        self.progressDialog = QProgressDialog(self)
        self.progressDialog.setMinimum(0)
        self.progressDialog.setLabelText(text)
        self.progressDialog.setMaximum(100)
        self.progressDialog.setWindowTitle(title)
        #self.dialog.setCancelButton(None)
        self.progressDialog.setModal(True)
        self.progressDialog.show()

    def set_loading_progressbar2(self, title, text):
        self.progressDialog = QProgressDialog("Operation in progress.", "Cancel", 0, 100)

    def plot_all_means(self):

        # plot the class means
        fig, ax = plt.subplots()
        for rowIdx in range(self.table_view.rowCount()):
            key = self.table_view.item(rowIdx,3).text()
            spectra = self.ROIdata[key].spectra
            mean = np.mean(spectra,0)
            if len(self.wl) == len(mean):
                wl = self.wl
            else:
                print('Number Band Mismatch: ')
                print('Number ROI Bands: '+str(len(mean)))
                print('Number Image Bands: '+str(len(self.wl)))
                wl = range(len(mean))
            ax.plot(wl, mean, label=self.ROIdata[key].name, color=self.ROIdata[key].color/255.)

            ax.set(xlabel='Wavelength',  title='Class Means')
        ax.legend()
        plt.show()

    def SelectAllMethodsCheckBoxChanged(self):
        if self.SelectAllMethodsCheckBox.isChecked():
            self.LDAclassificationCheckBox.setChecked(True)
            self.QDAclassificationCheckBox.setChecked(True)
            self.RFclassificationCheckBox.setChecked(True)
            self.DTclassificationCheckBox.setChecked(True)
            self.ScatterplotPCACheckBox.setChecked(True)
            self.ScatterplotLDACheckBox.setChecked(True)
        else:
            self.LDAclassificationCheckBox.setChecked(False)
            self.QDAclassificationCheckBox.setChecked(False)
            self.RFclassificationCheckBox.setChecked(False)
            self.DTclassificationCheckBox.setChecked(False)
            self.ScatterplotPCACheckBox.setChecked(False)
            self.ScatterplotLDACheckBox.setChecked(False)

    class ColorDelegate(QStyledItemDelegate):
        def paint(self, painter, option, index):
            color = index.data(Qt.UserRole)
            option.palette.setColor(QPalette.Highlight, color)
            QStyledItemDelegate.paint(self, painter, option, index)

    def choose_ROI_file(self):
        fname_ROI = QFileDialog.getOpenFileName(self, 'Choose ROI ASCII file.',
            'C:\\Users\\wfbsm\\OneDrive\\Documents\\My Papers\\Microscene\\Material Seperation\data', "Text files (*.txt)")
        if fname_ROI == '':
            return

        # read the ROI data from the file
        ok, self.ROIdata = read_roi_file(fname_ROI)
        if not ok:
            return

        # ROI data was read, so set the file name in the GUI
        self.ROIfileText.setText('ROI File: '+fname_ROI)

        # determine the keys
        keys = self.ROIdata.keys()
        # set the number of rows to be number of ROIs
        self.table_view.setRowCount(len(keys))
        # fill in the data
        for idx, key in enumerate(keys):
            # name item
            name = QTableWidgetItem(self.ROIdata[key].name)
            name.setData(Qt.UserRole,QColor(100,130,155))  # sets the highlight color
            self.table_view.setItem(idx, 0, name)
            # color item
            c = self.ROIdata[key].color
            blank = QTableWidgetItem()
            blank.setFlags(blank.flags() & ~Qt.ItemIsEditable)
            blank.setBackground(QColor(c[0], c[1], c[2]))
            blank.setData(Qt.UserRole,QColor(c[0], c[1], c[2]))  # sets the highlight color
            self.table_view.setItem(idx, 1,blank )
            # number of points item
            npts = QTableWidgetItem(str(self.ROIdata[key].npts))
            npts.setFlags(npts.flags() & ~Qt.ItemIsEditable)
            npts.setData(Qt.UserRole,QColor(100,130,155))   # sets the highlight color
            self.table_view.setItem(idx, 2, npts)
            # store the key for this ROI in the last item
            ROIkey = QTableWidgetItem(key)
            self.table_view.setItem(idx, 3, ROIkey)
        self.table_view.setItemDelegate(self.ColorDelegate()) # sets the background colors when slected

    def choose_WL_file(self):
        fname_WL = QFileDialog.getOpenFileName(self, 'Choose Image file with wavelengths.')
        if fname_WL == '':
            return

        try:
            im = envi.open(fname_WL+'.hdr')
        except:
            # sometimes images are saved with ".img" or similar suffix that must be removed from header
            im_fname_nosuffix = fname_WL[:fname_WL.rfind(".")]
            self.im = envi.open(im_fname_nosuffix+'.hdr', fname_WL)
        self.ROIfileText.setText('Image wl File: '+fname_WL)
        self.wl = self.im.bands.centers

    def full_analysis(self):

        # determine the eselected ROIs
        SelectedROIdata = {}
        selected_rows = sorted(set(index.row() for index in
                          self.table_view.selectedIndexes()))
        # return if not rows are selected
        if len(selected_rows) < 2:
            self.select_ROIs_message()
            return
        # build the ROI data for the selected rows
        for rowIdx in selected_rows:
            key = self.table_view.item(rowIdx,3).text()
            name = self.table_view.item(rowIdx,0).text()
            SelectedROIdata[name] = self.ROIdata[key]
            SelectedROIdata[name].name = name

        # determine which classification methods the user has selected
        methods = []
        if self.LDAclassificationCheckBox.isChecked():
            methods.append('LDA')
        if self.QDAclassificationCheckBox.isChecked():
            methods.append('QDA')
        if self.RFclassificationCheckBox.isChecked():
            methods.append('RF')
        # Compute the classificaiton analysis
        self.learners, self.validation = classification.ROI_class_learner(SelectedROIdata, self.wl, methods)

        # determine which plot methods the user has selected
        methods = []
        if self.ScatterplotPCACheckBox.isChecked():
            methods.append('PCA')
        if self.ScatterplotLDACheckBox.isChecked():
            methods.append('LDA')
        # create the requested plots
        self.plot_data = classification.dimension_reduction_plots(SelectedROIdata, methods)

        self.classificationResultsViewer = classificationResultsViewer.classificationResultsViewer(settings=self.settings,
                                                                                                   methods=methods,
                                                                                                   learners=self.learners,
                                                                                                   validation=self.validation,
                                                                                                   plot_data=self.plot_data)

    def classify_image(self):

        # Select the image
        prompt = 'Select an image'
        if self.imageDir is None:
            self.im_fname = QFileDialog.getOpenFileName(self, prompt)
        else:
            try:
                self.im_fname = QFileDialog.getOpenFileName(self, prompt, self.imageDir)
            except:
                self.im_fname = QFileDialog.getOpenFileName(self, prompt)
        if self.im_fname == '':
            return
        dummy,ok = specTools.is_image_file(self.im_fname)
        if not ok:
            QMessageBox.warning(self,"File is not valid ENVI image",
                "File Name: %s"%(os.path.basename(self.im_fname)))
            return
        self.imageDir = os.path.dirname(os.path.abspath(self.im_fname))

        # load the image
        try:
            # this will work if the filename has no suffix
            im_fname_nosuffix = self.im_fname
            self.im = envi.open(self.im_fname+'.hdr')
        except:
            # this will work if the filename has a suffix
            im_fname_nosuffix = self.im_fname[:self.im_fname.rfind(".")]
            self.im = envi.open(im_fname_nosuffix+'.hdr', self.im_fname)
        self.im_arr = specTools.envi_load(self.im)
        [nRows,nCols,nBands] = np.shape(self.im_arr)

        # check the bands
        band_check = True
        if nBands == len(self.wl):
            if not (self.im.bands.centers == self.wl):
                band_check = False
        else:
            band_check = False
        if band_check == False:
            QMessageBox.warning(self, "Band Mismatch","Image bands must match ROI spectra bands.")
            return

        class_results, prob_results = classification.image_calssification(self.im_arr, self.learners)

        # save the classification results
        for learnerMethod in self.learners.keys():
            envi.save_classification(
                im_fname_nosuffix+'_class_'+learnerMethod+'.hdr',
                class_results[learnerMethod],
                class_names = self.ROIdata.keys(),
                class_colors = [self.ROIdata[key].color for key in self.ROIdata.keys()], force=True)
            try:
                envi.save_image(im_fname_nosuffix+'_probability_'+learnerMethod+'.hdr',
                                prob_results[learnerMethod],
                                metadata={'band names': self.ROIdata.keys(), 'default stretch': '0.500000 1.000000 linear'},
                                ext='', force=True)
            except:
                pass


if __name__ == "__main__":
    app = QApplication(argv)
    form = classAnalysisGUI()
    form.show()
    app.exec_()