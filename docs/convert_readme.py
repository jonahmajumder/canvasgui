import markdown
from bs4 import BeautifulSoup
import re
from pathlib import Path
import base64

parent = Path(__file__).parent

def path_to_file(filename):
    return str(parent / filename)

filename = 'README'
mdfile = path_to_file('{}.md'.format(filename))
htmlfile = path_to_file('{}.html'.format(filename))

with open(mdfile, 'r') as file:
    html = markdown.markdown(file.read())

soup = BeautifulSoup(html, 'html.parser')

# embed image in html
imgs = soup.find_all('img')
for img in imgs:
    data = open(path_to_file(img['src']), 'rb').read()
    data_uri = base64.b64encode(data).decode('utf-8')
    img['src'] = 'data:image/png;base64,{}'.format(data_uri)

checked = soup.find_all('li', text=re.compile(r'\[X\].*'))
unchecked = soup.find_all('li', text=re.compile(r'\[ \].*'))

for li in checked:
    li['class'] = 'checkbox'

for li in unchecked:
    li['class'] = 'checkbox'
    li.string = str(li.string).replace('[ ]', '[&nbsp;&nbsp;]')

styletag = soup.new_tag('style', type='text/css')

css = """
li.checkbox {
    list-style-type: none;
}
"""

styletag.string = css

soup.insert(0, styletag)

with open(htmlfile, 'w') as file:
    file.write(soup.prettify(formatter=None))