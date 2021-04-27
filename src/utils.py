# utils.py
from pathlib import Path
import json
import os, sys
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
from classdefs import CourseItem, CONTENT_TYPES

from locations import ResourceFile, HOME

import keyring

# this is necessary to address issue where bundled app does not find keyring backend
if sys.platform == 'darwin': # macOS solution
    import keyring.backends.OS_X
    keyring.set_keyring(keyring.backends.OS_X.Keyring())
else: # Windows solution
    import keyring.backends.Windows
    keyring.set_keyring(keyring.backends.Windows.WinVaultKeyring())

class InvalidPreferences(Exception):
    pass

class Preferences(QDialog):
    """
    Holds current settings for app:
    baseurl
    token
    download location
    default content type
    """

    AUTOLOAD_FILE = HOME / '.canvasdefaults'

    CANVAS_KEY = 'canvas'
    ECHO360_KEY = 'echo360'

    def __init__(self, canvasapp):
        super().__init__(canvasapp)
        self.canvasapp = canvasapp # knows about parent

        self.current = {}
        self.messages = []

        self.build()

        candidates = self.load_from_file(self.AUTOLOAD_FILE)

        (isvalid, candidates) = self.validate(candidates)
        if all(isvalid.values()):
            self.current = candidates
            self.send_message('Preferences loaded from {} file.'.format(self.AUTOLOAD_FILE.name))
        else:
            validprefs = {k:v for (k,v) in candidates.items() if isvalid[k]}
            self.populate_fields(validprefs)
            self.run(cancellable=False)

        self.contentComboBox.currentIndexChanged.connect(self.check_content_changed)

        self.get_web_credentials(self.current)

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
        self.browseButton.setIcon(QIcon(ResourceFile('icons/folder.png')))
        self.pathLayout.addWidget(self.browseButton)
        self.mainLayout.addRow('Download Destination:', self.pathLayout)
        self.browseButton.clicked.connect(self.browse)

        self.contentComboBox = QComboBox()
        for ct in CONTENT_TYPES:
            self.contentComboBox.addItem(ct['displayname'])
        self.mainLayout.addRow('Default Content:', self.contentComboBox)

        self.saveLayout = QHBoxLayout()
        self.saveLabel = QLabel('Save validated preferences as defaults:')
        self.saveLabel.setAlignment(Qt.AlignRight)
        self.saveLayout.addWidget(self.saveLabel)
        self.saveValidated = QCheckBox()
        self.saveValidated.setTristate(False)
        self.saveLayout.addWidget(self.saveValidated)
        self.saveLayout.setStretch(0, 1)
        self.saveLayout.setStretch(1, 0)

        self.buttons = QDialogButtonBox()
        self.cancelButton = self.buttons.addButton('Cancel', QDialogButtonBox.RejectRole)
        self.okButton = self.buttons.addButton('Validate and Apply', QDialogButtonBox.AcceptRole)
        self.okButton.setFocus()

        self.buttons.accepted.connect(self.accept_if_valid)
        self.buttons.rejected.connect(self.reject)

        self.fullLayout.addLayout(self.mainLayout)
        self.fullLayout.addLayout(self.saveLayout)
        self.fullLayout.addWidget(self.buttons)

        self.setLayout(self.fullLayout)

    def send_message(self, text):
        # only set up to store one message at the moment
        self.messages = [text]

    def get_message(self):
        return self.messages.pop(0)

    def message_present(self):
        return len(self.messages) > 0

    def browse(self):
        folder = QFileDialog.getExistingDirectory(
            self, 'Select Folder', self.browse_default(), QFileDialog.ShowDirsOnly)
        if len(folder) > 0:
            self.pathField.setText(folder)

    def browse_default(self):
        current = Path(self.pathField.text())
        if current.exists() and current.is_dir() and current == current.absolute():
            return str(current)
        else:
            return str(HOME)

    def populate_fields(self, prefs):
        # note: only validated prefs should be put in here!
        # (do not include invalid ones in prefs dict)
        self.baseurlField.setText(prefs.get('baseurl', ''))
        self.tokenField.setText(prefs.get('token', ''))
        self.pathField.setText(prefs.get('downloadfolder', ''))
        self.contentComboBox.setCurrentIndex(prefs.get('defaultcontent', 0))

    def populate_with_current(self):
        # double check that current settings are valid
        (isvalid, validated) = self.validate(self.current)
        assert all(isvalid.values()) 

        self.populate_fields(validated)

    def check_content_changed(self, newindex):
        self.saveValidated.setChecked(newindex != self.current['defaultcontent'])

    def gather_fields(self):
        prefs = {
            'baseurl': self.baseurlField.text(),
            'token': self.tokenField.text(),
            'downloadfolder': self.pathField.text(),
            'defaultcontent': self.contentComboBox.currentIndex()
        }
        return prefs

    def load_from_file(self, file):
        candidates = {}

        if Path(file).is_file():
            with open(file, 'r') as fobj:
                j = json.load(fobj)

            candidates['baseurl'] = j.get('baseurl', '')
            candidates['token'] = j.get('token', '')
            candidates['downloadfolder'] = j.get('downloadfolder', '')
            candidates['defaultcontent'] = j.get('defaultcontent', 'modules')

        return candidates

    def get_web_credentials(self, prefs):
        canvas = Canvas(
            prefs['baseurl'],
            prefs['token']
        )
        profile = canvas.get_current_user().get_profile()
        self.web_credentials = {
            'canvas': keyring.get_credential(self.CANVAS_KEY, profile['login_id']),
            'echo360': keyring.get_credential(self.ECHO360_KEY, profile['primary_email'])
        }


    def load_echo_credentials(self):
        if self.ECHOCREDENTIAL_FILE.exists():
            with open(str(self.ECHOCREDENTIAL_FILE), 'r') as fileobj:
                filetext = fileobj.read()
            try:
                js = json.loads(filetext)
                if 'email' in js and 'password' in js:
                    self.echocredentials = js
                else:
                    self.echocredentials = None
            except ValueError:
                self.echocredentials = None
        else:
            self.echocredentials = None

    def save_current(self, file):
        with open(file, 'w') as fobj:
            json.dump(self.current, fobj, indent=4)

    def run(self, cancellable=True):
        self.cancelButton.setEnabled(cancellable)
        accepted = bool(self.exec_())
        self.cancelButton.setEnabled(True)
        return accepted

    def accept_if_valid(self):
        candidates = self.gather_fields()
        (isvalid, candidates) = self.validate(candidates)
        if all(isvalid.values()):
            self.current = candidates
            if self.saveValidated.isChecked():
                self.save_current(self.AUTOLOAD_FILE)
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

        trialbaseurl = candidates.get('baseurl', '')
        trialtoken = candidates.get('token', '')
        trialfolder = candidates.get('downloadfolder', '')
        trialcontent = candidates.get('defaultcontent', '')

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            c = Canvas(trialbaseurl, trialtoken)
        
        if len(w) > 0:
            valid['baseurl'] = False
        else:
            try:
                c.get_current_user()
            except ConnectionError:
                valid['baseurl'] = False
            except InvalidAccessToken:
                # valid['baseurl'] = False
                valid['token'] = False

        p = Path(trialfolder)

        if not p == p.absolute():
            valid['downloadfolder'] = False

        if not p.exists():
            valid['downloadfolder'] = False

        if not p.is_dir():
            valid['downloadfolder'] = False

        candidates['downloadfolder'] = str(p) # this should be a valid path

        tags = [c['tag'] for c in CONTENT_TYPES]

        ct = trialcontent

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

        