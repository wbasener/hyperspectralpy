from __future__ import division
import time
import sys
import os
import functools
from math import *
import matplotlib
import matplotlib.pyplot as plt
#matplotlib.use('Qt4Agg')
from spectral import *
import numpy as np
from scipy.optimize import nnls
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from pyqtgraph.widgets.MatplotlibWidget import *


# creating a custom MainWindow to collect resize events to redraw the plot
class MyMainWindow(QMainWindow):
    resized = pyqtSignal()
    def resizeEvent(self, event):
        self.resized.emit()
        QMainWindow.resizeEvent(self, event)

class interactiveStretch(MyMainWindow):
    # setup signal to send copied spectrum back
    imageStretchChanged = pyqtSignal(dict)

    def __init__(self, settings = None, imArray = None, stretch = None,
                 band_select_method = None, parent=None):
        super(interactiveStretch, self).__init__(parent)
        self.setWindowTitle("Interactive Image Stretch")
        self.resized.connect(self.resized_replot)
        self.setGeometry(850, 250, 1400, 750)
        self.settings = settings
        self.imArray = imArray
        self.stretch = stretch
        self.band_select_method = band_select_method
        self.band_idx = 0
        self.mousePressed = False
        self.firstTightRedraw = False
        self.fillColor = 'b'

        # manual stretch range
        self.label_plot_range = QLabel('Plot Range:')
        self.label_plot_range_min = QLineEdit('')
        self.label_plot_range_max = QLineEdit('')
        # set the max widths based on font size
        fm = self.label_plot_range_min.fontMetrics()
        m = self.label_plot_range_min.textMargins()
        c = self.label_plot_range_min.contentsMargins()
        w = np.max([fm.width('0.200238610804081')+m.left()+m.right()+c.left()+c.right(),
                    fm.width(str(np.min(self.imArray))) + m.left() + m.right() + c.left() + c.right(),
                    fm.width(str(np.max(self.imArray))) + m.left() + m.right() + c.left() + c.right()])
        self.label_plot_range_min.setMaximumWidth(w + 8)
        self.label_plot_range_max.setMaximumWidth(w + 8)

        # manual stretch range
        self.label_stretch_range = QLabel('Stretch Range:')
        self.label_stretch_min = QLineEdit(str(self.stretch['min'][0]))
        self.label_stretch_max = QLineEdit(str(self.stretch['max'][0]))
        # set the max widths based on font size
        fm = self.label_stretch_min.fontMetrics()
        m = self.label_stretch_min.textMargins()
        c = self.label_stretch_min.contentsMargins()
        w = np.max([fm.width('0.200238610804081')+m.left()+m.right()+c.left()+c.right(),
                    fm.width(str(np.min(self.imArray))) + m.left() + m.right() + c.left() + c.right(),
                    fm.width(str(np.max(self.imArray))) + m.left() + m.right() + c.left() + c.right()])
        self.label_stretch_min.setMaximumWidth(w + 8)
        self.label_stretch_max.setMaximumWidth(w + 8)
        self.label_stretch_min.textChanged.connect(self.update_stretch_min)
        self.label_stretch_max.textChanged.connect(self.update_stretch_max)

        # band selection radio buttons
        self.label_select_band = QLabel('Select Band:')
        self.rb_band_select_group=QButtonGroup()
        self.rb_select_blue=QRadioButton("Blue")
        self.rb_band_select_group.addButton(self.rb_select_blue)
        self.rb_select_green=QRadioButton("Green")
        self.rb_band_select_group.addButton(self.rb_select_green)
        self.rb_select_red=QRadioButton("Red")
        self.rb_band_select_group.addButton(self.rb_select_red)
        # set the checked band to blus for first time loading
        self.rb_select_blue.setChecked(True)

        # create the histogram plot widget
        self.MPWidget = MatplotlibWidget()
        fig = self.MPWidget.getFigure()
        win = fig.canvas.window()
        toolbar = win.findChild(QToolBar)
        toolbar.setVisible(False)
        self.subplot = self.MPWidget.getFigure().add_subplot(111)
        font = QFont()
        font.setPixelSize(20)

        # Layout
        self.widget_central = QWidget()
        vbox = QVBoxLayout()
        self.widget_central.setLayout(vbox)
        hbox = QHBoxLayout()
        hbox.addWidget(self.label_plot_range)
        hbox.addWidget(self.label_plot_range_min)
        hbox.addWidget(self.label_plot_range_max)
        hbox.addWidget(self.label_stretch_range)
        hbox.addWidget(self.label_stretch_min)
        hbox.addWidget(self.label_stretch_max)
        hbox.addWidget(self.label_select_band)
        hbox.addWidget(self.rb_select_blue)
        hbox.addWidget(self.rb_select_green)
        hbox.addWidget(self.rb_select_red)
        hbox.addStretch()
        vbox.addLayout(hbox)
        vbox.addWidget(self.MPWidget)
        #vbox.setSpacing(0)
        l,t,r,b = vbox.getContentsMargins()
        vbox.setContentsMargins(ceil(l/2), ceil(t/2) , ceil(r/2), 0)

        # set as central widget
        self.setCentralWidget(self.widget_central)
        self.show()

        # There appears to be a bug int he Matplotlib plot:
        # https://github.com/matplotlib/matplotlib/issues/10361
        # we have to modify the plot, then redraw
        self.MPWidget.getFigure().tight_layout()
        self.create_plot()
        self.firstPress = True

        # create signal/event handling
        self.rb_select_blue.clicked.connect(self.get_band_index)
        self.rb_select_green.clicked.connect(self.get_band_index)
        self.rb_select_red.clicked.connect(self.get_band_index)

        # customize the view based on band select methd (rgb vs pan)
        self.set_band_options()

    def set_band_options(self):
        # set the band selection if image is RGB
        if self.band_select_method == 'rgb':
            self.label_select_band.setVisible(True)
            self.rb_select_blue.setVisible(True)
            self.rb_select_green.setVisible(True)
            self.rb_select_red.setVisible(True)
        else:
            self.label_select_band.setVisible(False)
            self.rb_select_blue.setVisible(False)
            self.rb_select_green.setVisible(False)
            self.rb_select_red.setVisible(False)

    def create_plot(self):

        if self.band_select_method == 'rgb':
            banArray = self.imArray[:,:,self.band_idx]
        else:
            self.fillColor = 'gray'
            banArray = self.imArray

        lower_bound = np.min(banArray)
        upper_bound = np.max(banArray)

        self.hist_values,bin_edges = np.histogram(banArray, bins=np.linspace(lower_bound,upper_bound,500))
        self.bin_centers = (bin_edges[0:len(bin_edges)-1]+bin_edges[1:len(bin_edges)])/2
        self.subplot.clear()
        if self.settings.screen_width > 3000:
            self.subplot.axes.xaxis.set_tick_params(labelsize=20)
        self.subplot.axes.get_yaxis().set_ticks([])
        self.subplot.figure.canvas.updateGeometry()
        self.subplot.axes.autoscale(enable=True, tight=True)
        self.subplot.margins(0, tight=True)
        self.subplot.plot(self.bin_centers,self.hist_values,color='k')
        section = np.arange(-1, 1, 1 / 20.)
        self.subplot.fill_between(self.bin_centers, self.hist_values, color=self.fillColor, alpha=0.5)
        self.MPWidget.draw()
        # get the background
        fig = self.MPWidget.getFigure()  # gets the figure in a variable
        ax = self.subplot.axes  # get the axis in a variable
        self.background = fig.canvas.copy_from_bbox(ax.bbox)  # get everything currently plotted
        self.cid = self.subplot.figure.canvas.mpl_connect('axes_enter_event', self.replot_tight_from_mouseover)
        self.cid = self.MPWidget.getFigure().canvas.mpl_connect('button_press_event', self.onMouseDown)
        self.cid = self.MPWidget.getFigure().canvas.mpl_connect('button_release_event', self.onMouseUp)
        self.cid = self.MPWidget.getFigure().canvas.mpl_connect('motion_notify_event', self.onMouseMove)

        # plot the stretch region
        self.subplot.axvspan(self.stretch['min'][self.band_idx], self.stretch['max'][self.band_idx], facecolor='gray', alpha=0.25)
        self.replot_tight()

    def update_stretch_min(self):

        self.create_plot()
        try:
            self.stretch['min'][self.band_idx] = float(self.label_stretch_min.text())
        except:
            return # text cannot be converted to float

        fig = self.MPWidget.getFigure()
        ax = self.subplot.axes  # get the axis in a variable
        fig.canvas.restore_region(self.background)
        # draw and blit the stretch region
        ax.draw_artist(self.subplot.axvspan(self.stretch['min'][self.band_idx], self.stretch['max'][self.band_idx],
                                            facecolor='gray', alpha=0.25))  # adds the band_region to the axes
        fig.canvas.blit(ax.bbox)  # re-draws just what is needed

    def update_stretch_max(self):

        self.create_plot()
        try:
            self.stretch['max'][self.band_idx] = float(self.label_stretch_max.text())
        except:
            return # text cannot be converted to float



        fig = self.MPWidget.getFigure()
        ax = self.subplot.axes  # get the axis in a variable
        fig.canvas.restore_region(self.background)
        # draw and blit the stretch region
        ax.draw_artist(self.subplot.axvspan(self.stretch['min'][self.band_idx], self.stretch['max'][self.band_idx],
                                            facecolor='gray', alpha=0.25))  # adds the band_region to the axes
        fig.canvas.blit(ax.bbox)  # re-draws just what is needed

        self.stretch['type'] = 'slinear'

        if self.band_select_method == 'pan':
            for idx in range(3):
                self.stretch['min'][idx] = self.stretch['min'][0]
                self.stretch['max'][idx] = self.stretch['max'][0]

        self.imageStretchChanged.emit(self.stretch)


    def get_band_index(self):
        if self.rb_select_blue.isChecked() == True:
            self.band_idx = 0
            self.fillColor = 'b'
        if self.rb_select_green.isChecked() == True:
            self.band_idx = 1
            self.fillColor = 'g'
        if self.rb_select_red.isChecked() == True:
            self.band_idx = 2
            self.fillColor = 'r'

        self.firstTightRedraw = False
        self.firstPress = True
        self.create_plot()

    def resized_replot(self):
        self.create_plot()
        #fig = self.MPWidget.getFigure()
        #ax = self.subplot.axes  # get the axis in a variable
        #fig.canvas.restore_region(self.background)
        # draw and blit the stretch region
        #ax.draw_artist(self.subplot.axvspan(self.stretch['min'][self.band_idx], self.stretch['max'][self.band_idx], facecolor='gray', alpha=0.25))  # adds the band_region to the axes            fig.canvas.blit(ax.bbox)  # re-draws just what is needed


    def replot_tight_from_mouseover(self,dummy):
        self.replot_tight()

    def replot_tight(self):
        self.MPWidget.getFigure().tight_layout()
        if self.firstTightRedraw == False:
            self.MPWidget.draw()

    def onMouseDown(self, event):
        self.MPWidget.setCursor(Qt.SplitHCursor)
        self.mousePressed = True
        if self.firstPress == True:
            self.create_plot()
        self.firstPress = False

    def onMouseUp(self, event):
        self.MPWidget.setCursor(Qt.ArrowCursor)
        self.mousePressed = False

    def onMouseMove(self, event):

        if self.mousePressed == True:

            self.firstTightRedraw = True
            # determine the closest threshold
            try:
                thresh_idx = np.argmin([abs(event.xdata-self.stretch['min'][self.band_idx]),
                                        abs(event.xdata-self.stretch['max'][self.band_idx])])
            except:
                return # mouse was off plot

            if thresh_idx == 0:
                self.stretch['min'][self.band_idx] = event.xdata
                self.label_stretch_min.setText('%.6f' % event.xdata)
            else:
                self.stretch['max'][self.band_idx] = event.xdata
                self.label_stretch_max.setText('%.6f' % event.xdata)

            fig = self.MPWidget.getFigure()
            ax = self.subplot.axes  # get the axis in a variable
            fig.canvas.restore_region(self.background)
            # draw and blit the stretch region
            ax.draw_artist(self.subplot.axvspan(self.stretch['min'][self.band_idx], self.stretch['max'][self.band_idx], facecolor='gray', alpha=0.25))  # adds the band_region to the axes
            fig.canvas.blit(ax.bbox)  # re-draws just what is needed

            self.stretch['type'] = 'slinear'

            if self.band_select_method == 'pan':
                for idx in range(3):
                    self.stretch['min'][idx] = self.stretch['min'][0]
                    self.stretch['max'][idx] = self.stretch['max'][0]

            self.imageStretchChanged.emit(self.stretch)



    def get_closest_edge(self, x):
        np.argmin([abs(x-self.lower)])
