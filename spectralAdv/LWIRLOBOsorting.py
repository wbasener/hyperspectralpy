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


class LWIRLOBOsorting(QMainWindow):
    def __init__(self, parent=None, settings=None):
        super(LWIRLOBOsorting, self).__init__()
        self.setWindowTitle("LOBO Output Sorting")
        self.setWindowIcon(QIcon('files_icon.ico'))
        self.setGeometry(150, 150, 500, 0)

        self.ChoosehsicBtn = QPushButton('Choose hsic directory', self)
        self.ChoosehsicBtn.setFixedWidth(150)
        self.ChoosehsicBtn.clicked.connect(self.choose_hsic_dir)
        self.hsicDirText = QLineEdit()
        self.hsicDirText.setText("hsic directory")

        self.ChooseDirOutBtn = QPushButton('Choose output directory', self)
        self.ChooseDirOutBtn.setFixedWidth(150)
        self.ChooseDirOutBtn.clicked.connect(self.choose_output_dir)
        self.DirOutText = QLineEdit()
        self.DirOutText.setText("output directory")

        # add a horizontal seperator line
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)

        # Copy Files for Cue Report Hits
        self.CRhitsCheckBox = QCheckBox('Copy files associated with cue report', self)
        self.CRhitsCheckBox.stateChanged.connect(self.CRhitsCheckBoxChanged)
        self.ChooseCRBtn = QPushButton('Choose cue report', self)
        self.ChooseCRBtn.setFixedWidth(150)
        self.ChooseCRBtn.clicked.connect(self.choose_cue_report)
        self.CRfileText = QLineEdit()
        self.CRfileText.setText("cue report filename")

        # add a horizontal seperator line
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)

        # Copy Files near shape file locations
        self.ShapefileCheckBox = QCheckBox('Copy files near shapefile location', self)
        self.ShapefileCheckBox.stateChanged.connect(self.ShapefileCheckBoxChanged)
        self.ChooseShapefileBtn = QPushButton('Choose shapefile', self)
        self.ChooseShapefileBtn.setFixedWidth(150)
        self.ChooseShapefileBtn.clicked.connect(self.choose_shapefile)
        self.ShapefileText = QLineEdit()
        self.ShapefileText.setText("shapefile")
        self.ShapefileDistanceLabel = QLabel()
        self.ShapefileDistanceLabel.setText("Minimum distance to shapefile:")
        self.ShapefileDistanceText = QLineEdit()
        self.ShapefileDistanceText.setFixedWidth(75)
        self.ShapefileDistanceText.setText("500")
        self.ShapefileDistanceUnitsLabel = QLabel()
        self.ShapefileDistanceUnitsLabel.setText("meters")

        # add a horizontal seperator line
        line3 = QFrame()
        line3.setFrameShape(QFrame.HLine)
        line3.setFrameShadow(QFrame.Sunken)

        # OK and Cancel buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.buttons.accepted.connect(self.sort_data)
        self.buttons.rejected.connect(self.cancel)

        # TO DO: ADD FILE COUNT TO BOTTOM OF GUI #

        # Layout
        self.widget_central = QWidget()
        self.vbox = QVBoxLayout()
        self.widget_central.setLayout(self.vbox)
        self.vbox.addWidget(self.ChoosehsicBtn)
        self.vbox.addWidget(self.hsicDirText)
        self.vbox.addWidget(self.ChooseDirOutBtn)
        self.vbox.addWidget(self.DirOutText)

        self.vbox.addSpacing(20)
        self.vbox.addWidget(line1)
        self.vbox.addWidget(self.CRhitsCheckBox)
        # widget containing Cue Report button and text
        self.widget_CR=QWidget()
        self.layout_CR = QVBoxLayout()
        self.widget_CR.setLayout(self.layout_CR)
        self.layout_CR.addWidget(self.ChooseCRBtn)
        self.layout_CR.addWidget(self.CRfileText)
        self.vbox.addWidget(self.widget_CR)

        self.vbox.addSpacing(20)
        self.vbox.addWidget(line2)
        self.vbox.addWidget(self.ShapefileCheckBox)
        # widget containing Shape File button and text
        self.widget_Shapefile=QWidget()
        self.layout_Shapefile = QVBoxLayout()
        self.widget_Shapefile.setLayout(self.layout_Shapefile)
        self.layout_Shapefile.addWidget(self.ChooseShapefileBtn)
        self.layout_Shapefile.addWidget(self.ShapefileText)
        self.layout_Shapefile.addWidget(self.ShapefileDistanceLabel)
        self.hbox = QHBoxLayout()
        self.hbox.addWidget(self.ShapefileDistanceText)
        self.hbox.addWidget(self.ShapefileDistanceUnitsLabel)
        self.layout_Shapefile.addLayout(self.hbox)
        self.vbox.addWidget(self.widget_Shapefile)

        self.vbox.addSpacing(20)
        self.vbox.addWidget(line3)
        self.vbox.addWidget(self.buttons)

        # set as central widget and dock widget
        self.setCentralWidget(self.widget_central)

        self.widget_Shapefile.setEnabled(False)
        self.widget_CR.setEnabled(False)

    def CRhitsCheckBoxChanged(self):
        if self.CRhitsCheckBox.isChecked():
            self.widget_CR.setEnabled(True)
        else:
            self.widget_CR.setEnabled(False)

    def ShapefileCheckBoxChanged(self):
        if self.ShapefileCheckBox.isChecked():
            self.widget_Shapefile.setEnabled(True)
        else:
            self.widget_Shapefile.setEnabled(False)

    def choose_hsic_dir(self):
        outputDir = QFileDialog.getExistingDirectory(self, 'Choose hsic directory.')
        if len(outputDir) == 0:
            return
        self.hsicDirText.setText(outputDir)

    def choose_output_dir(self):
        outputDir = QFileDialog.getExistingDirectory(self, 'Choose output directory.')
        if len(outputDir) == 0:
            return
        self.DirOutText.setText(outputDir)

    def choose_cue_report(self):
        fname_CR, ok = QFileDialog.getOpenFileName(self, 'Choose cue report.')
        if not ok:
            return
        self.CRfileText.setText(fname_CR)

    def choose_shapefile(self):
        fname_shapefile, ok = QFileDialog.getOpenFileName(self, 'Choose shapefile.')
        if not ok:
            return
        self.ShapefileText.setText(fname_shapefile)

    def cancel(self):
        self.close()

    def sort_data(self):
        use_cue_report = self.CRhitsCheckBox.isChecked()
        use_shapefile = self.ShapefileCheckBox.isChecked()

        # validate that a hsic directory was chosen
        if not path.isdir(self.hsicDirText.text()):
            QMessageBox.warning(self, "Warning!", "An hsic directory needs to be selected.")
            return
        # validate that a output directory was chosen
        if not path.isdir(self.DirOutText.text()):
            QMessageBox.warning(self, "Warning!", "An output directory needs to be selected.")
            return

        if use_cue_report:
            fname_cue_report = self.CRfileText.text()
            cue_report = []
            # read the cue report into a list of dictionaries
            with open(fname_cue_report) as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    cue_report.append(row)

        if use_shapefile:
            # get the base filename of the shapefile
            fname_shapefile = self.ShapefileText.text()
            if fname_shapefile[-4:] == '.shp':
                fname_shapefile_base = fname_shapefile[0:-4]
            else:
                fname_shapefile_base = fname_shapefile

            # read the shapefile
            sf = shapefile.Reader(fname_shapefile_base)


        print('sort')






if __name__ == "__main__":
    app = QApplication(argv)
    form = LWIRLOBOsorting()
    form.show()
    app.exec_()