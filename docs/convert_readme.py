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
    mdstring = file.read()

mdstring = mdstring.replace(r'\<username\>', '<span class="angled">username</span>')

html = markdown.markdown(mdstring)
soup = BeautifulSoup(html, 'html.parser')

title = soup.find('h1')

title.string = 3 * '&nbsp;' + title.string

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

for code in soup.find_all('code'):
    code.string = code.string.replace('<', '&lt;')
    code.string = code.string.replace('>', '&gt;')

    code.string = code.string.replace('\n', '<br/>')

for s in soup.find_all('span'):
    s.string = '&lt;' + s.string + '&gt;'
    s.unwrap()

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