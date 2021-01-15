import sys
from time import time
import webbrowser
import base64

from json.decoder import JSONDecodeError

import threading

from urllib import parse

from PyQt5.Qt import *
from PyQt5.QtGui import *

from canvasapi import Canvas
from canvasapi.exceptions import Unauthorized

from guihelper import disp_html
from login import auth_canvas_session, auth_echo_session
from classdefs import (
    CanvasItem, CourseItem, CONTENT_TYPES,
    CustomProxyModel, CustomStyledItemDelegate, CustomComboBox, CustomPushButton
)
from classdefs import SliderHLayout, CheckableComboBox
from utils import Preferences

from locations import ResourceFile

class CanvasApp(QMainWindow):
    SIZE = (800, 600)
    TITLE = 'Canvas Browser'

    def __init__(self, *args, **kwargs):
        super(QMainWindow, self).__init__(*args, **kwargs)

        # establish easy reference to running QApplication
        self.app = QApplication.instance()

        self.app.setAttribute(Qt.AA_UseHighDpiPixmaps)
        # self.app.setWindowIcon(QIcon(ResourceFile('icons/icon.icns')))

        self.setWindowTitle(self.TITLE)

        self.preferences = Preferences(self)

        if len(self.preferences.current) == 0:
            # this means no preferences (user closed pref window)
            sys.exit()

        self.init_api()

        # use credentials to do logins
        # self.authenticate_session()
        threading.Thread(target=self.authenticate_session).start()

        self.build()

        if self.preferences.message_present():
            self.print(self.preferences.get_message(), 0)

        #populate courses after loading
        threading.Thread(target=self.add_courses).start()

        self.connect_signals()

        # self.tree.sortByColumn(1, Qt.DescendingOrder) # most recent at top

        self.show()
        
        self.center_on_screen()

        self.print('Welcome, {}!'.format(self.user.get_profile()['name']),  append=True)


    def auth_get(self, url):
        return self.canvas._Canvas__requester.request('GET', _url=url)

# -------------------- INITIALIZATION METHODS --------------------

    def init_api(self):
        self.canvas = Canvas(
            self.preferences.current['baseurl'],
            self.preferences.current['token']
        )
        self.user = self.canvas.get_current_user()
        self.terms = self.unique_terms()

    def authenticate_session(self):
        if self.preferences.web_credentials['canvas'] is not None:
            auth_canvas_session(
                self.preferences.web_credentials['canvas'],
                self.preferences.current['baseurl'],
                self.canvas._Canvas__requester._session
            )
            testurl = parse.urlunsplit(parse.urlsplit(self.preferences.current['baseurl'])._replace(path=''))
            try:
                r = self.auth_get(testurl)
                if r.ok:
                    self.CANVAS_AUTHENTICATED = True
                else:
                    self.CANVAS_AUTHENTICATED = False
            except:
                self.CANVAS_AUTHENTICATED = False
        else:
            self.CANVAS_AUTHENTICATED = False


        if self.preferences.web_credentials['echo360'] is not None:
            auth_echo_session(
                self.preferences.web_credentials['echo360'],
                self.canvas._Canvas__requester._session
            )
            try: # url returns json only if authenticated
                self.auth_get('https://echo360.org/user/enrollments').json()
                self.ECHO_AUTHENTICATED = True
            except:
                self.ECHO_AUTHENTICATED = False
        else:
            self.ECHO_AUTHENTICATED = False

    def build(self):

        self.contentTypeComboBox = CustomComboBox()
        for ct in CONTENT_TYPES:
            self.contentTypeComboBox.addItem(ct['displayname'])

        self.contentTypeComboBox.toolTipString = \
            lambda: 'Change course display (currently showing {})'.format(self.contentTypeComboBox.currentText().lower())

        # use preferences to set content type combo box
        self.contentTypeComboBox.setCurrentIndex(self.preferences.current['defaultcontent'])

        self.contentTypeLayout = QHBoxLayout()
        self.contentTypeLayout.addItem(QSpacerItem(20,40))
        self.contentTypeLayout.addWidget(self.contentTypeComboBox)
        self.contentTypeLayout.addItem(QSpacerItem(20,40))
        self.contentTypeLayout.setStretch(0, 1)
        self.contentTypeLayout.setStretch(1, 2)
        self.contentTypeLayout.setStretch(2, 1)

        self.expandButton = CustomPushButton('Expand All')
        self.expandButton.toolTipString = \
            lambda: 'Expand selected items' if len(self.selected_canvasitems()) > 0 else 'Expand all items'

        self.expandLayout = QHBoxLayout()
        self.expandLayout.addItem(QSpacerItem(20,40))
        self.expandLayout.addWidget(self.expandButton)
        self.expandLayout.addItem(QSpacerItem(20,40))
        self.expandLayout.setStretch(0, 1)
        self.expandLayout.setStretch(1, 1)
        self.expandLayout.setStretch(2, 1)

        self.mainLayout = QVBoxLayout()

        self.controlLayout = QHBoxLayout()
        self.controlLayout.addLayout(self.contentTypeLayout)
        self.controlLayout.addLayout(self.expandLayout)
        self.controlLayout.setStretch(0, 1)
        self.controlLayout.setStretch(1, 1)
        self.controlGroup = QGroupBox()
        self.controlGroup.setTitle('Application Settings')
        self.controlGroup.setLayout(self.controlLayout)

        self.favoriteSlider = SliderHLayout('All Courses', 'Favorites', startVal=True)
        self.favoriteSlider.slider.toolTipString = \
            lambda: 'Show all courses' if self.favoriteSlider.value() else 'Show only favorite courses'

        self.termComboBox = CheckableComboBox('Select Semester(s)')
        for t in self.terms:
            self.termComboBox.addItem(t['name'], True, t['id'])

        self.termLayout = QHBoxLayout()
        self.termLayout.addItem(QSpacerItem(20,40))
        self.termLayout.addWidget(self.termComboBox)
        self.termLayout.addItem(QSpacerItem(20,40))
        self.termLayout.setStretch(0, 1)
        self.termLayout.setStretch(1, 2)
        self.termLayout.setStretch(2, 1)

        self.filterLayout = QHBoxLayout()
        self.filterLayout.addLayout(self.favoriteSlider)
        self.filterLayout.addLayout(self.termLayout)
        self.filterLayout.setStretch(0, 1)
        self.filterLayout.setStretch(1, 1)

        # this is the layout that holds course filters and course treeview
        self.courseLayout = QVBoxLayout()
        self.courseLayout.addLayout(self.filterLayout)

        self.tree = QTreeView()
        self.model = QStandardItemModel(0, 2, self)
        self.modelroot = self.model.invisibleRootItem()

        self.proxyModel = CustomProxyModel(self.model,
            favorites_initial=self.favoriteSlider.value(),
            content_initial=self.contentTypeComboBox.currentIndex(),
            terms=self.terms
            )
        self.proxyModel.setSourceModel(self.model)
        self.model.setHorizontalHeaderLabels(['Course', 'Date Created'])
        self.tree.setAlternatingRowColors(True)
        self.tree.setSortingEnabled(True)
        self.tree.setEditTriggers(QTreeView.NoEditTriggers)
        self.tree.setModel(self.proxyModel)
        self.tree.header().setSortIndicator(1, Qt.DescendingOrder)
        self.tree.setSelectionMode(QTreeView.ExtendedSelection)

        self.tree.header().setSectionResizeMode(QHeaderView.Interactive)
        w = self.tree.geometry().width()
        self.tree.header().resizeSection(0, int(w*2/3))
        self.tree.header().resizeSection(1, int(w/3))

        self.courseLayout.addWidget(self.tree)

        self.mainGroup = QGroupBox()
        self.mainGroup.setTitle('Courses')
        self.mainGroup.setLayout(self.courseLayout)

        self.mainLayout.addWidget(self.controlGroup)
        self.mainLayout.addWidget(self.mainGroup)

        self.central = QWidget()
        self.central.setLayout(self.mainLayout)
        self.setCentralWidget(self.central)

        self.statusBar()

        self.bar = self.menuBar()
        self.file = self.bar.addMenu('Info')
        self.file.addAction('Preferences', self.edit_preferences)
        self.file.addAction('Show User Profile', self.show_user, QKeySequence('Ctrl+U'))
        self.file.addAction('Show Help', self.show_readme, QKeySequence('Ctrl+Shift+H'))


    def center_on_screen(self):
        self.setGeometry(
            QStyle.alignedRect(
                Qt.LeftToRight,
                Qt.AlignCenter,
                QSize(*self.SIZE),
                self.screen().geometry() # rectangle to center to
            )
        )

    def connect_signals(self):
        self.tree.doubleClicked.connect(self.tree_double_click)

        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.tree_right_click)

        self.model.itemChanged.connect(lambda item: item.itemChangeFcn())

        self.expandButton.clicked.connect(self.expand_all)
        self.contentTypeComboBox.currentIndexChanged.connect(self.proxyModel.contentTypeChanged)
        self.favoriteSlider.valueChanged.connect(self.proxyModel.only_favorites_changed)
        self.termComboBox.selectionsChanged.connect(self.proxyModel.terms_changed)

    def tree_double_click(self, proxyindex):
        # sourceindex = self.proxyModel.mapToSource(proxyindex)
        for item in self.selected_canvasitems():
            item.dblClickFcn(contentTypeIndex=self.contentTypeComboBox.currentIndex())

    def tree_right_click(self, point):
        sourceindex = self.proxyModel.mapToSource(self.tree.indexAt(point))
        item = self.model.itemFromIndex(sourceindex)
        item.run_context_menu(self.tree.viewport().mapToGlobal(point))

        # for item in self.selected_canvasitems():
        #     item.run_context_menu(self.tree.viewport().mapToGlobal(point))

    def selected_canvasitems(self):
        proxyindexes = self.tree.selectedIndexes()
        sourceindexes = [self.proxyModel.mapToSource(i) for i in proxyindexes]
        items = [self.model.itemFromIndex(i) for i in sourceindexes]
        canvasitems = [i for i in items if i.column() == 0]
        return canvasitems

    def selected_canvasitem(self):
        return self.selected_canvasitems()[0]

# -------------------- FUNCTIONAL METHODS --------------------

    def print(self, text, timeout=0, **kwargs): # default: stay there until replaced
        append = kwargs.get('append', False)
        if append:
            current = self.statusBar().currentMessage()
            self.statusBar().showMessage(' '.join([current, text]), timeout)
        else:
            self.statusBar().showMessage(text, timeout)

    def unique_terms(self):
        all_terms = [c.term for c in self.canvas.get_courses(include='term')]
        unique_terms = []
        for t in all_terms:
            if t not in unique_terms:
                unique_terms.append(t)
        unique_terms.sort(key=lambda t: t['id'], reverse=True)
        unique_terms[-1]['name'] = 'No Term' # change name of item with id = 1
        return unique_terms

    def synchronize_terms_to_gui(self):
        # assume self.terms has been updated
        gui_ids = [item.data(self.termComboBox.TagDataRole) for item in self.termComboBox.children()]
        term_ids = [t['id'] for t in self.terms]

        missing_terms = [t for (ti, t) in zip(term_ids, self.terms) if ti not in gui_ids]
        extra_items = [ch for (gi, ch) in zip(gui_ids, self.termComboBox.children()) if gi not in term_ids]

        for item in extra_items:
            self.termComboBox.model.removeRow(item.row())

        for term in missing_terms:
            self.termComboBox.addItem(term['name'], True, term['id'])

        # update GUI filtering in case it should change
        self.proxyModel.terms = self.terms
        self.termComboBox.selectionChangedFcn(None)

    def add_courses(self):
        courses = list(self.canvas.get_courses(include=['term', 'favorites']))
        numcourses = len(courses)
        nicknames = [self.canvas.get_course_nickname(course.id) for course in courses]
        classtypes = [d['subclass'] for d in CONTENT_TYPES]

        for classtype in classtypes:
            for (i, course, nickname) in zip(range(numcourses), courses, nicknames):
                fcn = lambda: self.make_and_add_courseitem(course, nickname, classtype)
                threading.Thread(target=fcn).start()

    def make_and_add_courseitem(self, course, nickname, classtype):
        item = classtype(object=course, gui=self, nickname=nickname)
        self.modelroot.appendRow([item, item.date])

    def reset_courses(self):
        self.model.removeRows(0, self.model.rowCount())
        self.add_courses()

    def expand_all(self):

        selected = self.selected_canvasitems()

        if len(selected) > 0:
            to_expand = selected
        else: # all top level items (i.e. courses)
            to_expand = [self.model.invisibleRootItem().child(i, 0) for i in range(self.model.rowCount())]

        for item in to_expand:
            item.expand_recursive()

    def generate_profile_html(self):
        data = self.user.get_profile()

        html = '<div align="center">'
        if 'name' in data:
            html += '<h1>{}</h1>'.format(data['name'])     
        if 'avatar_url' in data:
            img_content = self.auth_get(data['avatar_url']).content
            img_data_uri = base64.b64encode(img_content).decode('utf-8')
            html += '<br><img src="data:image/png;base64,{}">'.format(img_data_uri)
        if 'primary_email' in data:
            html += '<h4>Email: {}</h3>'.format(data['primary_email'])
        if 'login_id' in data:
            html += '<h4>Login: {}</h3>'.format(data['login_id'])
        if 'bio' in data:
            html += '<p>{}</p>'.format(data['bio'])

        auths = [self.CANVAS_AUTHENTICATED, self.ECHO_AUTHENTICATED]

        if any(auths):
            html += '<h3>Web Credentials (from Keychain)</h3>'
            for auth, (name, cred) in zip(auths, self.preferences.web_credentials.items()):
                if auth:
                    html += '<p>'
                    html += 'Keychain Item Name: {}<br/>'.format(name)
                    html += 'Account Name: {}<br/>'.format(cred.username)
                    html += 'Password: *********<br/>'
                    html += '</p>'

        html += '</div>'

        return html

# -------------------- MENU ACTION METHODS --------------------

    def show_user(self):
        htmlstr = self.generate_profile_html()
        disp_html(htmlstr, title='Current User', parent=self)

    def show_readme(self):
        with open(ResourceFile('docs/README.html'),'r') as file:
            htmlstr = file.read()
        disp_html(htmlstr, title='Help', parent=self, width=700, height=700)

    def edit_preferences(self):
        self.preferences.populate_with_current()
        oldprefs = self.preferences.current
        accepted = self.preferences.run()

        if accepted and self.preferences.current != oldprefs:
            self.print('Application preferences changed.')
            self.init_api() # reset canvasapi instance
            self.synchronize_terms_to_gui() # account for potentially new set of course terms
            self.reset_courses() # trigger repopulation of classes

