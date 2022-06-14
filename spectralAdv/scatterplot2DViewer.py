from spectral import *
import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import pyqtgraph as pg
import pyqtgraph.opengl as gl

class scatterplot2DViewer(QMainWindow):
    # setup signals
    changedBands = pyqtSignal(dict)

    def __init__(self, settings=None, bnames=None, x_index=None, y_index=None, im_list=None, pt_colors = None, parent=None):
        super(scatterplot2DViewer, self).__init__(parent)
        self.setWindowTitle("2D Scatterplot Viewer")
        self.setGeometry(650, 450, 1400, 1000)
        self.settings = settings
        self.bk_color = 'black'
        self.pt_color_type = 'default'
        self.lastClicked = []
        self.bnames = bnames
        self.x_index = x_index
        self.y_index = y_index
        self.im_list = im_list
        # create the point colors array
        nPix = np.shape(pt_colors)[0]
        o = 255*np.reshape(np.ones(nPix), (nPix, 1))
        self.pt_colors = np.hstack((pt_colors,o))
        self.pt_brush_colors = None

        # menu bar actions
        # Preferences menu
        toggleBackgroundColorAction = QAction("Toggle Background Color B/G/W",self)
        toggleBackgroundColorAction.triggered.connect(self.toggle_background_color)
        togglePointColorsAction = QAction("Toggle Point Colors (very slow)",self)
        togglePointColorsAction.triggered.connect(self.toggle_point_colors)

        # add the menu bar
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu("&Preferences ")
        fileMenu.addAction(toggleBackgroundColorAction)
        fileMenu.addAction(togglePointColorsAction)

        # create widgets
        self.bnames_x = QListWidget()
        self.bnames_y = QListWidget()
        self.PlotWidget = pg.PlotWidget()

        # get the max width of text in the band names
        fm = QLineEdit().fontMetrics()
        w = 0
        for b in self.bnames:
            w = max([w, 1.2 * fm.width(b)])
        # set the max width on the band names list widgets
        self.bnames_x.setMaximumWidth(w)
        self.bnames_y.setMaximumWidth(w)

        # create layout
        self.hbox = QHBoxLayout()
        self.hbox.addWidget(self.bnames_x)
        self.hbox.addWidget(self.bnames_y)
        self.hbox.addWidget(self.PlotWidget)

        # set the layout for the central widget
        self.widget_central=QWidget()
        self.widget_central.setLayout(self.hbox)
        # set as central widget and dock widget
        self.setCentralWidget(self.widget_central)

        # add items to band selection list widgets
        self.bnames_x.addItems(self.bnames)
        self.bnames_y.addItems(self.bnames)

        # set the band indices
        self.bnames_x.setCurrentRow(self.x_index)
        self.bnames_y.setCurrentRow(self.y_index)

        # connect the index selection signals to update the plot
        self.bnames_x.currentRowChanged.connect(self.update_plot)
        self.bnames_y.currentRowChanged.connect(self.update_plot)

        # update the plot
        self.create_plot()
        self.update_plot()

    def create_plot(self):
        self.scatterPlotItem = pg.ScatterPlotItem(size=7, pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 255, 120))
        self.scatterPlotItem.sigClicked.connect(self.clicked)
        self.PlotWidget.addItem(self.scatterPlotItem)

    def create_plot_scrath(self):

        if self.bk_color == 'black':
            self.PlotWidget.setBackgroundBrush(pg.mkColor(0,0,0))
            if self.pt_color_type == 'default':
                self.scatterPlotItem = pg.ScatterPlotItem(size=7, pen=pg.mkPen(None),
                                                          brush=pg.mkBrush(255, 125, 125, 125))
            else:
                pass
                #self.plotData = gl.GLScatterPlotItem(pos=pos, color=self.pt_colors)

        elif self.bk_color == 'gray':
            self.PlotWidget.setBackgroundBrush(pg.mkColor(100,100,100))
            if self.pt_color_type == 'default':
                self.scatterPlotItem = pg.ScatterPlotItem(size=7, pen=pg.mkPen(None),
                                                          brush=pg.mkBrush(255, 125, 125, 125))
            else:
                pass
                #self.plotData = gl.GLScatterPlotItem(pos=pos, color=self.pt_colors)

        else:
            self.PlotWidget.setBackgroundBrush(pg.mkColor(255,255,255))
            if self.pt_color_type == 'default':
                self.scatterPlotItem = pg.ScatterPlotItem(size=7, pen=pg.mkPen(None),
                                                          brush=pg.mkBrush(125, 50, 50, 125))
            else:
                pass
                #self.plotData = gl.GLScatterPlotItem(pos=pos, color=self.pt_colors)

        self.scatterPlotItem.sigClicked.connect(self.clicked)
        self.PlotWidget.addItem(self.scatterPlotItem)

    def update_plot(self):
        # get the data for the scatterplot
        x_data = self.im_list[:,self.bnames_x.currentRow()]
        y_data = self.im_list[:,self.bnames_y.currentRow()]

        # set the background and pen colors
        if self.bk_color == 'black':
            self.PlotWidget.setBackgroundBrush(pg.mkColor(0,0,0))
            if self.pt_color_type == 'default':
                brush = pg.mkBrush(255, 255, 255, 125)
            else:
                if self.pt_brush_colors == None: # making a brush for each point is SLOW, so only do it once when first called
                    self.pt_brush_colors =  [pg.mkBrush(c) for c in self.pt_colors]
                brush = self.pt_brush_colors

        elif self.bk_color == 'gray':
            self.PlotWidget.setBackgroundBrush(pg.mkColor(100,100,100))
            if self.pt_color_type == 'default':
                brush = pg.mkBrush(255, 255, 255, 125)
            else:
                if self.pt_brush_colors == None: # making a brush for each point is SLOW, so only do it once when first called
                    self.pt_brush_colors =  [pg.mkBrush(c) for c in self.pt_colors]
                brush = self.pt_brush_colors

        else:
            self.PlotWidget.setBackgroundBrush(pg.mkColor(255,255,255))
            if self.pt_color_type == 'default':
                brush = pg.mkBrush(50, 50, 50, 125)
            else:
                if self.pt_brush_colors == None: # making a brush for each point is SLOW, so only do it once when first called
                    self.pt_brush_colors =  [pg.mkBrush(c) for c in self.pt_colors]
                brush = self.pt_brush_colors

        self.scatterPlotItem.clear()
        self.scatterPlotItem.addPoints(x=x_data, y=y_data, brush=brush)

    def set_display_bands(self, band_indices):
        self.cb_blue.setCurrentIndex(band_indices['blue'])
        self.cb_green.setCurrentIndex(band_indices['gereen'])
        self.cb_red.setCurrentIndex(band_indices['red'])
        self.update_plot()

    def clicked(self, plot, points):
        for p in self.lastClicked:
            p.resetPen()
        for p in points:
            p.setPen('b', width=15)
            self.lastClicked = points

    def toggle_background_color(self):
        if self.bk_color == 'black':
            self.PlotWidget.setBackgroundBrush(pg.mkColor(100,100,100))
            self.bk_color = 'gray'
            self.update_plot()
        elif self.bk_color == 'gray':
            self.PlotWidget.setBackgroundBrush(pg.mkColor(255,255,255))
            self.bk_color = 'white'
            self.update_plot()
        else:
            self.PlotWidget.setBackgroundBrush(pg.mkColor(0,0,0))
            self.bk_color = 'black'
            self.update_plot()

    def toggle_point_colors(self):
        if self.pt_color_type == 'default':
            self.pt_color_type = 'pixel_colors'
            self.update_plot()
        else:
            self.pt_color_type = 'default'
            self.update_plot()