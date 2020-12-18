from canvasapi import Canvas
from canvasapi.exceptions import Unauthorized
from bs4 import BeautifulSoup

from pathlib import Path
import os
import requests
from urllib import parse

from guihelper import *
from appcontrol import convert
from secrets import BASEURL, TOKEN

# DOWNLOADS = os.path.expanduser('~/Downloads')

# def get_item_data(url):
#     resp = requests.get(url, headers={'Authorization': 'Bearer {}'.format(TOKEN)})
#     return resp

# def retrieve_sessionless_url(url):
#     d = get_item_data(url)
#     pagetype = d.headers['content-type'].split(';')[0]
#     if pagetype == 'application/json':
#         if 'url' in d.json():
#             return d.json()['url']
#         else:
#             return None
#     else:
#         return None

# def download_file(item, loc=DOWNLOADS):
#     if confirm_dialog('Download {}?'.format(item.filename), title='Confirm Download'):
#         r = get_item_data(item.url)
#         save_binary_response(r, item.filename, DOWNLOADS)

# def save_binary_response(resp, filename, loc):
#     filename = parse.unquote(filename)
#     newpath = Path(loc) / filename
#     if not newpath.exists():
#         with open(str(newpath), 'wb') as fileobj:
#             fileobj.write(resp.content)
#         print('{} downloaded.'.format(filename))
#     else:
#         print('{} already exists here; file not replaced.'.format(filename))

#     if newpath.suffix in ['.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx']:
#         if confirm_dialog('Convert {} to PDF?'.format(filename), title='Convert File'):
#             convert(newpath)
#             os.remove(newpath)






