import operator
import os
import sys
import pickle
import numpy as np
from . import specTools
from fuzzywuzzy import process
from fuzzywuzzy import fuzz
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
#from pyqtgraph.widgets.MatplotlibWidget import *
import timeit
from pyqtgraph.widgets.MatplotlibWidget import *



class TableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        return float(self.text()) < float(other.text())

class compareImages(QMainWindow):
    def __init__(self, settings=None, scores=[], header_labels=[], parent=None):
        super(compareImages, self).__init__(parent=None)
        self.setWindowTitle("Compare Image Scores")
        self.setGeometry(150, 150, 900, 400)

        # list widget with list of images
        self.listWidget = QListWidget()
        self.listWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.plot_data = {}
        for i in range(1,len(header_labels)):
            if i <= (len(header_labels)-1)/2:
                name = 'Std: '+header_labels[i].replace("\n", "")
            else:
                name = 'ACE: '+header_labels[i].replace("\n", "")
            self.listWidget.addItem(name)
            self.plot_data[name] = scores[:,i-1]

        # plot widget
        self.MPWidget = MatplotlibWidgetBottomToolbar()
        self.subplot = self.MPWidget.getFigure().add_subplot(111)
        self.subplot.set_xlabel('Spectrum Number')
        self.MPWidget.draw()
        self.plot = QDockWidget("", self)
        self.plot.setWidget(self.MPWidget)
        self.plot.setFloating(False)

        # set the layout for the central widget
        self.widget_central=QWidget()
        self.vbox = QVBoxLayout()
        self.widget_central.setLayout(self.vbox)
        self.vbox.addWidget(self.listWidget)

        # set as central widget and dock widget
        self.setCentralWidget(self.widget_central)
        self.addDockWidget(Qt.RightDockWidgetArea, self.plot)

        self.listWidget.itemClicked.connect(self.Clicked)

        self.show

    def Clicked(self,item):
        self.subplot.axes.clear()
        for item in self.listWidget.selectedItems():
            self.subplot.plot(self.plot_data[item.text()], label=item.text(),
                linewidth=1, alpha=0.5)
        self.subplot.axes.legend()
        self.MPWidget.draw()


class acePlot(QMainWindow):
    def __init__(self, parent=None, x=None, y=None, label=None):
        super(acePlot, self).__init__(parent)
        self.setWindowTitle("Spectral Plot")
        self.setGeometry(250, 150, 900, 600)

        # menu bar
        saveLibraryAction = QAction("Save Library",self)
        saveLibraryAction.triggered.connect(self.not_supportrd)
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu("&File ")
        fileMenu.addAction(saveLibraryAction)

        self.MPWidget = MatplotlibWidgetBottomToolbar()
        self.subplot = self.MPWidget.getFigure().add_subplot(111)
        self.subplot.plot(x,y,label=label)
        self.subplot.set_xlabel('Abundance')
        self.subplot.set_ylabel('ACE Score')
        self.MPWidget.draw()

        self.label = QLabel('Available Spectra:')
        self.cb_spectral = QComboBox()

        self.widget_central=QWidget()
        self.vbox = QVBoxLayout()
        self.widget_central.setLayout(self.vbox)
        self.vbox.addWidget(self.MPWidget)
        #self.vbox.addWidget(self.label)
        #self.vbox.addWidget(self.cb_spectral)

        # set as central widget
        self.setCentralWidget(self.widget_central)
        self.show()

    def not_supportrd(self):
        QMessageBox.information(self, "Not Supported","That functionality is not yet supported.")

         
                
class MyWindow(QMainWindow):
    def __init__(self, settings=None, data_list=[], header_labels=[], sc_image_plot_data=None,
            imageDir = None, libraryDir = None, outputDir = None, sc_library_plot_data=None, *args):
        #QWidget.__init__(self, *args)
        super(MyWindow, self).__init__()
        self.setGeometry(50, 50, 1500, 850) #(x_pos, y_pos, width, height)
        self.setWindowTitle("Spectral Contrast Analysis")
        # attach the plot data
        self.imageDir = imageDir
        self.libraryDir = libraryDir
        self.outputDir = outputDir
        self.data_list = data_list
        self.header_labels = header_labels
        self.sc_image_plot_data = sc_image_plot_data
        self.sc_library_plot_data = sc_library_plot_data
        
        # menu bar actions
        # File menu
        openNewDataAction = QAction("Open New Data",self)
        openNewDataAction.triggered.connect(self.spectral_contrast_analysis)
        openDataAction = QAction("Open Contrast File",self)
        openDataAction.triggered.connect(self.open_contrast_file) 
        saveDataAction = QAction("Save as Contrast File",self)
        saveDataAction.triggered.connect(self.save_contrast_file) 
        saveCSVAction = QAction("Save as CSV",self)
        saveCSVAction.triggered.connect(self.not_supported) 
        exitAction = QAction("Close",self)
        exitAction.triggered.connect(self.close_this) 
        # Settings menu
        tableSettingsAction = QAction("Table Display Settings",self)
        tableSettingsAction.triggered.connect(self.not_supported)       
        toggleUnitsScoresAction = QAction("Toggle ACE/StDev units",self)
        toggleUnitsScoresAction.triggered.connect(self.toggle_data_units)
        toggleUnitsScoresAction.setShortcut('Ctrl+U')
        # Analysis menu
        sortNameMatchingAction = QAction("Sort by name matching",self)
        sortNameMatchingAction.triggered.connect(self.sort_name_matches)
        compareImageScoresAction = QAction("Compare Image Scores",self)
        compareImageScoresAction.triggered.connect(self.compare_image_scores)         
        plotACEstdScoresScoresAction = QAction("Show ACE-vs-Abundace Plots",self)
        plotACEstdScoresScoresAction.triggered.connect(self.plot_ACE_vs_abuncance)  
        
        # add the menu bar   
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu("&File ")
        fileMenu.addAction(openNewDataAction)
        fileMenu.addAction(openDataAction)
        fileMenu.addAction(saveDataAction)
        #fileMenu.addAction(saveCSVAction)
        fileMenu.addAction(exitAction)
        settingsMenu = mainMenu.addMenu("&Settings ")
        settingsMenu.addAction(tableSettingsAction)
        settingsMenu.addAction(toggleUnitsScoresAction)
        analysisMenu = mainMenu.addMenu("&Analysis ")
        analysisMenu.addAction(sortNameMatchingAction)
        analysisMenu.addAction(compareImageScoresAction)
        analysisMenu.addAction(plotACEstdScoresScoresAction)
        
        # create the table widget
        self.table_view = QTableWidget()
        
        # create the spectral plot widget
        try:
            self.MPWidget = MatplotlibWidgetBottomToolbar()
        except:
            self.MPWidget = MatplotlibWidget()
        self.subplot = self.MPWidget.getFigure().add_subplot(111) 
        self.subplot.set_xlabel('Wavelength') 
        self.MPWidget.draw()   		
        self.plot = QDockWidget("", self)
        self.plot.setWidget(self.MPWidget)
        self.plot.setFloating(False) 
        
        # set the layout for the central widget
        self.widget_central=QWidget()
        self.vbox = QVBoxLayout()
        self.widget_central.setLayout(self.vbox)
        self.vbox.addWidget(self.table_view)
        
        # set as central widget and dock widget
        self.setCentralWidget(self.widget_central)
        self.addDockWidget(Qt.TopDockWidgetArea, self.plot)

        # Add stausbar with progressBar
        self.myStatusBar = QStatusBar()
        self.myStatusBar.showMessage('Ready')
        self.progressBar = QProgressBar()
        self.myStatusBar.addPermanentWidget(self.progressBar)
        self.progressBar.setValue(0)
        self.setStatusBar(self.myStatusBar)

        self.setup_table()
        self.show()       
    
    def setup_table(self):
        nCols = len(self.header_labels)
        nRows = len(self.data_list)
        self.table_view.verticalHeader().setDefaultSectionSize(18)
        self.table_view.setRowCount(nRows)
        self.table_view.setColumnCount(nCols)
        self.table_view.setColumnWidth(1, 900)
        self.table_view.setHorizontalHeaderLabels(self.header_labels)
        self.table_view.verticalHeader().hide()
        # set font
        #font = QFont("Courier New", 12)
        #table_view.setFont(font)
        # set column width to fit contents (set font first!)
        # self.table_view.resizeColumnsToContents()
        if len(self.header_labels) < 8:
            header = self.table_view.horizontalHeader()
            header.ResizeMode(0, QHeaderView.Stretch)
            header.ResizeMode(0, QHeaderView.Interactive)
            for i in range(1,len(self.header_labels)):
                header.ResizeMode(i, QHeaderView.ResizeToContents)
            self.table_view.setColumnWidth(0, 800)
            self.table_view.wordWrap()
        else:
            header = self.table_view.horizontalHeader()
            header.ResizeMode(0, QHeaderView.Interactive)
            for i in range(1,len(self.header_labels)):
                header.ResizeMode(i, QHeaderView.ResizeToContents)
            self.table_view.setColumnWidth(0, 800)
            self.table_view.wordWrap()
        # enable sorting
        self.table_view.setSortingEnabled(True)
        # add the data
        self.add_data()
        
        # signal for selection changed
        self.table_view.itemSelectionChanged.connect(self.selection_changed)
        self.table_view.cellClicked.connect(self.cell_was_clicked)

    def sort_name_matches(self):
        query, ok = QInputDialog.getText(self, "Enter words to search for", "Query words:", QLineEdit.Normal, "")
        if not ok:
            return
        # determine the new order of spectra names
        #self.myStatusBar.showMessage('Sorting spectra by text search...')
        #start_time = timeit.default_timer()
        #sorted_snames = process.extract(query, self.spectra_names, scorer=fuzz.ratio, limit=len(self.spectra_names))
        #print('scorer=fuzz.ratio, elapsed time: '+str(timeit.default_timer()-start_time))
        #start_time = timeit.default_timer()
        #sorted_snames = process.extract(query, self.spectra_names, scorer=fuzz.partial_ratio, limit=len(self.spectra_names))
        #print('scorer=fuzz.partial_ratio, elapsed time: '+str(timeit.default_timer()-start_time))
        #start_time = timeit.default_timer()
        #sorted_snames = process.extract(query, self.spectra_names, scorer=fuzz.token_sort_ratio, limit=len(self.spectra_names))
        #print('scorer=fuzz.token_sort_ratio, elapsed time: '+str(timeit.default_timer()-start_time))
        #start_time = timeit.default_timer()
        sorted_snames = process.extract(query, self.spectra_names, scorer=fuzz.token_set_ratio, limit=len(self.spectra_names))
        #print('scorer=fuzz.token_set_ratio, elapsed time: '+str(timeit.default_timer()-start_time))
        #re-order the data list
        self.myStatusBar.showMessage('Updating table data...')
        new_data_list = []
        for sname in sorted_snames:
            row = []
            row.append(sname[0])
            for val in self.data_dict[sname[0]]:
                row.append(val)
            new_data_list.append(row)
        self.data_list = new_data_list
        self.table_view.clear()
        self.table_view.setRowCount(0)
        self.table_view.setColumnCount(0)
        self.setup_table()
        self.myStatusBar.showMessage('Ready')

    def not_supported(self):
        QMessageBox.information(self, "Not Supported","That functionality is not yet supported.")
    
    def plot_ACE_vs_abuncance(self):   
        # get the selected indices   
        selected_indices = self.table_view.selectedIndexes()
        # get the row and column
        row = selected_indices[0].row()
        column = selected_indices[0].column() 
        # get the name of the spectrum and image
        selected_spectrum_text = self.table_view.item(row, 0).text()
        selected_image_header_text = self.header_labels[column]
        selected_image_text = selected_image_header_text.split('\n')[0]
        label_name = str(selected_image_text+', '+selected_spectrum_text[0:100])
        # get the x and y data for this plot
        x = self.ace_predicted_plot_data.abundances
        y = self.ace_predicted_plot_data.dict[selected_image_text,selected_spectrum_text]
        # create the plot        
        if not hasattr(self, 'ace_plot'):
            # This is the case if not spectral plot has been made
            self.ace_plot = acePlot(parent=self, x=x, y=y, label=label_name)
        elif self.ace_plot.isHidden():
            # This is the case if a spectral plot was made and then closed
            self.ace_plot = acePlot(parent=self, x=x, y=y, label=label_name)
        else:
            # This is the case if a spectral plot is made and still open
            # generate the plot
            self.ace_plot.subplot.plot(x, y, label=label_name)    
            self.ace_plot.MPWidget.draw()
        if len(selected_indices) > 1:
            selected_indices.pop(0)
            for idx in selected_indices:
                row = idx.row()
                column = idx.column() 
                # get the name of the spectrum and image
                selected_spectrum_text = self.table_view.item(row, 0).text()
                selected_image_header_text = self.header_labels[column]
                selected_image_text = selected_image_header_text.split('\n')[0]
                label_name = selected_image_text+', '+selected_spectrum_text[0:100]
                # get the x and y data for this plot
                x = self.ace_predicted_plot_data.abundances
                y = self.ace_predicted_plot_data.dict[selected_image_text,selected_spectrum_text]
                self.ace_plot.subplot.plot(x, y, label=label_name)     
                self.ace_plot.MPWidget.draw()
        self.ace_plot.subplot.axes.legend()
        self.ace_plot.MPWidget.draw()
        
    def compare_image_scores(self):
        nRows = len(self.data_list)
        nCols = len(self.header_labels)-1
        scores = np.zeros([nRows,nCols])
        for r in range(nRows):
            for c in range(nCols):
                scores[r,c] = float(self.table_view.item(r,c+1).text())
        
        self.cp = compareImages(settings=self.settings, scores=scores, header_labels=self.header_labels)
        self.cp.show()
    
    def close_this(self): 
        self.close()
            
    def save_contrast_file(self):
        fname,ok = QFileDialog.getSaveFileName(self, 'Save File', '', 'Spectral Contrast (*.sc)')
        if not ok:
            return
        self.myStatusBar.showMessage('Saving File')
        # create a disctionary will all the needed data
        data = {'data_list':self.data_list,
                'data_list_ACE_units': self.data_list_ACE_units,
                'ace_predicted_plot_data':self.ace_predicted_plot_data,
                'header_labels':self.header_labels,
                'sc_image_plot_data':self.sc_image_plot_data,
                'sc_library_plot_data':self.sc_library_plot_data}        
        # Write to file
        f_myfile = open(fname, 'wb')
        pickle.dump(data, f_myfile)
        f_myfile.close()
        self.myStatusBar.showMessage('Ready')
    
    def open_contrast_file(self):
        fname,ok = QFileDialog.getOpenFileName(self, 'Open File', '', 'Spectral Contrast (*.sc)')
        if not ok:
            return
        self.myStatusBar.showMessage('Opening File...')
        f_myfile = open(fname, 'rb')
        data = pickle.load(f_myfile)  # variables come out in the order you put them in
        f_myfile.close()
        # put data into variables
        self.data_list = data['data_list']
        self.data_list_ACE_units = data['data_list_ACE_units']
        self.ace_predicted_plot_data = data['ace_predicted_plot_data']
        self.header_labels = data['header_labels']
        self.sc_image_plot_data = data['sc_image_plot_data']
        self.sc_library_plot_data = data['sc_library_plot_data']
        self.myStatusBar.showMessage('Preparing table...')
        # setup the table with the new data
        self.setup_table()
        self.myStatusBar.showMessage('Ready')
        
    def spectral_contrast_analysis(self):
        # Get files from user
        fname_images,ok = self.select_images()
        fname_library,ok = self.select_library()
        # Setup input class
        inputs = specTools.inputs_struc() # set the optional parameters
        inputs.contrast = 1 # set this to 1 to compute constrast
        inputs.im_fnames = fname_images#['C:\\Users\\wfbsm\\Desktop\\specTools Tools\\images\\Mixed_Vegetation_Soil_AF','C:\\Users\\wfbsm\\Desktop\\specTools Tools\\images\\Bare_Soil_AF','C:\\Users\\wfbsm\\Desktop\\specTools Tools\\images\\Urban_AF']
        inputs.det_lib_fname = fname_library#'C:\\Users\\wfbsm\\Desktop\\specTools Tools\\libraries\\lib_detect_fullresolution
        inputs.verbose = 1
        inputs.abundances = range(101)
        inputs.sample_size = 4000
        # Call the spectral contrast function
        sc_list = specTools.compute_sc_library_analysis(inputs)
        #prepare the images
        images = specTools.open_read_images(inputs.im_fnames,inputs.verbose) 
        # convert results to a list for the viewer
        header_labels, data_list, data_list_ACE_units = specTools.make_sc_list_dictionary(sc_list,images,inputs)
        sc_image_plot_data, sc_library_plot_data, ace_predicted_plot_data = specTools.package_spectral_contrast_plot_data(
            sc_list, images, header_labels, inputs)
        # attach the plot data
        self.data_list = data_list
        self.data_list_ACE_units = data_list_ACE_units
        self.header_labels = header_labels
        self.sc_image_plot_data = sc_image_plot_data
        self.sc_library_plot_data = sc_library_plot_data
        self.ace_predicted_plot_data = ace_predicted_plot_data
        # add the data
        self.setup_table()
        
    def selection_changed(self):
        indices = self.table_view.selectedIndexes()
        row = indices[0].row()
        column = indices[0].column()  
        self.subplot.axes.clear()  
        selected_spectrum_text = self.table_view.item(row, 0).text()
        spectrum_wl = self.sc_library_plot_data.wl
        spectrum = self.sc_library_plot_data.dict[selected_spectrum_text]    
        if column > 0:  
            selected_header_text = self.table_view.horizontalHeaderItem(column).text()
            image_wl = self.sc_image_plot_data[selected_header_text]['wl']
            image_mean = self.sc_image_plot_data[selected_header_text]['mean']   
            image_endmembers = self.sc_image_plot_data[selected_header_text]['endmembers']            
            self.subplot.plot(image_wl,image_mean,'k', lw=1) 
            # rescale the spectrum to match the image mean
            spectrum = spectrum - np.mean(spectrum)
            spectrum = spectrum/np.std(spectrum)
            spectrum = spectrum*np.std(image_mean)
            spectrum = spectrum + np.mean(image_mean) 
            nEndmembers,nBands = image_endmembers.shape
            for i in range(max([5,nEndmembers])):
                em = image_endmembers[i,:]
                em = em - np.mean(em)
                em = em/np.std(em)
                em = em*np.std(image_mean)
                em = em + np.mean(image_mean) 
                self.subplot.plot(image_wl,em,'k', lw=0.1)     
            self.subplot.set_ylim(min([min(image_mean),min(spectrum)]),max([max(image_mean),max(spectrum)]))  
        else:           
            self.subplot.set_ylim(min(spectrum),max(spectrum)) 
        self.subplot.plot(spectrum_wl,spectrum,'r', lw=1) 
        self.subplot.set_xlabel('Wavelength') 
        self.MPWidget.draw()        
        
    def cell_was_clicked(self, row, column):
        self.subplot.axes.clear()  
        selected_spectrum_text = self.table_view.item(row, 0).text()
        spectrum_wl = self.sc_library_plot_data.wl
        spectrum = self.sc_library_plot_data.dict[selected_spectrum_text]    
        if column > 0:  
            selected_header_text = self.table_view.horizontalHeaderItem(column).text()
            image_wl = self.sc_image_plot_data[selected_header_text]['wl']
            image_mean = self.sc_image_plot_data[selected_header_text]['mean'] 
            image_endmembers = self.sc_image_plot_data[selected_header_text]['endmembers']            
            self.subplot.plot(image_wl,image_mean,'k', lw=1) 
            # rescale the spectrum to match the image mean
            spectrum = spectrum - np.mean(spectrum)
            spectrum = spectrum/np.std(spectrum)
            spectrum = spectrum*np.std(image_mean)
            spectrum = spectrum + np.mean(image_mean) 
            nEndmembers,nBands = image_endmembers.shape
            for i in range(max([5,nEndmembers])):
                em = image_endmembers[i,:]
                em = em - np.mean(em)
                em = em/np.std(em)
                em = em*np.std(image_mean)
                em = em + np.mean(image_mean) 
                self.subplot.plot(image_wl,em,'k', lw=0.1)       
            self.subplot.set_ylim(min([min(image_mean),min(spectrum)]),max([max(image_mean),max(spectrum)]))  
        else:           
            self.subplot.set_ylim(min(spectrum),max(spectrum))              
        self.subplot.plot(spectrum_wl,spectrum,'r', lw=1)  
        self.subplot.set_xlabel('Wavelength') 
        self.MPWidget.draw()  
            
    def add_data(self):
        self.table_units = 'stdev'
        self.spectra_names = []
        self.data_dict = {}

        self.table_view.setUpdatesEnabled(False)
        r = 0
        nrows = len(self.data_list)
        num_data_columns = (len(self.header_labels)-1)/2
        for row_text in self.data_list:
            c = 0
            self.data_dict[row_text[0]] = row_text[1:len(row_text)]
            for item_text in row_text:
                if c == 0:
                    # use QTableWidgetItem for first column, which is text
                    self.table_view.setItem(r,c, QTableWidgetItem(item_text))
                    self.spectra_names.append(item_text)
                else:
                    # use custom TableWidgetItem for numerical columns
                    self.table_view.setItem(r,c, TableWidgetItem(item_text))
                c = c+1
            r = r+1
            if (r % 100) == 0:
                self.progressBar.setValue(100*r/nrows)
        self.table_view.setUpdatesEnabled(True)
        self.progressBar.setValue(0)
        self.toggle_data_units()

    def toggle_data_units(self):
        num_data_columns =  int((len(self.header_labels)-1)/2)
        if num_data_columns == 0:
            return

        if self.table_units == 'ace':
            self.table_units = 'stdev'
            for i in range(1,(num_data_columns+1)):
                self.table_view.setColumnHidden(i, False)
            for i in range((num_data_columns+1),(2*num_data_columns+1)):
                self.table_view.setColumnHidden(i, True)
        else:
            self.table_units = 'ace'
            for i in range(1,(num_data_columns+1)):
                self.table_view.setColumnHidden(i, True)
            for i in range((num_data_columns+1),(2*num_data_columns+1)):
                self.table_view.setColumnHidden(i, False)
    
    def select_images(self,prompt="Choose one or more images"):  
        if self.imageDir is None:
            fname_images = QFileDialog.getOpenFileNames(self, prompt)
        else:
            try:
                fname_images = QFileDialog.getOpenFileNames(self, prompt, self.imageDir)
            except:
                fname_images = QFileDialog.getOpenFileNames(self, prompt)
        if fname_images == '':
            return
        self.imageDir = os.path.dirname(os.path.abspath(fname_images[0])) 
        return fname_images,True
        
    def select_library(self,prompt="Choose a library"): 
        if self.libraryDir is None:
            try:
                fname_library = QFileDialog.getOpenFileName(self, prompt, self.imageDir)
            except:
                fname_library,ok = QFileDialog.getOpenFileName(self, prompt)
        else:
            try:
                fname_library = QFileDialog.getOpenFileName(self, prompt, self.libraryDir)
            except:
                fname_library = QFileDialog.getOpenFileName(self, prompt)
        if fname_library == '':
            return
        self.libraryDir = os.path.dirname(os.path.abspath(fname_library)) 
        return fname_library,True

    def select_output_dir(self,prompt="Choose an output directory"): 
        if self.outputDir is None:
            try:
                outputDir = QFileDialog.getExistingDirectory(self, prompt, self.imageDir)
            except:
                outputDir = QFileDialog.getExistingDirectory(self, prompt)
        else:
            try:
                outputDir = QFileDialog.getExistingDirectory(self, prompt, self.outputDir)
            except:
                outputDir = QFileDialog.getExistingDirectory(self, prompt) 
        self.outputDir = os.path.abspath(outputDir)
        return outputDir
            


if __name__ == '__main__':
    app = QApplication(sys.argv)
    #app = QApplication.instance() # when running in Canopy
    win = MyWindow()
    win.show()
    app.exec_()