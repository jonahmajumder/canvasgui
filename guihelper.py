# guihelper.py
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.Qt import *

def confirm_dialog(text, title='Confirm'):
    m = QMainWindow()

    dlg = QDialog(m)
    dlg.setWindowTitle(title)

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

    m.setGeometry(
        QStyle.alignedRect(
            Qt.LeftToRight,
            Qt.AlignCenter,
            QSize(100,100),
            m.screen().geometry())
    )
    return bool(dlg.exec_())


def disp_html(htmlstr, title='HTML'):
    m = QMainWindow()

    dlg = QDialog(m)
    dlg.setWindowTitle(title)

    viewer = QTextBrowser()
    viewer.setOpenExternalLinks(True)
    viewer.setHtml(htmlstr)

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
            QSize(600,600),
            dlg.screen().geometry())
    )
    return dlg.exec_()


if __name__ == '__main__':
    app = QApplication([])
    s = """
    <p><b>This text is bold</b></p>
    <p><i>This text is italic</i></p>
    <p>This is<sub> subscript</sub> and <sup>superscript</sup></p>
    """
    disp_html(s)
    


