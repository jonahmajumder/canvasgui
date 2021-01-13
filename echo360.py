# echo360.py

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlsplit, urlunsplit, unquote

import json
import re

def get_formdata(formelem):
    inputs = formelem.find_all('input')
    return {i.attrs['name']: i.attrs.get('value', '') for i in inputs}

def auth_echo_session(credentials, sess=None):
    # make new session only existing not provided
    if sess is None:
        sess = requests.Session()

    url1 = 'https://login.echo360.org/login'

    r1 = sess.get(url1)
    assert r1.ok

    soup1 = BeautifulSoup(r1.text, 'html.parser')
    loginform1 = soup1.find(id='login-form')
    data1 = get_formdata(loginform1)
    data1['email'] = credentials['email']
    dest2 = loginform1.attrs['action']
    url2 = urlunsplit(urlsplit(r1.url)._replace(path=dest2))

    r2 = sess.post(url2, data=data1)
    assert r2.ok

    soup2 = BeautifulSoup(r2.text, 'html.parser')
    loginform2 = soup2.find(id='login-form')
    data2 = get_formdata(loginform2)
    data2['password'] = credentials['password']
    dest3 = loginform2.attrs['action']
    url3 = urlunsplit(urlsplit(r2.url)._replace(path=dest3, query=''))

    r3 = sess.post(url3, data=data2)
    assert r3.ok

    soup3 = BeautifulSoup(r3.text, 'html.parser')
    loginform3 = soup3.find(id='completeLogin')
    data3 = get_formdata(loginform3)
    url4 = unquote(loginform3.attrs['action'])

    r4 = sess.post(url4, data=data3)
    assert r4.ok

    return sess

# example of how it could be used

if __name__ == '__main__':
    pass

