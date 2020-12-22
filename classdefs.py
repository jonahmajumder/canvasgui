import sys
from time import time
import json
import os
from pathlib import Path
import webbrowser
import pytz
from dateutil.parser import isoparse
from datetime import datetime

from PyQt5.Qt import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from bs4 import BeautifulSoup
from urllib import parse

from canvasapi import Canvas
from canvasapi.exceptions import Unauthorized
from appcontrol import convert, CONVERTIBLE_EXTENSIONS
from guihelper import disp_html, confirm_dialog

DOWNLOADS = Path.home() / 'Downloads'

SORTROLE = 256

class SeparatorItem(QStandardItem):
    """
    class to serve as divider (no functionality)
    """
    def __init__(self, *args, **kwargs):
        super(SeparatorItem, self).__init__(*args, **kwargs)

        self.setFlags(Qt.NoItemFlags)

        # self.setBackground(0, QBrush(QColor('black')))
        # self.setBackground(1, QBrush(QColor('black')))

    def dblClickFcn(self):
        pass


class CanvasItem(QStandardItem):
    """
    general parent class for tree elements with corresponding canvasapi objects
    (not intended to be instantiated directly)
    """
    CONTEXT_MENU_ACTIONS = []

    def __init__(self, *args, **kwargs):
        self.obj = kwargs.pop('object', None)
        super(CanvasItem, self).__init__(*args, **kwargs)
        # super(DoubleClickHandler, self).__init__()
        # print(repr(self.obj))
        if hasattr(self.obj, 'name'):
            self.name = self.obj.name
        elif hasattr(self.obj, 'title'):
            self.name = self.obj.title
        elif hasattr(self.obj, 'display_name'):
            self.name = self.obj.display_name
        elif hasattr(self.obj, 'label'):
            self.name = self.obj.label
        else:
            self.name = str(self.obj)

        self.setText(self.name)
        self.setData(self.name, SORTROLE)

        self.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        self.date = Date(item=self)

        # self.setText(1, format_date(self.created))
        # self.setText(1, self.date.smart_formatted())
        # self.setData(1, Qt.InitialSortOrderRole, self.date.as_qdt())

    def auth_get(self, url):
        return self.obj._requester.request('GET', _url=url)

    def identifier(self):
        if isinstance(self, PageItem):
            return self.obj.page_id
        else:
            return self.obj.id

    def __eq__(self, other):
        return (self.identifier() == other.identifier())

    def append_dated_item(self, item):
        children = [self.child(r, 0) for r in range(self.rowCount())]
        if not item in children:
            self.appendRow([item, item.date])

    def dblClickFcn(self, **kwargs):
        pass

    def expand(self, **kwargs):
        pass

    def course(self):
        if self.parent() is None:
            return self
        else:
            return self.parent().course()

    def safe_get_folders(self, folder=None):
        parent = folder if folder else self.obj
        try:
            folders = list(parent.get_folders())
        except Unauthorized:
            print('Unauthorized!')
            folders = []
        return folders

    def safe_get_files(self, folder=None):
        parent = folder if folder else self.obj
        try:
            files = list(parent.get_files())
        except Unauthorized:
            print('Unauthorized!')
            files = []
        return files

    @staticmethod
    def get_html_links(html):
        linkdict = {}
        soup = BeautifulSoup(html, 'html.parser')
        links = soup.find_all('a')
        classes = [l.attrs.get('class', []) for l in links]
        rettypes = [l.attrs.get('data-api-returntype', '') for l in links]
        for (l, r) in zip(links, rettypes):
            if len(r) > 0:
                if not json.loads(l.attrs.get('aria-hidden', 'false')):
                    if r not in linkdict:
                        linkdict[r] = []
                    linkdict[r].append(l)
        return linkdict

    def children_from_html(self, html, **kwargs):
        '''
        general method to be used by any element that contains html
        creates children for linked files, pages, etc.
        '''
        advance = kwargs.get('advance', True)

        if html is not None:
            links = self.get_html_links(html)
            # print(self.text(0))
            # print('Link types: ' + str(list(links.keys())))
            # print('')
            files = links.get('File', [])
            pages = links.get('Page', [])
            quizzes = links.get('Quiz', [])
            assignments = links.get('Assignment', [])

            # for a in sum(links.values(), []):
            #     info = self.parse_api_url(a.attrs['data-api-endpoint'])

            for a in files:
                info = self.parse_api_url(a.attrs['data-api-endpoint'])
                file = self.course().safe_get_item('get_file', info['files'])
                if file:
                    item = FileItem(object=file)
                    self.append_dated_item(item)
            for a in pages:
                info = self.parse_api_url(a.attrs['data-api-endpoint'])
                page = self.course().safe_get_item('get_page', info['pages'])
                if page:
                    item = PageItem(object=page)
                    self.append_dated_item(item)
            for a in quizzes:
                info = self.parse_api_url(a.attrs['data-api-endpoint'])
                quiz = self.course().safe_get_item('get_quiz', info['quizzes'])
                if quiz:
                    item = QuizItem(object=quiz)
                    self.append_dated_item(item)
            for a in assignments:
                info = self.parse_api_url(a.attrs['data-api-endpoint'])
                assignment = self.course().safe_get_item('get_assignment', info['assignments'])
                if assignment:
                    item = AssignmentItem(object=assignment)
                    self.append_dated_item(item)
            if not sum(links.values(), []):
                print('No links found.')
        else:
            print('HTML is None.')

    def retrieve_sessionless_url(self):
        if hasattr(self.obj, 'url'):
            d = self.auth_get(self.obj.url)
            pagetype = d.headers['content-type'].split(';')[0]
            if pagetype == 'application/json':
                if 'url' in d.json():
                    return d.json()['url']

        return None

    @staticmethod
    def parse_api_url(apiurl):
        pathstr = parse.urlsplit(apiurl).path.strip(os.sep)
        parts = Path(pathstr).parts
        if not len(parts) % 2:
            info = {k:v for (k,v) in zip(parts[::2], parts[1::2])}
        else:
            raise Exception('Odd number of path elements to parse ({})'.format(pathstr))
        return info

    @staticmethod
    def open_and_notify(url):
        print('Opening linked url:\n{}'.format(url))
        webbrowser.open(url)

class CourseItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "course" objects
    """
    CONTENT_TYPES = [
        {'tag': 'modules', 'displayname': 'Modules'},
        {'tag': 'files', 'displayname': 'Filesystem'},
        {'tag': 'assignments', 'displayname': 'Assignments'},
        {'tag': 'tools', 'displayname': 'External Tools'}
    ]

    def __init__(self, *args, **kwargs):
        self.expanders = [
            self.get_modules,
            self.get_filesystem,
            self.get_assignments,
            self.get_tools
        ]

        self.content = kwargs.pop('content', 'files')
        self.downloadfolder = kwargs.pop('downloadfolder', DOWNLOADS)
        self.isfavorite = kwargs.pop('favorite', False)

        super(CourseItem, self).__init__(*args, **kwargs)

        self.setIcon(QIcon('icons/book.png'))

    def expand(self, **kwargs):
        contentTypeIndex = kwargs.get('contentTypeIndex', 0)
        self.expanders[contentTypeIndex]()

    def dblClickFcn(self, **kwargs):
        self.expand(**kwargs)

    def get_modules(self):
        ct = 0
        for m in self.obj.get_modules():
            item = ModuleItem(object=m)
            self.append_dated_item(item)
            ct += 1
        if ct == 0:
            self.setEnabled(False) # if module is empty

    def get_root_folder(self):
        all_folders = self.obj.get_folders()
        first_levels = [f for f in all_folders if len(Path(f.full_name).parents) == 1]
        assert len(first_levels) == 1
        return first_levels[0]

    def get_filesystem(self):
        root = self.get_root_folder()

        files = self.safe_get_files(root)
        folders = self.safe_get_folders(root)

        if len(files + folders) > 0:
            for file in files:
                item = FileItem(object=file)
                self.append_dated_item(item)
            
            for folder in folders:
                item = FolderItem(object=folder)
                self.append_dated_item(item)
        else:
            self.setEnabled(False)

    def get_assignments(self):
        for a in self.obj.get_assignments():
            item = AssignmentItem(object=a)
            self.append_dated_item(item)

    def get_tools(self):
        tabs = [t for t in self.obj.get_tabs() if t.type == 'external']
        for t in tabs:
            item = TabItem(object=t)
            self.append_dated_item(item)

    def safe_get_item(self, method, id):
        try:
            return getattr(self.obj, method)(id)
        except Unauthorized:
            print('Unauthorized!')
            return None

class ExternalToolItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "externaltool" objects
    note: this is not great because some tools are inaccessible as these types of objects
    """
    def __init__(self, *args, **kwargs):
        super(ExternalToolItem, self).__init__(*args, **kwargs)

        self.setIcon(QIcon('icons/link.png'))

    def dblClickFcn(self, **kwargs):
        self.open(**kwargs)

    def open(self, **kwargs):
        if 'url' in self.obj.custom_fields:
            self.open_and_notify(self.obj.custom_fields['url'])
        else:
            print('No external url found!')
            # print('')
            # print(repr(self.obj))

class TabItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "tab" objects
    note: represents similar information to externaltools but preferable
    because all are "accessible"
    """
    def __init__(self, *args, **kwargs):
        super(TabItem, self).__init__(*args, **kwargs)

        self.setIcon(QIcon('icons/link.png'))

    def open(self, **kwargs):
        u = self.retrieve_sessionless_url()
        if u is not None:
            self.open_and_notify(u)
        else:
            print('No external url found!')
            # print('')
            # print(repr(self.obj))

    def dblClickFcn(self, **kwargs):
        self.open(**kwargs)

class ModuleItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "module" objects
    """
    def __init__(self, *args, **kwargs):
        super(ModuleItem, self).__init__(*args, **kwargs)

        self.setIcon(QIcon('icons/module.png'))

    def expand(self, **kwargs):
        items = list(self.obj.get_module_items())
        for mi in items:
            if mi.type == 'SubHeader':
                pass
            elif mi.type == 'File':
                file = self.course().safe_get_item('get_file', mi.content_id)
                if file:
                    item = FileItem(object=file)
                    self.append_dated_item(item)
            elif mi.type == 'Page':
                page = self.course().safe_get_item('get_page', mi.page_url)
                if page:
                    item = PageItem(object=page)
                    self.append_dated_item(item)
            elif mi.type == 'Discussion':
                disc = self.course().safe_get_item('get_discussion_topic', mi.content_id)
                if disc:
                    item = DiscussionItem(object=disc)
                    self.append_dated_item(item)
            elif mi.type == 'Quiz':
                quiz = self.course().safe_get_item('get_quiz', mi.content_id)
                if quiz:
                    item = QuizItem(object=quiz)
                    self.append_dated_item(item)
            elif mi.type == 'Assignment':
                assignment = self.course().safe_get_item('get_assignment', mi.content_id)
                if assignment:
                    item = AssignmentItem(object=assignment)
                    self.append_dated_item(item)
            else:
                # print(repr(mi))
                item = ModuleItemItem(object=mi)
                self.append_dated_item(item)

        if len(items) == 0:
            self.setEnabled(False)

    def dblClickFcn(self, **kwargs):
        self.expand(**kwargs)

class ModuleItemItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "moduleitem" objects
    this class should only be instantiated when an "unknown" type is encountered
    """
    def __init__(self, *args, **kwargs):
        super(ModuleItemItem, self).__init__(*args, **kwargs)

        self.setIcon(QIcon('icons/link.png'))

    def open(self, **kwargs):
        if hasattr(self.obj, 'html_url'):
            self.open_and_notify(self.obj.html_url)
        else:
            print('No html_url to open.')

    def dblClickFcn(self, **kwargs):
        self.open(**kwargs)

class FolderItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "folder" objects
    """
    def __init__(self, *args, **kwargs):
        super(FolderItem, self).__init__(*args, **kwargs)

        self.setIcon(QIcon('icons/folder.png'))

    def expand(self, **kwargs):
        for file in self.safe_get_files():
            item = FileItem(object=file)
            self.append_dated_item(item)

        for folder in self.safe_get_folders():
            item = FolderItem(object=folder)
            self.append_dated_item(item)

    def dblClickFcn(self, **kwargs):
        self.expand(**kwargs)

    def download(self, **kwargs):
        # expand all-- does that need to be a CanvasItem method?

        # create folder in download location
        # download all files into new folder
        # call this function recursively on all folders
        # (this function will need a param for folder)

        pass


class FileItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "file" objects (within folders)
    """
    def __init__(self, *args, **kwargs):
        super(FileItem, self).__init__(*args, **kwargs)

        self.setIcon(QIcon('icons/file.png'))

    # this is a faster version of the CanvasAPI's download method (not sure why...)
    def save_data(self, filepath):
        r = self.auth_get(self.obj.url)
        with open(filepath, 'wb') as fileobj:
            fileobj.write(r.content)

    def download(self):
        if confirm_dialog('Download {}?'.format(self.obj.filename), title='Confirm Download'):
            filename = parse.unquote(self.obj.filename)
            newpath = Path(self.course().downloadfolder) / filename # build local file Path obj
            if not newpath.exists():
                self.save_data(str(newpath))
                print('{} downloaded.'.format(filename))
            else:
                print('{} already exists here; file not replaced.'.format(filename))

        if newpath.suffix in CONVERTIBLE_EXTENSIONS:
            if confirm_dialog('Convert {} to PDF?'.format(filename), title='Convert File'):
                convert(newpath)
                os.remove(newpath)

    def dblClickFcn(self, **kwargs):
        self.download()

class PageItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "page" objects
    """
    def __init__(self, *args, **kwargs):
        super(PageItem, self).__init__(*args, **kwargs)

        self.setIcon(QIcon('icons/html.png'))

    def expand(self, **kwargs):
        self.children_from_html(self.obj.body, **kwargs)

    def dblClickFcn(self, **kwargs):
        self.expand(**kwargs)

    def open(self, **kwargs):
        if self.obj.body:
            disp_html(self.obj.body, title=self.text(0))
        else:
            print('No content on page.')

class QuizItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "quiz" objects
    """
    def __init__(self, *args, **kwargs):
        super(QuizItem, self).__init__(*args, **kwargs)

        self.setIcon(QIcon('icons/quiz.png'))

    def open(self, **kwargs):
        self.open_and_notify(self.obj.html_url)

    def dblClickFcn(self, **kwargs):
        self.open(**kwargs)

class DiscussionItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "discussiontopic" objects
    """
    def __init__(self, *args, **kwargs):
        super(DiscussionItem, self).__init__(*args, **kwargs)

        self.setIcon(QIcon('icons/discussion.png'))

    def expand(self, **kwargs):
        self.children_from_html(self.obj.message, **kwargs)

    def dblClickFcn(self, **kwargs):
        self.expand(**kwargs)

    def open(self, **kwargs):
        disp_html(self.obj.message, title=self.text(0))

class AssignmentItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "assigment" objects
    """
    def __init__(self, *args, **kwargs):
        super(AssignmentItem, self).__init__(*args, **kwargs)

        self.setIcon(QIcon('icons/assignment.png'))

    def expand(self, **kwargs):
        self.children_from_html(self.obj.description, **kwargs)

    def dblClickFcn(self, **kwargs):
        self.expand(**kwargs)

    def open(self, **kwargs):
        if hasattr(self.obj, 'url'):
            u = self.retrieve_sessionless_url()
            if u is not None:
                self.open_and_notify(u)
            else:
                self.open_and_notify(self.obj.url)
        else:
            self.open_and_notify(self.obj.html_url)

# ----------------------------------------------------------------------

class Date(QStandardItem):
    """docstring for Date"""
    TIMEZONE = pytz.timezone('America/New_York')

    def __init__(self, *args, **kwargs):
        self.item = kwargs.pop('item')
        self.obj = self.item.obj
        super(Date, self).__init__(*args, **kwargs)
        self.datetime = self.datetime_from_obj()

        self.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        self.setData(self.as_qdt(), SORTROLE)

        self.setText(self.smart_formatted())

    @staticmethod
    def hasattr_not_none(obj, attr):
    # check if has attr and also if that attr is not-None
        if hasattr(obj, attr):
            if getattr(obj, attr) is not None:
                return True
            else:
                return False
        else:
            return False

    def parse_datestr(self):
        if self.hasattr_not_none(self.obj, 'created_at'):
            return self.obj.created_at
        elif self.hasattr_not_none(self.obj, 'completed_at'):
            return self.obj.completed_at
        elif self.hasattr_not_none(self.obj, 'unlock_at'):
            return self.obj.unlock_at
        elif self.hasattr_not_none(self.obj, 'due_at'):
            return self.obj.due_at
        elif self.hasattr_not_none(self.obj, 'url'): # do this one last because can't try another after
            jsdata = self.item.auth_get(self.obj.url).json()
            if 'created_at' in jsdata:
                return jsdata['created_at']
            else:
                return None
        else:
            print('No date found for {}.'.format(str(self.obj)))
            return None

    def datetime_from_obj(self):
        s = self.parse_datestr()
        if s is not None:
            # make datetime (which will be in UTC timc) and convert to EST
            return isoparse(s).astimezone(self.TIMEZONE)
        else:
            return None

    def smart_formatted(self):
        if self.datetime is not None:
            days_ago = (datetime.now().astimezone(self.TIMEZONE).date() - self.datetime.date()).days
            if days_ago == 0:
                daystring = 'Today'
            elif days_ago == 1:
                daystring = 'Yesterday'
            else:
                daystring = self.datetime.strftime('%b %-d, %Y')
            timestring = self.datetime.strftime('%-I:%M %p')
            return '{0} at {1}'.format(daystring, timestring)
        else:
            return ''

    # def __lt__(self, other):
    #     return self.datetime.timestamp() < other.datetime.timestamp()

    def as_qdt(self):
        if self.datetime is not None:
            secs = self.datetime.timestamp() # seconds since epoch
            return QDateTime.fromSecsSinceEpoch(secs)
        else:
            return None

# ----------------------------------------------------------------------

class CustomProxyModel(QSortFilterProxyModel):
    """
    this subclass implements filtering and sorting functions for the app
    """

    def __init__(self, *args, **kwargs):
        self.ONLY_FAVORITES = kwargs.pop('favorites_initial', True)

        super(QSortFilterProxyModel, self).__init__(*args, **kwargs)

        self.setSortRole(SORTROLE)

    def only_favorites_changed(self, newval):
        self.ONLY_FAVORITES = newval
        self.invalidateFilter() # signal that filtering param changed

    def filtering_item(self, row, parentindex, column=0):
        # tricky thing here is that "parentindex" correspondes 
        # to (invalid) root item for top level items, and so
        # we can't get the parent item via model->itemFromIndex
        source = self.sourceModel()
        # handle top level item case explicitly
        if parentindex == source.invisibleRootItem().index():
            parent = source.invisibleRootItem()
        else:
            parent = source.itemFromIndex(parentindex)

        return parent.child(row, column)

    def filterAcceptsRow(self, row, parentindex):
        if not self.ONLY_FAVORITES:
            return True # makes it easy
        else:
            item = self.filtering_item(row, parentindex)
            return item.course().isfavorite

class SliderHLayout(QHBoxLayout):
    """
    hlayout with labels on left and right, with 2 choices
    """
    valueChanged = pyqtSignal(bool)

    def __init__(self, *args, **kwargs):
        arglist = list(args)
        if len(arglist) >= 2:
            self.falseLabelText = arglist.pop(0)
            self.trueLabelText = arglist.pop(0)
            newargs = tuple(arglist)
        else:
            raise Exception('Slider needs 2 labels!')

        self.startVal = kwargs.pop('startVal', False)

        super(QHBoxLayout, self).__init__(*newargs, **kwargs)

        self.addFalseLabel()
        self.addSlider()
        self.addTrueLabel()

        self.setWidths()

        self.setValue(self.startVal)

        self.slider.valueChanged.connect(self.sliderValueChangedFcn)

    def addSlider(self):
        self.slider = QSlider()
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setMaximum(1)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(1)
        self.addWidget(self.slider)

    def addFalseLabel(self):
        self.falseLabel = QLabel(self.falseLabelText)
        self.falseLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.addWidget(self.falseLabel)

    def addTrueLabel(self):
        self.trueLabel = QLabel(self.trueLabelText)
        self.trueLabel.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.addWidget(self.trueLabel)

    def setWidths(self):
        self.setStretch(0, 2)
        self.setStretch(1, 1)
        self.setStretch(2, 2)

    def setValue(self, boolVal):
        self.slider.setValue(int(boolVal))

    def value(self):
        return bool(self.slider.value())

    def sliderValueChangedFcn(self, int):
        self.valueChanged.emit(bool(int))





