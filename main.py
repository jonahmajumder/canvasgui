import sys

from PyQt5.Qt import QApplication

from app import CanvasApp

# set_term_title(CanvasApp.TITLE)

app = QApplication(sys.argv)
gui = CanvasApp()

if __name__ == '__main__':
    sys.exit(app.exec_()) # block until qapp instance exits