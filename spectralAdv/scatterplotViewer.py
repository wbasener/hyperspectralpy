from spectral import *
import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import pyqtgraph as pg
import pyqtgraph.opengl as gl

class scatterplotViewer(QMainWindow):
    # setup signals
    changedBands = pyqtSignal(dict)

    def __init__(self, settings=None, bnames=None, x_index=None, y_index=None, z_index=None, im_list=None, parent=None):
        super(scatterplotViewer, self).__init__(parent)
        self.setWindowTitle("3D Scatterplot Band Selection")
        self.setGeometry(650, 450, 200, 750)
        self.bnames = bnames
        self.x_index = x_index
        self.y_index = y_index
        self.z_index = z_index
        self.im_list = im_list

        # create widgets
        self.bnames_x = QListWidget()
        self.bnames_y = QListWidget()
        self.bnames_z = QListWidget()
        self.scatterplot = gl.GLViewWidget()
        self.scatterplot.setWindowTitle('3D Scatterplot')

        # create layout
        self.hbox = QHBoxLayout()
        self.hbox.addWidget(self.bnames_x)
        self.hbox.addWidget(self.bnames_y)
        self.hbox.addWidget(self.bnames_z)

        # set the layout for the central widget
        self.widget_central=QWidget()
        self.widget_central.setLayout(self.hbox)
        # set as central widget and dock widget
        self.setCentralWidget(self.widget_central)

        # add items to band selection list widgets
        self.bnames_x.addItems(self.bnames)
        self.bnames_y.addItems(self.bnames)
        self.bnames_z.addItems(self.bnames)

        # set the band indices
        self.bnames_x.setCurrentRow(self.x_index)
        self.bnames_y.setCurrentRow(self.y_index)
        self.bnames_z.setCurrentRow(self.z_index)

        # connect the index selection signals to update the plot
        self.bnames_x.currentRowChanged.connect(self.update_plot)
        self.bnames_y.currentRowChanged.connect(self.update_plot)
        self.bnames_z.currentRowChanged.connect(self.update_plot)

        # update the plot
        self.update_plot()


    def update_plot(self):

        try:
            self.scatterplot.removeItem(self.plotData)
        except:
            pass

        # get the data for the scatterplot
        pos = self.im_list[:,[self.bnames_x.currentRow(),
                              self.bnames_y.currentRow(),
                              self.bnames_z.currentRow()]]
        self.plotData = gl.GLScatterPlotItem(pos=pos, color=[1,.5,.5,.5])
        self.scatterplot.opts['distance'] = np.max(pos)
        self.g = gl.GLGridItem()
        self.scatterplot.addItem(self.g)
        self.scatterplot.addItem(self.plotData)

    def set_display_bands(self, band_indices):
        self.cb_blue.setCurrentIndex(band_indices['blue'])
        self.cb_green.setCurrentIndex(band_indices['gereen'])
        self.cb_red.setCurrentIndex(band_indices['red'])
        self.update_plot()