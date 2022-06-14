import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

import random

class pltDisplay(QMainWindow):
    def __init__(self, parent=None, title = "Plot Viewer", width=600, height=300, settings=None):
        super(pltDisplay, self).__init__(parent)
        self.settings = settings
        self.setWindowTitle(title)
        self.setGeometry(150, 350, width, height)

        # a figure instance to plot on
        self.figure = Figure()

        # this is the Canvas Widget that displays the `figure`
        # it takes the `figure` instance as a parameter to __init__
        self.canvas = FigureCanvas(self.figure)

        # this is the Navigation widget
        # it takes the Canvas widget and a parent
        self.toolbar = NavigationToolbar(self.canvas, self)

        # set the layout
        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        #self.setLayout(layout)


        # set as central widget
        widget_central = QWidget()
        widget_central.setLayout(layout)
        self.setCentralWidget(widget_central)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    pltWindow = pltDisplay(title = "Plot Viewer", width=600, height=300, settings=None)
    pltWindow.show()

