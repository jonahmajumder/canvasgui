# guihelper.py
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.Qt import *
from PyQt5.QtCore import *

import os, sys

def confirm_dialog(text, title='Confirm', yesno=False, parent=None):

    m = parent if parent else QMainWindow() 

    dlg = QDialog(m)
    dlg.setWindowTitle(title)

    if yesno:
        buttonBox = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No)
    else:
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

    buttonBox.accepted.connect(dlg.accept)
    buttonBox.rejected.connect(dlg.reject)

    layout = QVBoxLayout()
    textLayout = QHBoxLayout()
    textLayout.addWidget(QLabel(text))
    textLayout.setAlignment(Qt.AlignCenter)
    layout.addLayout(textLayout)
    layout.addWidget(buttonBox)
    dlg.setLayout(layout)

    return bool(dlg.exec_())

def disp_html(text, title='HTML', parent=None, width=600, height=600):

    m = parent if parent else QMainWindow() 

    dlg = QDialog(m)
    dlg.setWindowTitle(title)

    viewer = QTextBrowser()
    viewer.setOpenExternalLinks(True)
    viewer.setText(text)

    buttonBox = QDialogButtonBox(QDialogButtonBox.Ok)
    buttonBox.accepted.connect(dlg.accept)

    layout = QVBoxLayout()
    layout.addWidget(viewer)
    layout.addWidget(buttonBox)
    dlg.setLayout(layout)

    dlg.setGeometry(
        QStyle.alignedRect(
            Qt.LeftToRight,
            Qt.AlignCenter,
            QSize(width,height),
            m.geometry())
    )
    return dlg.exec_()

def alert(text, title='Alert', parent=None):
    
    m = parent if parent else QMainWindow() 

    dlg = QDialog(m)
    dlg.setWindowTitle(title)

    buttonBox = QDialogButtonBox(QDialogButtonBox.Ok)
    buttonBox.accepted.connect(dlg.accept)

    layout = QVBoxLayout()
    textLayout = QHBoxLayout()
    textLayout.addWidget(QLabel(text))
    textLayout.setAlignment(Qt.AlignCenter)
    layout.addLayout(textLayout)
    layout.addWidget(buttonBox)
    dlg.setLayout(layout)

    dlg.setGeometry(
        QStyle.alignedRect(
            Qt.LeftToRight,
            Qt.AlignCenter,
            QSize(100,100),
            m.geometry())
    )
    return dlg.exec_()

class StreamThread(QThread):
    chunk_done = pyqtSignal(int)
    finished = pyqtSignal()
    aborted = pyqtSignal()

    def __init__(self, request, filepath):
        self.request = request
        self.filepath = filepath
        self.abortRequested = False

        super().__init__()

    @pyqtSlot()
    def abort(self):
        self.abortRequested = True

    def run(self):
        total_bytes = int(self.request.headers['content-length'])
        # print(total_bytes)
        current_bytes = 0

        fileobj = open(str(self.filepath), 'wb')

        for chunk in self.request.iter_content(chunk_size=2**14):
            current_bytes += len(chunk)
            fileobj.write(chunk)
            pct_done = 100 * current_bytes / total_bytes
            # print(pct_done)
            self.chunk_done.emit(int(pct_done))

            if self.abortRequested:
                fileobj.close()
                os.remove(str(self.filepath))
                self.aborted.emit()
                return

        fileobj.close()
        self.finished.emit()
        return

class DownloadDialog(QDialog):
    def __init__(self, *args, **kwargs):
        self.filepath = kwargs.pop('filepath')
        self.request = kwargs.pop('request')

        super().__init__(*args, **kwargs)

        self.setupUI()
        self.initThread()

        self.setAttribute(Qt.WA_DeleteOnClose)
        # self.show()

    def setupUI(self):
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Abort)
        self.mainlayout = QVBoxLayout()

        self.captionLayout = QHBoxLayout()
        self.captionLabel = QLabel('Downloading {} ...'.format(self.filepath.name))
        self.captionLayout.addWidget(self.captionLabel)
        self.captionLayout.setAlignment(Qt.AlignCenter)

        self.pctLayout = QHBoxLayout()
        self.pctLabel = QLabel('')
        self.pctLayout.addWidget(self.pctLabel)
        self.pctLayout.setAlignment(Qt.AlignCenter)

        self.progbar = QProgressBar()
        self.progbar.setTextVisible(True) # ignored with macOS styling
        self.progbar.valueChanged.connect(lambda val: self.pctLabel.setText('{}%'.format(val)))
        self.progbar.setValue(0)

        self.progLayout = QHBoxLayout()
        self.progLayout.addWidget(self.progbar)
        self.progLayout.addLayout(self.pctLayout)
        self.progLayout.setStretch(0, 4)
        self.progLayout.setStretch(1, 1)

        self.mainlayout.addLayout(self.captionLayout)
        self.mainlayout.addLayout(self.progLayout)
        self.mainlayout.addWidget(self.buttonBox)
        self.setLayout(self.mainlayout)

        self.setGeometry(
        QStyle.alignedRect(
            Qt.LeftToRight,
            Qt.AlignCenter,
            QSize(200,100),
            self.screen().geometry())
        )

    def initThread(self):
        self.thread = StreamThread(self.request, self.filepath)

        self.buttonBox.rejected.connect(self.thread.abort)
        self.thread.chunk_done.connect(self.progbar.setValue)
        self.thread.aborted.connect(self.reject)
        self.thread.finished.connect(self.accept)

    def showEvent(self, *args):
        # called when dialog is shown
        self.thread.start()
        return super().showEvent(*args)

def test_dispatch():
    pass

if __name__ == '__main__':
    app = QApplication(sys.argv)

    m = QMainWindow()

    import requests
    from pathlib import Path
    size_mb = 10
    source = 'http://ipv4.download.thinkbroadband.com/{}MB.zip'.format(size_mb)
    dest = Path('/Users/jonahmajumder/Downloads/{}MB_requests.txt'.format(size_mb))
    req = requests.get(source, stream=True)

    d = DownloadDialog(m, filepath=dest, request=req)

    d.accepted.connect(lambda: print('done!'))
    d.rejected.connect(lambda: print('canceled!'))
    d.show()


    


