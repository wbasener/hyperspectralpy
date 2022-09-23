import sys
import os
import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class settings_struc:
    def __init__(self):
        self.font_size = 12
        self.plot_font_size = 20
        self.gui_size_scale = 100
        self.screen_width = 0
        self.screen_height = 0
        

class settingsDialog(QDialog):
    settingsChanged = pyqtSignal(object)

    def __init__(self, parent=None, settings=None):
        super(settingsDialog, self).__init__(parent)
        self.setWindowTitle("Settings")
        self.setGeometry(150, 150, 550, 250)

        if settings == None:
            self.settings = settings_struc()
        else:
            self.settings = settings

        # list widget with list of images
        self.label_font_size = QLabel("Font size:")
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(8,40)
        self.spin_font_size.setValue(self.settings.font_size)

        self.label_plot_font_size = QLabel("Font size in plots:")
        self.spin_plot_font_size = QSpinBox()
        self.spin_plot_font_size.setRange(8,40)
        self.spin_plot_font_size.setValue(self.settings.plot_font_size)

        self.label_gui_size_scale = QLabel("GUI size scale:")
        self.spin_gui_size_scale = QSpinBox()
        self.spin_gui_size_scale.setRange(10,400)
        self.spin_gui_size_scale.setSingleStep(5)
        self.spin_gui_size_scale.setValue(self.settings.gui_size_scale)

        # add buttons to layout
        grid = QGridLayout()
        grid.addWidget(self.label_font_size,1,1)
        grid.addWidget(self.spin_font_size,1,2)
        grid.addWidget(self.label_plot_font_size,2,1)
        grid.addWidget(self.spin_plot_font_size,2,2)
        grid.addWidget(self.label_gui_size_scale,3,1)
        grid.addWidget(self.spin_gui_size_scale,3,2)
        self.setLayout(grid)

        # set signals for the buttons
        self.spin_font_size.valueChanged.connect(self.value_change)
        self.spin_plot_font_size.valueChanged.connect(self.value_change)
        self.spin_gui_size_scale.valueChanged.connect(self.value_change)

    def value_change(self):
        print(self.spin_font_size.value())
        print(self.spin_plot_font_size.value())
        print(self.spin_gui_size_scale.value())

        # update settings with the new values
        self.settings.font_size = self.spin_font_size.value()
        self.settings.plot_font_size = self.spin_plot_font_size.value()
        self.settings.gui_size_scale = self.spin_gui_size_scale.value()
        # emit signal that the settings have changed
        self.settingsChanged.emit(self.settings)


if __name__ == '__main__':
    #app = QApplication.instance() # when running in Canopy
    app = QApplication(sys.argv)
    GUI = settingsDialog()
    GUI.show()
    sys.exit(app.exec_())