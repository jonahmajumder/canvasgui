from canvasapi import Canvas
from canvasapi.exceptions import Unauthorized
from bs4 import BeautifulSoup

from pathlib import Path
import os
import requests
from urllib import parse
from dateutil.parser import isoparse
from datetime import datetime
import pytz
import json

from guihelper import *
from appcontrol import convert
from secrets import BASEURL, TOKEN

DOWNLOADS = os.path.expanduser('~/Downloads')

TIMEZONE = pytz.timezone('America/New_York')

def get_root_folder(course):
    all_folders = course.get_folders()
    first_levels = [f for f in all_folders if len(Path(f.full_name).parents) == 1]
    assert len(first_levels) == 1
    return first_levels[0]

def get_courses_separated(canvas):
    u = canvas.get_current_user()
    favorites = u.get_favorite_courses()
    favorite_ids = [c.id for c in favorites]
    all_courses = list(u.get_courses())
    others = [c for c in all_courses if c.id not in favorite_ids]
    return favorites, others

def safe_get_folders(parent):
    try:
        folders = list(parent.get_folders())
    except Unauthorized:
        print('Unauthorized!')
        folders = []
    return folders

def safe_get_files(parent):
    try:
        files = list(parent.get_files())
    except Unauthorized:
        print('Unauthorized!')
        files = []
    return files

def get_item_data(url):
    resp = requests.get(url, headers={'Authorization': 'Bearer {}'.format(TOKEN)})
    return resp

def get_module_page_links(item):
    body = get_module_page_html(item)
    linkdict = {}
    if body is not None:
        soup = BeautifulSoup(body, 'html.parser')
        links = soup.find_all('a')
        classes = [l.attrs.get('class', []) for l in links]
        rettypes = [l.attrs.get('data-api-returntype', '') for l in links]
        for (l, r) in zip(links, rettypes):
            if len(r) > 0:
                if not json.loads(l.attrs.get('aria-hidden', 'false')):
                    if r not in linkdict:
                        linkdict[r] = []
                    linkdict[r].append(l)

    # linkdict['files'] = [l for l in links if 'instructure_file_link' in l.attrs.get('class', [])]
    # linkdict['internals'] = [l for l in links if 'data-api-returntype' in l.attrs and 'file_preview_link' not in l.attrs.get('class', []) and l not in linkdict['files']]

    # leftover_links = [l for l in links if (l not in linkdict['files']) and (l not in linkdict['internals'])]
    # linkdict['leftovers'] = leftover_links

    # for k,v in linkdict.items():
    #     print(k)
    #     [print(l) for l in v]
    #     print('')

    return linkdict

def get_module_page_html(item):
    r = get_item_data(item.url)
    js = r.json()
    if 'body' in js:
        return js['body']
    else:
        print(js)
        return None

def download_file(item, loc=DOWNLOADS):
    r = get_item_data(item.url)
    if confirm_dialog('Download {}?'.format(item.filename), title='Confirm Download'):
        save_binary_response(r, item.filename, DOWNLOADS)

def download_module_file(item, loc=DOWNLOADS):
    r = get_item_data(item.url)
    js = r.json()
    r = get_item_data(js['url'])
    if confirm_dialog('Download {}?'.format(js['display_name']), title='Confirm Download'):
        save_binary_response(r, js['display_name'], DOWNLOADS)

def download_module_linked_file(attrs, loc=DOWNLOADS):
    r = get_item_data(attrs['href'])
    if confirm_dialog('Download {}?'.format(attrs['title']), title='Confirm Download'):
        save_binary_response(r, attrs['title'], DOWNLOADS)

def get_module_linked_page(attrs):
    r = get_item_data(attrs['data-api-endpoint'])
    js = r.json()
    return js

def parse_title_from_link(attrs):
    if 'title' in attrs:
        return attrs['title']
    else:
        js = get_module_linked_page(attrs)
        if 'title' in js:
            return js['title']
        elif 'display_name' in js:
            return js['display_name']
        else:
            print(json.dumps(js))
            raise Exception('Could not find a title!')


def save_binary_response(resp, filename, loc):
    filename = parse.unquote(filename)
    newpath = Path(loc) / filename
    if not newpath.exists():
        with open(str(newpath), 'wb') as fileobj:
            fileobj.write(resp.content)
        print('{} downloaded.'.format(filename))
    else:
        print('{} already exists here; file not replaced.'.format(filename))

    if newpath.suffix in ['.doc', '.docx', '.ppt', '.pptx']:
        convert(newpath)
        os.remove(newpath)


def hasattr_not_none(obj, attr):
    if hasattr(obj, attr):
        if getattr(obj, attr) is not None:
            return True
        else:
            return False
    else:
        return False

def get_date_string(canvasobj):
    if hasattr_not_none(canvasobj, 'created_at'):
        return canvasobj.created_at
    elif hasattr_not_none(canvasobj, 'completed_at'):
        return canvasobj.completed_at
    elif hasattr_not_none(canvasobj, 'unlock_at'):
        return canvasobj.unlock_at
    elif hasattr_not_none(canvasobj, 'url'): # do this one last because can't try another after
        jsdata = get_item_data(canvasobj.url).json()
        if 'created_at' in jsdata:
            return jsdata['created_at']
        else:
            return None
    else:
        return None

def parse_date_string(datestring):
    if datestring is not None:
        utctime = isoparse(datestring)
        nyctime = utctime.astimezone(TIMEZONE)
        return nyctime
    else:
        return None

def format_date(datetimeobj):
    if datetimeobj is not None:
        days_ago = (datetime.now().astimezone(TIMEZONE).date() - datetimeobj.date()).days
        if days_ago == 0:
            daystring = 'Today'
        elif days_ago == 1:
            daystring = 'Yesterday'
        else:
            daystring = datetimeobj.strftime('%b %-d, %Y')

        timestring = datetimeobj.strftime('%-I:%M %p')

        return '{0} at {1}'.format(daystring, timestring)
    else:
        return ''





