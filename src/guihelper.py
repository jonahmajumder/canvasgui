# guihelper.py
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.Qt import *

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

if __name__ == '__main__':
    app = QApplication([])
    text = open('docs/README.html', 'r').read()
    disp_html(text, title='Markdown')


    


