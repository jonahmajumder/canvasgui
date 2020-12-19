import sys
from time import time
import webbrowser
import base64

from PyQt5.Qt import *
from PyQt5.QtGui import *

from canvasapi import Canvas
from canvasapi.exceptions import Unauthorized

from app import CanvasApp
from guihelper import disp_html
from classdefs import CourseItem, SeparatorItem, SliderHLayout
from utils import Preferences
from appcontrol import set_term_title
from secrets import BASEURL, TOKEN

# set_term_title(CanvasApp.TITLE)

app = QApplication(sys.argv)
gui = CanvasApp()

if __name__ == '__main__':
    sys.exit(app.exec_()) # block until app exits