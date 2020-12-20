# utils.py
from pathlib import Path
import json
import warnings
from requests.exceptions import ConnectionError

from PyQt5.QtCore import QDateTime, QSize, QTimer
from PyQt5.QtWidgets import (QApplication, QComboBox, QDialog,
QPlainTextEdit, QDialogButtonBox, QFormLayout, QGridLayout, QHBoxLayout,
QLabel, QLineEdit, QToolButton, QPushButton, QSpinBox, QTextEdit,
QVBoxLayout, QStyle, QCheckBox, QFileDialog)
from PyQt5.Qt import Qt
from PyQt5.QtGui import QIcon

from canvasapi import Canvas
from canvasapi.exceptions import InvalidAccessToken
from classdefs import CourseItem

DOWNLOADS = Path.home() / 'Downloads'

class InvalidPreferences(Exception):
    pass

class Preferences(QDialog):
    """
    Holds current settings for app:
    baseurl
    token
    download location
    show favorites?

    """
    AUTOLOAD_FILE = 'defaults.json'

    def __init__(self, canvasapp):
        super(Preferences, self).__init__()
        self.canvasapp = canvasapp # knows about parent

        self.current = {}

        self.build()

        candidates = self.load_from_file(self.AUTOLOAD_FILE)

        (isvalid, candidates) = self.validate(candidates)
        if all(isvalid.values()):
            self.current = candidates
            print("Preferences loaded from '{}'.".format(self.AUTOLOAD_FILE))
            # print(self.current)
        else:
            validprefs = {k:v for (k,v) in candidates.items() if isvalid[k]}
            self.populate_fields(validprefs)
            self.run(cancellable=False)

    def build(self):
        self.setWindowTitle('Canvas Preferences')

        self.fullLayout = QVBoxLayout()

        self.mainLayout = QFormLayout()
        self.mainLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.mainLayout.setRowWrapPolicy(QFormLayout.WrapLongRows)

        self.baseurlField = QLineEdit()
        self.baseurlField.setPlaceholderText('https://canvas.university.edu/')
        self.mainLayout.addRow('Base URL:', self.baseurlField)

        self.tokenField = QLineEdit()
        self.mainLayout.addRow('Auth. Token:', self.tokenField)

        self.pathLayout = QHBoxLayout()
        self.pathField = QLineEdit()
        self.pathField.setPlaceholderText('Click Icon to Select')
        self.pathLayout.addWidget(self.pathField)
        self.browseButton = QPushButton()
        self.browseButton.setFocusPolicy(Qt.NoFocus)
        self.browseButton.setIcon(QIcon('icons/folder.png'))
        self.pathLayout.addWidget(self.browseButton)
        self.mainLayout.addRow('Download Destination:', self.pathLayout)
        self.browseButton.clicked.connect(self.browse)

        self.contentComboBox = QComboBox()
        for ct in CourseItem.CONTENT_TYPES:
            self.contentComboBox.addItem(ct['displayname'])
        self.mainLayout.addRow('Default Content:', self.contentComboBox)

        self.buttons = QDialogButtonBox()
        self.cancelButton = self.buttons.addButton('Cancel', QDialogButtonBox.RejectRole)
        self.okButton = self.buttons.addButton('Validate and Apply', QDialogButtonBox.AcceptRole)
        self.okButton.setFocus()

        self.buttons.accepted.connect(self.accept_if_valid)
        self.buttons.rejected.connect(self.reject)

        self.fullLayout.addLayout(self.mainLayout)
        self.fullLayout.addWidget(self.buttons)

        self.setLayout(self.fullLayout)

        self.setGeometry(
            QStyle.alignedRect(
                Qt.LeftToRight,
                Qt.AlignCenter,
                QSize(400,100),
                self.screen().geometry())
        )

    def browse(self):
        folder = QFileDialog.getExistingDirectory(
            self, 'Select Folder', str(DOWNLOADS), QFileDialog.ShowDirsOnly)
        if len(folder) > 0:
            self.pathField.setText(folder)

    def populate_fields(self, prefs):
        # note: only validated prefs should be put in here!
        # (do not include invalid ones in prefs dict)
        self.baseurlField.setText(prefs.get('baseurl', ''))
        self.tokenField.setText(prefs.get('token', ''))
        self.pathField.setText(prefs.get('downloadfolder', ''))
        self.contentComboBox.setCurrentIndex(prefs.get('defaultcontent', 0))

    def gather_fields(self):
        prefs = {
            'baseurl': self.baseurlField.text(),
            'token': self.tokenField.text(),
            'downloadfolder': self.pathField.text(),
            'defaultcontent': self.contentComboBox.currentIndex()
        }
        return prefs

    def load_from_file(self, file):
        with open(file, 'r') as fobj:
            j = json.load(fobj)

        candidates = {}
        candidates['baseurl'] = j.get('baseurl', '')
        candidates['token'] = j.get('token', '')
        candidates['downloadfolder'] = j.get('downloadfolder', '')
        candidates['defaultcontent'] = j.get('defaultcontent', 'modules')
        return candidates

    def save_current(self, file):
        with open(file, 'w') as fobj:
            json.dump(self.current)

    def run(self, cancellable=True):
        self.cancelButton.setEnabled(cancellable)
        self.exec_()
        self.cancelButton.setEnabled(True)

    def accept_if_valid(self):
        candidates = self.gather_fields()
        (isvalid, candidates) = self.validate(candidates)
        if all(isvalid.values()):
            self.current = candidates
            self.accept()
        else:
            invalid = [k for (k,v) in isvalid.items() if not v]
            self.highlight_invalid(invalid)

    def highlight_invalid(self, invalid=[]):
        if 'baseurl' in invalid:
            self.color_red_temporarily(self.baseurlField)
        if 'token' in invalid:
            self.color_red_temporarily(self.tokenField)
        if 'downloadfolder' in invalid:
            self.color_red_temporarily(self.pathField)
        if 'defaultcontent' in invalid:
            self.color_red_temporarily(self.contentComboBox)

    def color_red_temporarily(self, widget):
        widget.setStyleSheet("background-color: rgba(255,0,0,100)")
        QTimer.singleShot(400, lambda: widget.setStyleSheet(""))

    def validate(self, candidates):

        valid = {k:True for k in candidates.keys()} # start with all true

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            c = Canvas(candidates['baseurl'], candidates['token'])
        
        if len(w) > 0:
            if w[0].message.args[0] == 'An invalid `base_url` for the Canvas API Instance was used. Please provide a valid HTTP or HTTPS URL if possible.':
                valid['baseurl'] = False
        try:
            c.get_current_user()
        except ConnectionError:
            valid['baseurl'] = False
        except InvalidAccessToken:
            # valid['baseurl'] = False
            valid['token'] = False

        p = Path(candidates['downloadfolder'])

        if not p == p.absolute():
            valid['downloadfolder'] = False

        if not p.exists():
            valid['downloadfolder'] = False

        if not p.is_dir():
            valid['downloadfolder'] = False

        candidates['downloadfolder'] = str(p) # this should be a valid path

        tags = [c['tag'] for c in CourseItem.CONTENT_TYPES]

        ct = candidates['defaultcontent']

        if isinstance(ct, str):
            if ct in tags:
                ct = tags.index(ct) # was specified by tag - ok
            else:
                if ct.isnumeric():
                    if int(ct) not in range(len(tags)):
                        ct = int(ct) # was specified by string index - ok
                    else:
                        # numeric string but out of range
                        valid['defaultcontent'] = False
                else:
                    # string, but not a tag or a valid index string
                    valid['defaultcontent'] = False
        elif isinstance(ct, int):
            if ct not in range(len(tags)):
                valid['defaultcontent'] = False
        else:
            # must be either string or int
            valid['defaultcontent'] = False

        candidates['defaultcontent'] = ct

        return (valid, candidates)

if __name__ == '__main__':
    app = QApplication([])
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    p = Preferences('app')

        