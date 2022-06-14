import operator
import sys
import os
import csv
import pickle
import numpy as np
from . import specTools
from . import spectraViewer
from . import scatterplotViewer
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from pyqtgraph.widgets.MatplotlibWidget import *
#from pyqtgraph.widgets.MatplotlibWidget import *


class tabelDisplayPropertiesDlg(QDialog):
    def __init__(self, bhat_coeff, table_display_mode, shade_cells, parent=None):
        super(tabelDisplayPropertiesDlg, self).__init__(parent)
        self.setGeometry(300, 300, 280, 100)
        self.setWindowTitle("Bhattacharyya Table Options")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.bhat_coeff = bhat_coeff
        self.table_display_mode = table_display_mode
        self.shade_cells = shade_cells

        # main layout
        layout = QVBoxLayout()
        # create coefficient inputs
        grid = QGridLayout()
        means_label = QtGui.QLabel('Means coefficient:')
        self.means_input = QLineEdit()
        self.means_input.setValidator(QDoubleValidator(0.0, 99.99, 6))
        self.means_input.setText(str(self.bhat_coeff[0]))
        shape_label = QtGui.QLabel('Shape coefficient:')
        self.shape_input = QLineEdit()
        self.shape_input.setValidator(QDoubleValidator(0.99, 99.99, 6))
        self.shape_input.setText(str(self.bhat_coeff[1]))
        # add coefficient inputs to grid layout
        grid.addWidget(means_label, 1, 0)
        grid.addWidget(self.means_input , 1, 1)
        grid.addWidget(shape_label, 2, 0)
        grid.addWidget(self.shape_input , 2, 1)
        layout.addLayout(grid)

        # create radio buttons
        self.b1 = QRadioButton("Bhattacharyya Distance")
        self.b1.setChecked(True)
        self.b1.toggled.connect(self.apply)
        self.b2 = QRadioButton("Mean Term Only")
        self.b2.toggled.connect(self.apply)
        self.b3 = QRadioButton("Shape Term Only")
        self.b3.toggled.connect(self.apply)
        self.b4 = QRadioButton("Avg. Mahalanobis Distance")
        self.b4.toggled.connect(self.apply)
        self.b5 = QRadioButton("Full Formula")
        self.b5.toggled.connect(self.apply)
        # add radio buttons to layout
        layout.addWidget(self.b1)
        layout.addWidget(self.b2)
        layout.addWidget(self.b3)
        layout.addWidget(self.b4)

        # create buttons
        self.bDefaults = QPushButton("Defaults")
        buttonBox = QDialogButtonBox(QDialogButtonBox.Apply |
                                     QDialogButtonBox.Close)
        # add buttons to layout
        hbox = QHBoxLayout()
        hbox.addWidget(self.bDefaults)
        hbox.addWidget(buttonBox)
        layout.addLayout(hbox)
        # set signals for the buttons
        self.connect(buttonBox.button(QDialogButtonBox.Apply),
            SIGNAL("clicked()"), self.apply)
        self.connect(self.bDefaults, SIGNAL("clicked()"), self.defaults)
        self.connect(buttonBox, SIGNAL("rejected()"), self, SLOT("reject()"))

        self.setLayout(layout)

    def apply(self):
        # set the display mode based on radio buttons
        if self.b1.isChecked() == True:
            self.table_display_mode = 'Bhat_distance'
        elif self.b2.isChecked() == True:
            self.table_display_mode = 'mean_only'
        elif self.b3.isChecked() == True:
            self.table_display_mode = 'shape_only'
        elif self.b4.isChecked() == True:
            self.table_display_mode = 'MD_avg'
        elif self.b5.isChecked() == True:
            self.table_display_mode = 'formula'
        else:
            self.table_display_mode = 'Bhat_distance'

        # emit the signal to send data back and refresh gui
        self.emit(SIGNAL("changed(QString, QString, QString)"),
                  self.table_display_mode, str(self.shape_input.text()), str(self.means_input.text()))

    def defaults(self):
        # set the default values
        self.b1.setChecked(True)
        self.means_input.setText(str(0.125))
        self.shape_input.setText(str(0.5))
        self.table_display_mode = 'Bhat_distance'
        # emit the signal to send data back and refresh gui
        self.emit(SIGNAL("changed(QString, QString, QString)"),
                  self.table_display_mode, str(self.shape_input.text()), str(self.means_input.text()))




class MyWindow(QMainWindow):
    def __init__(self, fname_images=[], settings=None,
                 imageDir = 'C:\\Users\\wfbsm\\Desktop\\specTools Tools\\images', 
                 libraryDir = None, outputDir = None, *args):
        super(MyWindow, self).__init__()
        # setGeometry(x_pos, y_pos, width, height)
        self.setGeometry(150, 50, 700, 450)
        self.setWindowTitle("Bhattacharyya Distance Comparison")
        # attache the plot data
        self.fname_images = fname_images
        self.imageDir = imageDir
        self.libraryDir = libraryDir
        self.outputDir = outputDir
        self.bhat_coeff = [0.125, 0.5]
        self.table_display_mode = 'Bhat_distance'
        self.shade_cells = True
        self.settings = settings
        
        # menu bar actions
        # File menu
        selectImagesAction = QAction("Open Images",self)
        selectImagesAction.triggered.connect(self.select_bhat_images)
        openFileAction = QAction("Open Bhat File",self)
        openFileAction.triggered.connect(self.open_bhat_file)
        saveFileAction = QAction("Save Bhat File",self)
        saveFileAction.triggered.connect(self.save_bhat_file)
        saveTableAction = QAction("Save Table as CSV",self)
        saveTableAction.triggered.connect(self.save_as_csv)
        exitAction = QAction("Close",self)
        exitAction.triggered.connect(self.close_this) 
        # Settings menu
        toggleCellShadingAction = QAction("Toggle Cell Shading",self)
        toggleCellShadingAction.triggered.connect(self.toggle_cell_shading)
        bhatFormulaAction = QAction("Bhattacharyya Formula Settings",self)
        bhatFormulaAction.triggered.connect(self.set_table_properties)
        
        # add the menu bar   
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu("&File")
        fileMenu.addAction(selectImagesAction)
        fileMenu.addAction(openFileAction)
        fileMenu.addAction(saveFileAction)
        fileMenu.addAction(saveTableAction)
        fileMenu.addAction(exitAction)
        settingsMenu = mainMenu.addMenu("&Settings")
        settingsMenu.addAction(toggleCellShadingAction)
        settingsMenu.addAction(bhatFormulaAction)
        
        # create the table widget
        self.table_view = QTableWidget()
        #self.setup_table()

        # create the plot widget
        try:
            self.MPWidget = MatplotlibWidgetBottomToolbar()
        except:
            self.MPWidget = MatplotlibWidget()
        #self.subplot = self.MPWidget.getFigure().add_subplot(111)
        #self.subplot.set_xlabel('Spectrum Number')
        #self.MPWidget.draw()
        self.plot = QDockWidget("", self)
        self.plot.setWidget(self.MPWidget)
        self.plot.setFloating(False)
        
        # set the layout for the central widget
        self.widget_central=QWidget()
        self.hbox = QHBoxLayout()
        self.widget_central.setLayout(self.hbox)
        self.hbox.addWidget(self.table_view)
        
        # set as central widget and dock widget
        self.setCentralWidget(self.widget_central)
        self.addDockWidget(Qt.RightDockWidgetArea, self.plot)
        
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # add stausbar with progressBar
        self.myStatusBar = QStatusBar()
        self.myStatusBar.showMessage('Ready')
        self.progressBar = QProgressBar()
        self.myStatusBar.addPermanentWidget(self.progressBar)
        self.progressBar.setGeometry(30, 40, 200, 25)
        self.progressBar.setValue(0)
        self.setStatusBar(self.myStatusBar)

        self.show()       
    
    def setup_table(self):
        nCols = len(self.header_labels)
        nRows = len(self.data_list)
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
            header.setResizeMode(0, QHeaderView.Stretch)
            header.setResizeMode(0, QHeaderView.Interactive)
            header.setResizeMode(1, QHeaderView.ResizeToContents)
            header.setResizeMode(2, QHeaderView.ResizeToContents)
            header.setResizeMode(3, QHeaderView.ResizeToContents)
            header.setResizeMode(4, QHeaderView.ResizeToContents)
            self.table_view.setColumnWidth(0, 800)
            self.table_view.wordWrap()
        else:
            header = self.table_view.horizontalHeader()
            header.setResizeMode(0, QHeaderView.Interactive)
            header.setResizeMode(1, QHeaderView.ResizeToContents)
            header.setResizeMode(2, QHeaderView.ResizeToContents)
            header.setResizeMode(3, QHeaderView.ResizeToContents)
            header.setResizeMode(4, QHeaderView.ResizeToContents)
            self.table_view.setColumnWidth(0, 800)
            self.table_view.wordWrap()
        # enable sorting
        self.table_view.setSortingEnabled(True)
        # add the data
        self.add_data(self.data_list)
        
        # signal for selection changed
        self.table_view.itemSelectionChanged.connect(self.selection_changed)
        
    def not_supported(self):
        QMessageBox.information(self, "Not Supported","That functionality is not yet supported.") 
    
    def close_this(self): 
        self.close()

    def save_as_csv(self):
        # get save filename
        fname = QFileDialog.getSaveFileName(self, 'Save CSV File', '', '(*.csv)')
        if fname == '':
            return

        # create a list of lists with the table data
        tableData = []
        rowData = ['']
        for name in self.header_labels: rowData.append(name)
        tableData.append(rowData)
        for row_idx in range(self.table_view.rowCount()):
            rowData = [self.header_labels[row_idx]]
            for col_idx in range(self.table_view.columnCount()):
                rowData.append(self.table_view.item(row_idx,col_idx).text())
            tableData.append(rowData)

        # save the table to csv file
        with  open(fname, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(tableData)
              
    def select_bhat_images(self):
        # choose parameters
        self.num_PCs,ok = QInputDialog.getInt(self,"Bhattacharyya Distance, Two Images","Number of Principle Components",10,0,1000,0)
		
        if ok:        
            # choose the images
            fname_images = self.select_images()
            if not (fname_images == ''):
                self.fname_images = fname_images
                self.compute_bhat_distances()

    def compute_bhat_distances(self):

        # load the headers
        self.header_labels = []
        for image_name in self.fname_images:
            self.header_labels.append(os.path.basename(image_name))
        self.nCols = len(self.header_labels)
        self.nRows = len(self.header_labels)
        self.table_view.setRowCount(self.nRows)
        self.table_view.setColumnCount(self.nRows)
        self.table_view.setHorizontalHeaderLabels(self.header_labels)
        self.table_view.setVerticalHeaderLabels(self.header_labels)
        
        # resize to fit the table
        widths = []
        for i in range(len(self.header_labels)):
            self.table_view.setColumnWidth(i, 120)
            widths.append(self.table_view.columnWidth(i))
        full_width = np.min([np.sum(widths)+np.max(widths)+500,1000])
        heights = []
        for i in range(len(self.header_labels)):
            heights.append(self.table_view.rowHeight(i))
        full_height = np.max([500,np.min([np.sum(heights)+np.max(heights),1000])])
        self.resize(int(full_width)+60,int(full_height)+60)

        # setup the progress bar information
        self.myStatusBar.showMessage('Computing Bhattacharyya Dinstances...')
        num_images = len(self.fname_images)
        progress_total = 1+num_images*(num_images-1)/2
        progress = 0
        self.progressBar.setValue(100*progress/progress_total)

        # create dictionary of rgb images
        images = specTools.open_read_images(self.fname_images,0)
        self.rgb_images = {}
        for image in images:
            rgb_image = specTools.make_jpg_array(image)
            self.rgb_images[image.name] = rgb_image

        self.BD_means = np.zeros([self.nRows,self.nCols])
        self.BD_shape = np.zeros([self.nRows,self.nCols])
        self.MD_avg = np.zeros([self.nRows,self.nCols])
        progress = progress + 1
        self.progressBar.setValue(100*progress/progress_total)
        for r in range(self.nRows):
            for c in range(r+1,self.nCols):
                inputs = specTools.inputs_bd_struc() # set the optional parameters
                inputs.verbose = 0
                inputs.im_fnames = [self.fname_images[r],self.fname_images[c]]
                images = specTools.open_read_images(inputs.im_fnames,inputs.verbose)                
                if images[0].im.nbands == images[1].im.nbands:
                    # compute the Bhattacharyya distance
                    Dist, Dist_means, Dist_shape, MD_avg, mean1, evals1, mean2, evals2 = \
                        specTools.bhattacharyya_distance(images[0].arr, images[1].arr, self.num_PCs, inputs)
                    evals1[evals1 <= 0] = np.min(evals1[evals1 > 0]) # force the evals to be positive, nonzero
                    evals2[evals2 <= 0] = np.min(evals2[evals2 > 0]) # force the evals to be positive, nonzero
                    #H = np.sqrt(1-np.exp(-(Dist)))
                    self.BD_means[r,c] = np.min([Dist_means,1000])
                    self.BD_shape[r,c] = np.min([Dist_shape,1000])
                    self.MD_avg[r,c] = MD_avg
                else:
                    self.BD_means[r,c] = -1
                    self.BD_shape[r,c] = -1

                # create the mean eigenvalue plots
                if r==0:
                    if c==1:
                        # create the eigenvalue plot and a plot evals for image 0
                        ms = ''
                        ls = '-'
                        if 'AVIRIS' in self.header_labels[0]:
                            ls = ':'
                        if 'HYDICE' in self.header_labels[0]:
                            ls = '-.'
                        if 'full' in self.header_labels[0]:
                            ms = 'o'
                        if 'scotty' in self.header_labels[0]:
                            ms = 'x'
                        plt.figure(1)
                        plt.plot(np.log(evals1),linestyle=ls,marker=ms,
                                 label=self.header_labels[0] + ' ' + str(np.product(evals1[range(self.num_PCs)])))
                        plt.figure(2)
                        plt.plot(images[0].im.bands.centers,mean1,linestyle=ls,marker=ms,
                                 label=self.header_labels[0])
                    ms = ''
                    ls = '-'
                    if 'AVIRIS' in self.header_labels[c]:
                        ls = ':'
                    if 'HYDICE' in self.header_labels[c]:
                        ls = '-.'
                    if 'full' in self.header_labels[c]:
                        ms = 'o'
                    if 'scotty' in self.header_labels[c]:
                        ms = 'x'
                    plt.figure(1)
                    plt.plot(np.log(evals2),linestyle=ls,marker=ms,
                             label=self.header_labels[c] + ' ' + str(np.product(evals2[range(self.num_PCs)])))
                    plt.figure(2)
                    plt.plot(images[1].im.bands.centers,mean2,linestyle=ls,marker=ms,
                                 label=self.header_labels[c])

                progress = progress + 1
                self.progressBar.setValue(100*progress/progress_total)

        # Show the eigenvalue plot
        plt.figure(1)
        if self.settings.screen_width > 3000:
            plt.legend(fontsize=30)
        else:
            plt.legend()
        plt.xlabel('Eigenvalue Number')
        plt.ylabel('log Eigenvalue')
        plt.figure(2)
        if self.settings.screen_width > 3000:
            plt.legend(fontsize=30)
        else:
            plt.legend()
        plt.xlabel('Wavelength')
        plt.ylabel('Reflectance')
        plt.show()

        # fill in the entries below the diagonal
        for r in range(self.nRows):
            for c in range(r):
                self.BD_means[r,c] = self.BD_means[c,r]
                self.BD_shape[r,c] = self.BD_shape[c,r]
                self.MD_avg[r,c] = self.MD_avg[c,r]
        
        # fill entries in the table for display
        self.refresh_table()

        # signal for selection changed
        self.table_view.itemSelectionChanged.connect(self.selection_changed)

        self.progressBar.setValue(0)
        self.myStatusBar.showMessage('Ready')

    def refresh_table(self):
        vals = np.zeros([self.nRows,self.nCols])
        if self.table_display_mode == 'Bhat_distance':
            for r in range(self.nRows):
                for c in range(self.nCols):
                    vals[r,c] = (self.bhat_coeff[0] * self.BD_means[r,c] + self.bhat_coeff[1] * self.BD_shape[r,c])
                    self.table_view.setItem(r,c, QTableWidgetItem('%.3f' %
                        (self.bhat_coeff[0] * self.BD_means[r,c] + self.bhat_coeff[1] * self.BD_shape[r,c])))
        elif self.table_display_mode == 'mean_only':
            for r in range(self.nRows):
                for c in range(self.nCols):
                    vals[r,c] = (self.bhat_coeff[0]*self.BD_means[r,c])
                    self.table_view.setItem(r,c, QTableWidgetItem('%.3f' % (self.bhat_coeff[0]*self.BD_means[r,c])))
        elif self.table_display_mode == 'shape_only':
            for r in range(self.nRows):
                for c in range(self.nCols):
                    vals[r,c] = (self.bhat_coeff[0]*self.BD_shape[r,c])
                    self.table_view.setItem(r,c, QTableWidgetItem('%.3f' % (self.bhat_coeff[0]*self.BD_shape[r,c])))
        elif self.table_display_mode == 'MD_avg':
            for r in range(self.nRows):
                for c in range(self.nCols):
                    vals[r,c] = self.MD_avg[r,c]
                    self.table_view.setItem(r,c, QTableWidgetItem('%.3f' % self.MD_avg[r,c]))
        elif self.table_display_mode == 'formula':
            for r in range(self.nRows):
                for c in range(self.nCols):
                    vals[r,c] = (self.bhat_coeff[0] * self.BD_means[r,c] + self.bhat_coeff[1] * self.BD_shape[r,c])
                    self.table_view.setItem(r,c, QTableWidgetItem(
                        str(self.bhat_coeff[0])+'*'+
                        '%.2f' % self.BD_means[r,c]+'+'+
                        str(self.bhat_coeff[1])+'*'+
                        '%.2f' % self.BD_shape[r,c]))
        else:
            for r in range(self.nRows):
                for c in range(self.nCols):
                    vals[r,c] = (self.bhat_coeff[0] * self.BD_means[r,c] + self.bhat_coeff[1] * self.BD_shape[r,c])
                    self.table_view.setItem(r,c, QTableWidgetItem(str(
                        self.bhat_coeff[0] * self.BD_means[r,c] + self.bhat_coeff[1] * self.BD_shape[r,c])))

        # shade cells by value
        if self.shade_cells == True:
            vals_scale = vals
            vals_scale[vals>10^6] = 100
            scale = 100/np.max(vals_scale)
            for r in range(self.nRows):
                for c in range(self.nCols):
                    grayVal = 255-int(vals_scale[r,c]*scale)
                    self.table_view.item(r, c).setBackground(QtGui.QColor(grayVal, grayVal, grayVal))


    def selection_changed(self):
        # get the row and column of the selection
        indices = self.table_view.selectedIndexes()
        try:
            row = indices[0].row()
            column = indices[0].column()
        except:
            # user clicked outside the table entries
            return

        # show images
        rgb_row = self.rgb_images[self.header_labels[row]]
        rgb_column = self.rgb_images[self.header_labels[column]]

        if not hasattr(self, 'subplot_row'):
            self.subplot_row = self.MPWidget.getFigure().add_subplot(121)
            self.subplot_row.imshow(rgb_row)
            self.subplot_row.set_title(self.header_labels[row])
            self.subplot_col = self.MPWidget.getFigure().add_subplot(122)
            self.subplot_col.imshow(rgb_column)
            self.subplot_col.set_title(self.header_labels[column])
            self.MPWidget.draw()
        else:
            self.subplot_row.imshow(rgb_row)
            self.subplot_row.set_title(self.header_labels[row])
            self.subplot_col.imshow(rgb_column)
            self.subplot_col.set_title(self.header_labels[column])
            self.MPWidget.draw()

    def toggle_cell_shading(self):
        if hasattr(self, 'nRows'):
            if self.shade_cells == True:
                self.shade_cells = False
            else:
                self.shade_cells = True
            self.refresh_table()
        else:
            pass

    def set_table_properties(self):
        if hasattr(self, 'nRows'):
            self.dialog = tabelDisplayPropertiesDlg(self.bhat_coeff, self.table_display_mode, self)
            self.connect(self.dialog, SIGNAL("changed(QString, QString, QString)"), self.update_table_properties)
            self.dialog.show()
        else:
            pass

    def save_bhat_file(self):
        fname = QFileDialog.getSaveFileName(self, 'Save File', '', 'Bhattacharyya Distnace (*.bhat)')
        if fname == '':
            return
        self.myStatusBar.showMessage('Loading File...')

        # create a disctionary will all the needed data
        data = {'nRows': self.nRows,
                'nCols': self.nCols,
                'means': self.BD_means,
                'shape': self.BD_shape,
                'bhat_coeff': self.bhat_coeff,
                'rgb_images': self.rgb_images,
                'header_labels': self.header_labels}
        # Write to file
        f_myfile = open(fname, 'wb')
        pickle.dump(data, f_myfile)
        f_myfile.close()

    def open_bhat_file(self):
        fname = QFileDialog.getOpenFileName(self, 'Open File', '', 'Bhattacharyya Distnace (*.bhat)')
        if fname == '':
            return
        f_myfile = open(fname, 'rb')
        data = pickle.load(f_myfile)  # variables come out in the order you put them in
        f_myfile.close()
        # put data into variables
        self.nRows = data['nRows']
        self.nCols = data['nCols']
        self.BD_means = data['means']
        self.BD_shape = data['shape']
        self.bhat_coeff = data['bhat_coeff']
        self.rgb_images = data['rgb_images']
        self.header_labels = data['header_labels']

        # setup the table with the new data

        # load the headers
        self.table_view.setRowCount(self.nRows)
        self.table_view.setColumnCount(self.nRows)
        self.table_view.setHorizontalHeaderLabels(self.header_labels)
        self.table_view.setVerticalHeaderLabels(self.header_labels)

        # resize to fit the table
        widths = []
        for i in range(len(self.header_labels)):
            self.table_view.setColumnWidth(i, 120)
            widths.append(self.table_view.columnWidth(i))
        full_width = np.min([np.sum(widths)+np.max(widths)+500,1000])
        heights = []
        for i in range(len(self.header_labels)):
            heights.append(self.table_view.rowHeight(i))
        full_height = np.max([500,np.min([np.sum(heights)+np.max(heights),1000])])
        self.resize(int(full_width)+60,int(full_height)+60)        # fill entries in the table for display
        self.refresh_table()

        # signal for selection changed
        self.table_view.itemSelectionChanged.connect(self.selection_changed)

        self.progressBar.setValue(0)
        self.myStatusBar.showMessage('Ready')

    def update_table_properties(self, table_display_mode, coeff_means, coeff_shape):
        self.table_display_mode = table_display_mode
        self.bhat_coeff = [float(coeff_means), float(coeff_shape)]
        self.table_display_mode = table_display_mode
        self.refresh_table()
    
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
        return fname_images
        
    def select_library(self,prompt="Choose a library"): 
        if self.libraryDir is None:
            try:
                fname_library = QFileDialog.getOpenFileName(self, prompt, self.imageDir)
            except:
                fname_library = QFileDialog.getOpenFileName(self, prompt)
        else:
            try:
                fname_library = QFileDialog.getOpenFileName(self, prompt, self.libraryDir)
            except:
                fname_library = QFileDialog.getOpenFileName(self, prompt)
        if fname_library == '':
            return
        self.libraryDir = os.path.dirname(os.path.abspath(fname_library)) 
        return fname_library

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
    form = MyWindow()
    form.show()
    app.exec_()