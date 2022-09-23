from spectral import *
import numpy as np
#from PyQt4.QtCore import *
#from PyQt4.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import pyqtgraph as pg
import pyqtgraph.opengl as gl

class scatterplot3DViewer(QMainWindow):
    # setup signals
    changedBands = pyqtSignal(dict)

    def __init__(self, settings=None, bnames=None, x_index=None, y_index=None, z_index=None, im_list=None, pt_colors = None, parent=None):
        super(scatterplot3DViewer, self).__init__(parent)
        self.setWindowTitle("3D Scatterplot Band Selection")
        self.setGeometry(650, 450, 200, 750)
        self.settings = settings
        self.bk_color = 'black'
        self.pt_color_type = 'default'
        self.bnames = bnames
        self.x_index = x_index
        self.y_index = y_index
        self.z_index = z_index
        self.im_list = im_list
        # create the point colors array
        nPix = np.shape(pt_colors)[0]
        o = np.reshape(np.ones(nPix), (nPix, 1))
        self.pt_colors = np.hstack((pt_colors/255.,o))

        # menu bar actions
        # Preferences menu
        toggleBackgroundColorAction = QAction("Toggle Background Color B/G/W",self)
        toggleBackgroundColorAction.triggered.connect(self.toggle_background_color)
        togglePointColorsAction = QAction("Toggle Point Colors",self)
        togglePointColorsAction.triggered.connect(self.toggle_point_colors)

        # add the menu bar
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu("&Preferences ")
        fileMenu.addAction(toggleBackgroundColorAction)
        fileMenu.addAction(togglePointColorsAction)


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
            self.scatterplot.removeItem(self.g)
        except:
            pass

        # get the data for the scatterplot
        pos = self.im_list[:,[self.bnames_x.currentRow(),
                              self.bnames_y.currentRow(),
                              self.bnames_z.currentRow()]]

        if self.bk_color == 'black':

            if self.pt_color_type == 'default':
                self.plotData = gl.GLScatterPlotItem(pos=pos, color=[1,.5,.5,.5])
                self.plotData.setGLOptions('additive')
            else:
                self.plotData = gl.GLScatterPlotItem(pos=pos, color=self.pt_colors)
                self.plotData.setGLOptions('additive')

        elif self.bk_color == 'gray':
            if self.pt_color_type == 'default':
                self.plotData = gl.GLScatterPlotItem(pos=pos, color=[1,.5,.5,.5])
                self.plotData.setGLOptions('additive')
            else:
                self.plotData = gl.GLScatterPlotItem(pos=pos, color=self.pt_colors)
                self.plotData.setGLOptions('additive')

        else:
            if self.pt_color_type == 'default':
                self.plotData = gl.GLScatterPlotItem(pos=pos, color=[0.5,0.2,0.2,.5])
                self.plotData.setGLOptions('translucent')
            else:
                self.plotData = gl.GLScatterPlotItem(pos=pos, color=self.pt_colors)
                self.plotData.setGLOptions('translucent')

        self.scatterplot.addItem(self.plotData)

        # add a mesh for the x-y plane
        self.scatterplot.opts['distance'] = np.max(pos)
        self.g = gl.GLGridItem()
        self.scatterplot.addItem(self.g)

        # add the x-y-x axis
        self.a = gl.GLAxisItem(size=QVector3D(20, 20, 20))
        self.scatterplot.addItem(self.a)

        # set camera looking at the mean of the data
        self.scatterplot.opts['center'] = QVector3D(np.mean(pos[:,0]), np.mean(pos[:,1]), np.mean(pos[:,2]))


    def update_colors(self):

        try:
            opts = self.scatterplot.opts
            self.scatterplot.removeItem(self.plotData)
        except:
            pass

        # get the data for the scatterplot
        pos = self.im_list[:,[self.bnames_x.currentRow(),
                              self.bnames_y.currentRow(),
                              self.bnames_z.currentRow()]]

        if self.bk_color == 'black':

            if self.pt_color_type == 'default':
                self.plotData = gl.GLScatterPlotItem(pos=pos, color=[1,.5,.5,.5])
                self.plotData.setGLOptions('additive')
            else:
                self.plotData = gl.GLScatterPlotItem(pos=pos, color=self.pt_colors)
                self.plotData.setGLOptions('additive')

        elif self.bk_color == 'gray':
            if self.pt_color_type == 'default':
                self.plotData = gl.GLScatterPlotItem(pos=pos, color=[1,.5,.5,.5])
                self.plotData.setGLOptions('additive')
            else:
                self.plotData = gl.GLScatterPlotItem(pos=pos, color=self.pt_colors)
                self.plotData.setGLOptions('additive')

        else:
            if self.pt_color_type == 'default':
                self.plotData = gl.GLScatterPlotItem(pos=pos, color=[0.5,0.2,0.2,.5])
                self.plotData.setGLOptions('translucent')
            else:
                self.plotData = gl.GLScatterPlotItem(pos=pos, color=self.pt_colors)
                self.plotData.setGLOptions('translucent')

        self.scatterplot.addItem(self.plotData)
        # set camera looking at the mean of the data
        self.scatterplot.opts = opts



    def set_display_bands(self, band_indices):
        self.cb_blue.setCurrentIndex(band_indices['blue'])
        self.cb_green.setCurrentIndex(band_indices['gereen'])
        self.cb_red.setCurrentIndex(band_indices['red'])
        self.update_plot()

    def toggle_background_color(self):
        if self.bk_color == 'black':
            self.scatterplot.setBackgroundColor(pg.mkColor(100,100,100))
            self.bk_color = 'gray'
            self.update_colors()
        elif self.bk_color == 'gray':
            self.scatterplot.setBackgroundColor(pg.mkColor(255,255,255))
            self.bk_color = 'white'
            self.update_colors()
        else:
            self.scatterplot.setBackgroundColor(pg.mkColor(0,0,0))
            self.bk_color = 'black'
            self.update_colors()

    def toggle_point_colors(self):
        if self.pt_color_type == 'default':
            self.pt_color_type = 'pixel_colors'
            self.update_colors()
        else:
            self.pt_color_type = 'default'
            self.update_colors()
