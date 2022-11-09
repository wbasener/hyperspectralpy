import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from spectral import *

import spectralAdv.specTools
from spectralAdv import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

def test_PYSPECTRA():
    assert spectralAdv.specTools.hex_to_rgb('#800080') is np.array((128, 0, 128))

