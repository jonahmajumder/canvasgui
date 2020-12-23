import sys
from time import time

from canvasapi import Canvas
from canvasapi.exceptions import Unauthorized

from secrets import BASEURL, TOKEN

canvas = Canvas(BASEURL, TOKEN)

u = canvas.get_current_user()

f = u.get_favorite_courses()

mm = f[7]

ann = mm.get_discussion_topics(only_announcements=True)

print([a.title for a in ann])


