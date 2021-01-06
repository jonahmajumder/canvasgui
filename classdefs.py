import sys
from time import time
import json
import os
import re
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

from echo360 import get_formdata

from canvasapi import Canvas
from canvasapi.favorite import Favorite
from canvasapi.exceptions import Unauthorized, ResourceDoesNotExist
from appcontrol import convert, CONVERTIBLE_EXTENSIONS
from guihelper import disp_html, confirm_dialog
from locations import ResourceFile

class CustomItem(QStandardItem):
    """
    base class for everything!
    (not intended to be instantiated directly)
    """
    def __init__(self, *args, **kwargs):
        super(CustomItem, self).__init__(*args, **kwargs)

        self.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        self.date = DateItem(item=self)

        self.CONTEXT_MENU_ACTIONS = []
        self.update_context_menu()

    def dblClickFcn(self, **kwargs):
        pass

    def expand(self, **kwargs):
        pass

    def download(self, **kwargs):
        pass

    def itemChangeFcn(self):
        pass

    def expand_recursive(self):
        self.expand()
        for ch in self.children():
            ch.expand_recursive()

    def lineage(self, lineage=[]):
        lineage = [self] + lineage # highest up will be first
        if self.parent() is None:
            return lineage
        else:
            return self.parent().lineage(lineage)

    def children(self):
        return [self.child(r, 0) for r in range(self.rowCount())]

    def append_item_row(self, item):
        children = self.children()
        lineage = self.lineage()

        if not item in children and not item in lineage:
            row = []
            row.append(item)
            row.append(item.date)
            self.appendRow(row)

    def update_context_menu(self):
        self.contextMenu = QMenu()
        for d in self.CONTEXT_MENU_ACTIONS:
            action = self.contextMenu.addAction(d['displayname'])
            action.triggered.connect(d['function'])

    def run_context_menu(self, point):
        if len(self.contextMenu.actions()) > 0:
            action = self.contextMenu.exec_(point)
            
    def course(self):
        # recursively find topmost parent
        if self.parent() is None:
            return self
        else:
            return self.parent().course()

    def print(self, text):
        self.course().gui.print(text)

    def open_and_notify(self, url):
        self.print('Opening linked url:\n{}'.format(url))
        webbrowser.open(url)

    def __eq__(self, other):
        return (self.identifier() == other.identifier())

    def identifier(self):
        raise Exception('Identifier must be subclassed for class {}!'.format(type(self).__name__))

class CanvasItem(CustomItem):
    """
    intermediate parent class for tree elements with corresponding canvasapi objects
    (not intended to be instantiated directly)
    """
    SORTROLE = Qt.UserRole

    def __init__(self, *args, **kwargs):
        self.obj = kwargs.pop('object', None)
        super(CanvasItem, self).__init__(*args, **kwargs)

        self.process_name()

    def auth_get(self, url):
        return self.obj._requester.request('GET', _url=url)

    def api_get(self, urlpath):
        return self.obj._requester.request('GET', urlpath)

    def process_name(self):
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
        self.setData(self.name, self.SORTROLE)

    def identifier(self):
        if isinstance(self, PageItem):
            return self.obj.page_id
        else:
            return self.obj.id

    def safe_get_folders(self, folder=None):
        parent = folder if folder else self.obj
        try:
            folders = list(parent.get_folders())
        except Unauthorized:
            self.print('Unauthorized!')
            folders = []
        return folders

    def safe_get_files(self, folder=None):
        parent = folder if folder else self.obj
        try:
            files = list(parent.get_files())
        except Unauthorized:
            self.print('Unauthorized!')
            files = []
        return files

    def to_apiurl(self, url):
        parts = parse.urlsplit(url)

    def get_html_links(self, html):
        linkdict = {}
        soup = BeautifulSoup(html, 'html.parser')
        links = soup.find_all('a')
        for l in links:
            if 'instructure_file_link' in l.attrs.get('class', []):
                try:
                    urlparts = parse.urlsplit(l.attrs['href'])
                    r = self.api_get(urlparts.path)
                    newpath = 'api/v1/' / Path(urlparts.path).relative_to('/')
                    newparts = urlparts._replace(query='', path=str(newpath))
                    l.attrs['data-api-endpoint'] = parse.urlunsplit(newparts)

                    info = self.parse_api_url(l.attrs['data-api-endpoint'])
                    if 'files' in info:
                        l.attrs['data-api-returntype'] = 'File'
                    elif 'pages' in info:
                        l.attrs['data-api-returntype'] = 'Page'
                    elif 'quizzes' in info:
                        l.attrs['data-api-returntype'] = 'Quiz'
                    elif 'assignments' in info:
                        l.attrs['data-api-returntype'] = 'Assignment'
                    else:
                        raise ValueError('Unknown instructure_file_link type, url: {}'.format(l.attrs['data-api-endpoint']))

                except ResourceDoesNotExist:
                    pass

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
                    self.append_item_row(item)
            for a in pages:
                info = self.parse_api_url(a.attrs['data-api-endpoint'])
                page = self.course().safe_get_item('get_page', parse.unquote(info['pages']))
                if page:
                    item = PageItem(object=page)
                    self.append_item_row(item)
            for a in quizzes:
                info = self.parse_api_url(a.attrs['data-api-endpoint'])
                quiz = self.course().safe_get_item('get_quiz', info['quizzes'])
                if quiz:
                    item = QuizItem(object=quiz)
                    self.append_item_row(item)
            for a in assignments:
                info = self.parse_api_url(a.attrs['data-api-endpoint'])
                assignment = self.course().safe_get_item('get_assignment', info['assignments'])
                if assignment:
                    item = AssignmentItem(object=assignment)
                    self.append_item_row(item)
            if not sum(links.values(), []):
                self.print('No HTML links found.')
        else:
            self.print('No HTML present.')

    def retrieve_sessionless_url(self):
        if hasattr(self.obj, 'url'):
            d = self.auth_get(self.obj.url)
            pagetype = d.headers['content-type'].split(';')[0]
            if pagetype == 'application/json':
                if 'url' in d.json():
                    return d.json()['url']

        return None

    def parse_api_url(self, apiurl):
        pathstr = parse.urlsplit(apiurl).path.strip(os.sep)
        parts = Path(pathstr).parts
        if not len(parts) % 2:
            info = {k:v for (k,v) in zip(parts[::2], parts[1::2])}
        else:
            raise Exception('Odd number of path elements to parse ({})'.format(pathstr))
        return info

class CourseItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "course" objects
    """
    CONTENT_TYPES = [
        {'tag': 'modules', 'displayname': 'Modules', 'icon': 'icons/book_module.png'},
        {'tag': 'files', 'displayname': 'Filesystem', 'icon': 'icons/book_folder.png'},
        {'tag': 'assignments', 'displayname': 'Assignments', 'icon': 'icons/book_assignment.png'},
        {'tag': 'tools', 'displayname': 'External Tools', 'icon': 'icons/book_link.png'},
        {'tag': 'announcements', 'displayname': 'Announcements', 'icon': 'icons/book_announcement.png'}

    ]

    def __init__(self, *args, **kwargs):
        self.expanders = [
            self.get_modules,
            self.get_filesystem,
            self.get_assignments,
            self.get_tools,
            self.get_announcements
        ]

        self.gui = kwargs.pop('gui')
        self.echo360session = kwargs.pop('echo360session', None)

        self.content = self.gui.contentTypeComboBox.currentIndex()
        self.downloadfolder = self.gui.preferences.current['downloadfolder']

        super(CourseItem, self).__init__(*args, **kwargs)

        self.setEditable(True) # item is editable but nothing causes editing except explicit

        self.init_from_obj()

    def refresh(self):
        self.refresh_course_obj()
        self.process_name()
        self.init_from_obj()
        self.gui.proxyModel.invalidateFilter()

    def refresh_course_obj(self):
        self.obj = self.gui.canvas.get_course(self.obj.id, include=['term', 'favorites'])

    def get_nickname(self):
        self.nickname = self.gui.canvas.get_course_nickname(self.obj.id)
        self.has_nickname = self.nickname is not None

    def init_from_obj(self):
        self.CONTEXT_MENU_ACTIONS = []
        self.get_nickname()

        if self.obj.is_favorite:
            self.favoriteobj = Favorite(self.obj._requester, {'context_id': self.obj.id, 'context_type': 'course'})
            self.CONTEXT_MENU_ACTIONS.extend([
                {'displayname': 'Remove Favorite', 'function': self.remove_favorite}
            ])
        else:
            self.favoriteobj = None
            self.CONTEXT_MENU_ACTIONS.extend([
                {'displayname': 'Add Favorite', 'function': self.add_favorite}
            ])

        self.CONTEXT_MENU_ACTIONS.extend([
            {'displayname': 'Edit Nickname', 'function': self.edit_text}
        ])

        self.update_context_menu()

        self.setIcon(QIcon(ResourceFile(self.CONTENT_TYPES[self.content]['icon'])))

    def add_favorite(self):
        self.favoriteobj = self.gui.user.add_favorite_course(self.obj.id)
        self.refresh()

    def remove_favorite(self):
        # this is necessary due to bug
        self.favoriteobj.context_type = 'course'

        self.favoroteobj = self.favoriteobj.remove()
        self.refresh()

    def set_nickname(self, newname):
        if newname.strip() == '':
            self.nickname.remove()
            self.setText(self.nickname.name)
        else:
            self.gui.canvas.set_course_nickname(self.obj.id, newname)

        # most foolproof would be to call self.refresh here,
        # but that causes gui to hang with edit field open
        # (something in self.init_from_obj is responsible)
        # hacky solution: do everything in that method except init_from_obj
        self.refresh_course_obj()
        self.process_name()
        self.gui.proxyModel.invalidateFilter()

    def edit_text(self):
        self.gui.tree.edit(self.gui.proxyModel.mapFromSource(self.index()))

    def itemChangeFcn(self):
        # this function is called for all item changes (not just editing)
        # only change nickname if text was changed
        if self.text() != self.name:
            self.set_nickname(self.text())

    def expand(self, **kwargs):
        self.expanders[self.content]()

    def dblClickFcn(self, **kwargs):
        self.expand(**kwargs)

    def get_modules(self):
        ct = 0
        for m in self.obj.get_modules():
            item = ModuleItem(object=m)
            self.append_item_row(item)
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
                self.append_item_row(item)
            
            for folder in folders:
                item = FolderItem(object=folder)
                self.append_item_row(item)
        else:
            self.setEnabled(False)

    def get_assignments(self):
        assignments = self.obj.get_assignments()
        if len(list(assignments)) > 0:
            for a in assignments:
                item = AssignmentItem(object=a)
                self.append_item_row(item)
        else:
            self.setEnabled(False)

    def get_tools(self):
        tabs = [t for t in self.obj.get_tabs() if t.type == 'external']
        if len(tabs) > 0:
            for t in tabs:
                if t.label == 'Echo360' and self.gui.echo360session is not None:
                    item = Echo360Item(object=t, session=self.gui.echo360session)
                    self.append_item_row(item)
                else:
                    item = TabItem(object=t)
                    self.append_item_row(item)
        else:
            self.setEnabled(False)

    def get_announcements(self):
        announcements = self.obj.get_discussion_topics(only_announcements=True)
        if len(list(announcements)) > 0:
            for a in announcements:
                item = AnnouncementItem(object=a)
                self.append_item_row(item)
        else:
            self.setEnabled(False)

    def safe_get_item(self, method, id):
        try:
            return getattr(self.obj, method)(id)
        except Unauthorized:
            self.print('Unauthorized!')
            return None
        except ResourceDoesNotExist:
            self.print('Resource "{0}" (via "{1}") not found for course "{2}".'.format(id, method, self.name))
            return None

class ExternalToolItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "externaltool" objects
    note: this is not great because some tools are inaccessible as these types of objects
    """
    def __init__(self, *args, **kwargs):
        super(ExternalToolItem, self).__init__(*args, **kwargs)

        self.CONTEXT_MENU_ACTIONS.extend([
            {'displayname': 'Open', 'function': self.open}
        ])
        self.update_context_menu()

        self.setIcon(QIcon(ResourceFile('icons/link.png')))

    def dblClickFcn(self, **kwargs):
        self.open(**kwargs)

    def open(self, **kwargs):
        if 'url' in self.obj.custom_fields:
            self.open_and_notify(self.obj.custom_fields['url'])
        else:
            self.print('No external url found!')

class TabItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "tab" objects
    note: represents similar information to externaltools but preferable
    because all are "accessible"
    """
    def __init__(self, *args, **kwargs):
        super(TabItem, self).__init__(*args, **kwargs)

        self.CONTEXT_MENU_ACTIONS.extend([
            {'displayname': 'Open', 'function': self.open}
        ])

        self.update_context_menu()

        self.setIcon(QIcon(ResourceFile('icons/link.png')))

    def open(self, **kwargs):
        u = self.retrieve_sessionless_url()
        if u is not None:
            self.open_and_notify(u)
        else:
            self.print('No external url found!')

    def dblClickFcn(self, **kwargs):
        self.open(**kwargs)

class Echo360Item(TabItem):
    """
    docstring for Echo360Item
    """
    def __init__(self, *args, **kwargs):
        self.session = kwargs.pop('session', None)
        assert self.session is not None

        super(Echo360Item, self).__init__(*args, **kwargs)

        self.setIcon(QIcon(ResourceFile('icons/echo360.png')))

        self.get_urls()

    def get_urls(self):
        r1 = self.session.get(self.retrieve_sessionless_url())
        assert r1.ok

        soup = BeautifulSoup(r1.text, 'html.parser')
        postform = soup.find(id='tool_form')
        data = get_formdata(postform)

        r2 = self.session.post(postform['action'], data=data)
        assert r2.ok

        self.homeurl = r2.url

        parts = parse.urlsplit(self.homeurl)
        path = Path(parts.path)
        self.section_id = path.parent.name
        self.urlparts = parts._replace(path=str(path.parent))

    def make_url(self, relpath):
        currentpath = Path(self.urlparts.path)
        newpath = currentpath / relpath
        newparts = self.urlparts._replace(path=str(newpath))
        return parse.urlunsplit(newparts)

    def get_syllabus(self):
        r = self.session.get(self.make_url('syllabus'))
        assert r.ok

        js = r.json()
        assert js['status'] == 'ok'
        return js['data']

    def get_lectures(self):
        syllabus = self.get_syllabus()
        return [l['lesson'] for l in syllabus]

    def expand(self, **kwargs):
        lectures = self.get_lectures()
        for lec in lectures:
            item = Echo360LectureItem(json=lec)
            self.append_item_row(item)

        if len(lectures) == 0:
            self.setEnabled(False)

    def open(self, **kwargs):
        self.open_and_notify(self.homeurl)

    def dblClickFcn(self, **kwargs):
        self.expand(**kwargs)

class Echo360LectureItem(CustomItem):
    """
    class for individual echo360 lectures
    notably NOT a CanvasItem (and has no canvas obj)
    """
    def __init__(self, *args, **kwargs):
        json = kwargs.pop('json', None)

        # create obj so date class is happy
        attrdict = json
        self.obj = type('Lecture', (object,), attrdict)

        super(Echo360LectureItem, self).__init__(*args, **kwargs)

        self.name = self.obj.lesson['name']

        self.setText(self.name)
        self.setData(self.name, CanvasItem.SORTROLE)

        self.CONTEXT_MENU_ACTIONS.extend([
            {'displayname': 'Open', 'function': self.open},
            {'displayname': 'Download', 'function': self.download}
        ])
        self.update_context_menu()

        self.setIcon(QIcon(ResourceFile('icons/video.png')))

        self.basepath = Path('/lesson/{}'.format(self.obj.lesson['id']))

    def make_url(self, path):
        newparts = self.parent().urlparts._replace(path=str(path))
        return parse.urlunsplit(newparts)

    def identifier(self):
        return self.obj.lesson['id']

    def dblClickFcn(self, **kwargs):
        self.open(**kwargs)

    def open(self, **kwargs):
        openpath = self.basepath / 'classroom'
        self.open_and_notify(self.make_url(openpath))

    def make_downloadurl(self, **kwargs):
        hd = kwargs.get('hidef', True)

        online_filename = 'hd1.mp4' if hd else 'sd1.mp4'
        media_id = self.obj.medias[0]['id']
        downloadpath = Path('media/download/{0}/video/{1}'.format(media_id, online_filename))
        return self.make_url(downloadpath)

    def download(self, **kwargs):
        confirm = kwargs.get('confirm', True)
        loc = kwargs.get('location', self.course().downloadfolder)

        u = self.make_downloadurl(**kwargs)

        if confirm:
            confirmed = confirm_dialog('Download video {}?'.format(self.name), title='Confirm Download')
        else:
            confirmed = True

        if confirmed:
            newpath = (Path(loc) / self.name).with_suffix('.mp4') # build local file Path obj

            if not newpath.exists():
                # download file here
                self.open_and_notify(u)
                self.print('{} downloaded.'.format(newpath.name))
            else:
                self.print('{0} already exists at {1}; file not replaced.'.format(newpath.name, loc))


class ExternalUrlItem(CanvasItem):
    """
    class for module items with type "externalurl" which have no canvasapi class
    have "external_url" property and little else (typically no date)
    """
    def __init__(self, *args, **kwargs):
        super(ExternalUrlItem, self).__init__(*args, **kwargs)

        self.CONTEXT_MENU_ACTIONS.extend([
            {'displayname': 'Open', 'function': self.open}
        ])
        self.update_context_menu()

        self.setIcon(QIcon(ResourceFile('icons/link.png')))

    def dblClickFcn(self, **kwargs):
        self.open(**kwargs)

    def open(self, **kwargs):
        self.open_and_notify(self.obj.external_url)

class ModuleItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "module" objects
    """
    def __init__(self, *args, **kwargs):
        super(ModuleItem, self).__init__(*args, **kwargs)

        self.CONTEXT_MENU_ACTIONS.extend([
            {'displayname': 'Download Module', 'function': self.download}
        ])
        self.update_context_menu()

        self.setIcon(QIcon(ResourceFile('icons/module.png')))

    def expand(self, **kwargs):
        items = list(self.obj.get_module_items(include='content_details'))
        for mi in items:
            if mi.type == 'SubHeader':
                pass
            elif mi.type == 'File':
                file = self.course().safe_get_item('get_file', mi.content_id)
                if file:
                    item = FileItem(object=file)
                    self.append_item_row(item)
            elif mi.type == 'Page':
                page = self.course().safe_get_item('get_page', mi.page_url)
                if page:
                    item = PageItem(object=page)
                    self.append_item_row(item)
            elif mi.type == 'Discussion':
                disc = self.course().safe_get_item('get_discussion_topic', mi.content_id)
                if disc:
                    item = DiscussionItem(object=disc)
                    self.append_item_row(item)
            elif mi.type == 'Quiz':
                quiz = self.course().safe_get_item('get_quiz', mi.content_id)
                if quiz:
                    item = QuizItem(object=quiz)
                    self.append_item_row(item)
            elif mi.type == 'Assignment':
                assignment = self.course().safe_get_item('get_assignment', mi.content_id)
                if assignment:
                    item = AssignmentItem(object=assignment)
                    self.append_item_row(item)

            elif mi.type == 'ExternalUrl' or mi.type == 'ExternalTool':
                item = ExternalUrlItem(object=mi)
                self.append_item_row(item)
            else:
                self.print('{0} has unrecognized type ("{1}").'.format(str(mi), mi.type))
                item = ModuleItemItem(object=mi)
                self.append_item_row(item)

        if len(items) == 0:
            self.setEnabled(False)

    def dblClickFcn(self, **kwargs):
        self.expand(**kwargs)

    def download(self, **kwargs):
        loc = kwargs.get('location', self.course().downloadfolder)
        confirm = kwargs.get('confirm', True)

        if confirm:
            confirmed = confirm_dialog('Download contents of {}?'.format(self.name), title='Confirm Download')
        else:
            confirmed = True

        folderpath = Path(loc) / self.name

        if folderpath.exists():
            self.print('Folder {0} already exists at {1}; module not downloaded.'.format(self.name, loc))
        else:
            folderpath.mkdir()
            self.expand()
            for ch in self.children():
                ch.download(location=folderpath, confirm=False) # works for both files and folders!

class ModuleItemItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "moduleitem" objects
    this class should only be instantiated when an "unknown" type is encountered
    """
    def __init__(self, *args, **kwargs):
        super(ModuleItemItem, self).__init__(*args, **kwargs)

        self.CONTEXT_MENU_ACTIONS.extend([
            {'displayname': 'Open', 'function': self.open}
        ])
        self.update_context_menu()

        self.setIcon(QIcon(ResourceFile('icons/link.png')))

    def open(self, **kwargs):
        if hasattr(self.obj, 'html_url'):
            self.open_and_notify(self.obj.html_url)
        else:
            self.print('No html_url to open.')

    def dblClickFcn(self, **kwargs):
        self.open(**kwargs)

class FolderItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "folder" objects
    """
    def __init__(self, *args, **kwargs):
        super(FolderItem, self).__init__(*args, **kwargs)

        self.CONTEXT_MENU_ACTIONS.extend([
            {'displayname': 'Download Folder', 'function': self.download}
        ])
        self.update_context_menu()

        self.setIcon(QIcon(ResourceFile('icons/folder.png')))

    def expand(self, **kwargs):
        for file in self.safe_get_files():
            item = FileItem(object=file)
            self.append_item_row(item)

        for folder in self.safe_get_folders():
            item = FolderItem(object=folder)
            self.append_item_row(item)

    def dblClickFcn(self, **kwargs):
        self.expand(**kwargs)

    def download(self, **kwargs):
        loc = kwargs.get('location', self.course().downloadfolder)
        confirm = kwargs.get('confirm', True)

        if confirm:
            confirmed = confirm_dialog('Download contents of {}?'.format(self.name), title='Confirm Download')
        else:
            confirmed = True

        folderpath = Path(loc) / self.name

        if folderpath.exists():
            self.print('Folder {0} already exists at {1}; not downloaded.'.format(self.name, loc))
        else:
            folderpath.mkdir()
            self.expand()
            for ch in self.children():
                ch.download(location=folderpath, confirm=False) # works for both files and folders!

class FileItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "file" objects (within folders)
    """
    def __init__(self, *args, **kwargs):
        super(FileItem, self).__init__(*args, **kwargs)

        self.CONTEXT_MENU_ACTIONS.extend([
            {'displayname': 'Download', 'function': self.download}
        ])
        self.update_context_menu()

        self.setIcon(QIcon(ResourceFile('icons/file.png')))

    # this is a faster version of the CanvasAPI's download method (not sure why...)
    def save_data(self, filepath):
        r = self.auth_get(self.obj.url)
        with open(filepath, 'wb') as fileobj:
            fileobj.write(r.content)

    def download(self, **kwargs):
        loc = kwargs.get('location', self.course().downloadfolder)
        confirm = kwargs.get('confirm', True)

        if confirm:
            confirmed = confirm_dialog('Download {}?'.format(self.obj.filename), title='Confirm Download')
        else:
            confirmed = True

        if confirmed:
            filename = parse.unquote(self.obj.filename)
            newpath = Path(loc) / filename # build local file Path obj
            if not newpath.exists():
                self.save_data(str(newpath))
                self.print('{} downloaded.'.format(filename))
            else:
                self.print('{0} already exists at {1}; file not replaced.'.format(filename, loc))

            if newpath.suffix in CONVERTIBLE_EXTENSIONS:
                if confirm_dialog('Convert {} to PDF?'.format(filename), title='Convert File'):
                    self.print('Converting {} to a PDF.'.format(filename))
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

        self.CONTEXT_MENU_ACTIONS.extend([
            {'displayname': 'Display HTML', 'function': self.display}
        ])
        self.update_context_menu()

        self.setIcon(QIcon(ResourceFile('icons/html.png')))

    def expand(self, **kwargs):
        self.children_from_html(self.obj.body, **kwargs)

    def dblClickFcn(self, **kwargs):
        self.expand(**kwargs)

    def display(self, **kwargs):
        if self.obj.body:
            disp_html(self.obj.body, title=self.name)
        else:
            self.print('No content on page.')

class QuizItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "quiz" objects
    """
    def __init__(self, *args, **kwargs):
        super(QuizItem, self).__init__(*args, **kwargs)

        self.CONTEXT_MENU_ACTIONS.extend([
            {'displayname': 'Open', 'function': self.open}
        ])
        self.update_context_menu()

        self.setIcon(QIcon(ResourceFile('icons/quiz.png')))

    def open(self, **kwargs):
        self.open_and_notify(self.obj.html_url)

    def dblClickFcn(self, **kwargs):
        self.open(**kwargs)

class DiscussionItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "discussiontopic" objects
    meant for "discussion" type items (discussion_type: threaded)
    """
    def __init__(self, *args, **kwargs):
        super(DiscussionItem, self).__init__(*args, **kwargs)

        assert self.obj.discussion_type == 'threaded'

        self.CONTEXT_MENU_ACTIONS.extend([
            {'displayname': 'Display HTML', 'function': self.display}
        ])
        self.update_context_menu()

        self.setIcon(QIcon(ResourceFile('icons/discussion.png')))

    def expand(self, **kwargs):
        self.children_from_html(self.obj.message, **kwargs)

    def dblClickFcn(self, **kwargs):
        self.expand(**kwargs)

    def display(self, **kwargs):
        disp_html(self.obj.message, title=self.text())

class AnnouncementItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "discussiontopic" objects
    meant for "discussion" type items (discussion_type: side_comment)
    """
    def __init__(self, *args, **kwargs):
        super(AnnouncementItem, self).__init__(*args, **kwargs)

        assert self.obj.discussion_type == 'side_comment'

        self.init_from_obj()

    def init_from_obj(self):

        if self.obj.read_state == 'read':
            self.is_read = True
        elif self.obj.read_state == 'unread':
            self.is_read = False
        else:
            raise ValueError('Unrecognized "read_state" attribute!')

        self.CONTEXT_MENU_ACTIONS = []

        self.CONTEXT_MENU_ACTIONS.extend([
            {'displayname': 'Expand Embedded Links', 'function': self.expand}
        ])

        if self.is_read:
            self.CONTEXT_MENU_ACTIONS.extend([
                {'displayname': 'Mark as Unread', 'function': self.mark_unread}
            ])
            self.setIcon(QIcon(ResourceFile('icons/announcement.png')))
        else:
            self.CONTEXT_MENU_ACTIONS.extend([
                {'displayname': 'Mark as Read', 'function': self.mark_read}
            ])
            self.setIcon(QIcon(ResourceFile('icons/announcement_unread_blue.png')))

        self.update_context_menu()

    def refresh(self):
        newobj = self.course().obj.get_discussion_topic(self.obj)
        self.obj = newobj
        self.init_from_obj()

    def mark_read(self):
        self.obj.mark_as_read()
        self.refresh()

    def mark_unread(self):
        self.obj.mark_as_unread()
        self.refresh()

    def expand(self, **kwargs):
        self.children_from_html(self.obj.message, **kwargs)

    def dblClickFcn(self, **kwargs):
        self.display(**kwargs)

    def display(self, **kwargs):
        disp_html(self.obj.message, title=self.text())
        self.mark_read()

class AssignmentItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "assigment" objects
    """
    def __init__(self, *args, **kwargs):
        super(AssignmentItem, self).__init__(*args, **kwargs)

        self.CONTEXT_MENU_ACTIONS.extend([
            {'displayname': 'Open', 'function': self.open}
        ])
        self.update_context_menu()

        self.setIcon(QIcon(ResourceFile('icons/assignment.png')))

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

class DateItem(QStandardItem):
    """
    QStandardItem subclass used in second column to represent date of CanvasItem
    """
    TIMEZONE = pytz.timezone('America/New_York')

    def __init__(self, *args, **kwargs):
        self.item = kwargs.pop('item')
        super(DateItem, self).__init__(*args, **kwargs)
        self.datetime = self.datetime_from_obj(self.item.obj)

        self.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        self.setData(self.as_qdt(), CanvasItem.SORTROLE)

        self.setText(self.smart_formatted())

    def run_context_menu(self, point):
        self.item.run_context_menu(point)

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

    def datestr_from_obj(self, obj):
        datestr_attrs = [
            'created_at',
            'completed_at',
            'unlock_at',
            'due_at',
            'endTimeUTC'
        ]

        for attr in datestr_attrs:
            if self.hasattr_not_none(obj, attr):
                return getattr(obj, attr)

        if self.hasattr_not_none(obj, 'url'): # do this one last because can't try another after
            jsdata = self.item.auth_get(obj.url).json()
            if 'created_at' in jsdata:
                return jsdata['created_at']

        # if fcn reaches here it means all others failed -- return none
        
        return None

    def datetime_from_obj(self, obj):
        s = self.datestr_from_obj(obj)
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
        # set defaults
        self.ONLY_FAVORITES = kwargs.pop('favorites_initial', True)
        self.terms = kwargs.pop('terms', [])
        self.VISIBLE_TERM_IDS =  [t['id'] for t in self.terms] # initially all

        super(QSortFilterProxyModel, self).__init__(*args, **kwargs)

        self.setSortRole(CanvasItem.SORTROLE)

    def only_favorites_changed(self, newval):
        self.ONLY_FAVORITES = newval
        self.invalidateFilter() # signal that filtering param changed

    def terms_changed(self, bool_vals):
        terms = [t['id'] for t in self.terms]
        self.VISIBLE_TERM_IDS = [i for (i,b) in zip(terms, bool_vals) if b]
        self.invalidateFilter()

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
        item = self.filtering_item(row, parentindex)

        if not self.ONLY_FAVORITES:
            favorite_accept = True # makes it easy
        else:
            favorite_accept = item.course().obj.is_favorite

        if item.course().obj.term['id'] in self.VISIBLE_TERM_IDS:
            term_accept = True
        else:
            term_accept = False

        return favorite_accept and term_accept

# ---------------------------- CUSTOM WIDGETS -----------------------------

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


class CheckableComboBox(QComboBox):
    """
    subclass of QComboBox with checkable options
    """
    selectionsChanged = pyqtSignal(list)
    TagDataRole = Qt.UserRole + 1

    def __init__(self, *args, **kwargs):

        listargs = list(args)
        self.title = listargs.pop(0)
        args = tuple(listargs)

        super(CheckableComboBox, self).__init__(*args, **kwargs)

        self.setItemDelegate(CustomStyledItemDelegate(self))

        self.model = QStandardItemModel()

        self.titleitem = QStandardItem()
        self.titleitem.setText(self.title)
        self.titleitem.setTextAlignment(Qt.AlignHCenter)
        self.titleitem.setFlags(Qt.NoItemFlags) # set disabled
        self.model.appendRow(self.titleitem)

        self.model.itemChanged.connect(self.selectionChangedFcn)
        self.currentIndexChanged.connect(self.itemSelected)

        self.setModel(self.model)
        self.setCurrentIndex(0)

        # remove selection coloring so user doesn't see
        # self.setStyleSheet("""
        #     selection-background-color: rgba(0, 0, 0, 0%);
        #     selection-color: rgb(0, 0, 0);
        # """)


    def addItem(self, text, checked=False, tag=None):
        newitem = QStandardItem(text)
        newitem.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        if checked:
            newitem.setData(Qt.Checked, Qt.CheckStateRole)
        else:
            newitem.setData(Qt.Unchecked, Qt.CheckStateRole)
        newitem.setData(tag, self.TagDataRole)
        self.model.appendRow(newitem)

    def children(self):
        return [self.model.item(i,0) for i in range(1, self.model.rowCount())]

    def strings(self):
        return [self.model.item(i,0).text() for i in range(1, self.model.rowCount())]

    def checked(self):
        checkstates = [item.data(Qt.CheckStateRole) for item in self.children()]
        return [state == Qt.Checked for state in checkstates]

    def checkedList(self):
        ischecked = self.checked()
        return os.linesep.join([s for (s,b) in zip(self.strings(), self.checked()) if b])

    def selectionChangedFcn(self, item):
        self.selectionsChanged.emit(self.checked())

    def toggleItem(self, item):
        item.setData(
            Qt.Unchecked if item.data(Qt.CheckStateRole) == Qt.Checked else Qt.Checked,
            Qt.CheckStateRole
        )

    def itemSelected(self, idx):
        if idx > 0:
            self.toggleItem(self.model.item(idx,0))
            self.setCurrentIndex(0)

class CustomStyledItemDelegate(QStyledItemDelegate):
    """
    Fixes issue with macOS checkbox in qcombobox styling
    """
    def __init__(self, *args, **kwargs):
        super(CustomStyledItemDelegate, self).__init__(*args, **kwargs)

    """
    signature: paint(QPainter *painter, const QStyleOptionViewItem &option, const QModelIndex &index) 
    """
    def paint(self, painter, option, index):
        option = QStyleOptionViewItem(option) # cast?
        option.showDecorationSelected = False
        super(CustomStyledItemDelegate, self).paint(painter, option, index)


