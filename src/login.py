# login.py

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlsplit, urlunsplit, unquote
from pathlib import Path

import keyring

import json
import re

def dump_resp(r):
    with open('resp.html', 'w') as file:
        file.write(r.text)

def get_formdata(formelem):
    inputs = formelem.find_all('input')
    return {i.attrs['name']: i.attrs.get('value', '') for i in inputs}

# def submit_form(formelem, newdata, session):
#     d = get_formdata(formelem)
#     d.update(newdata)

#     assert d.attrs['method'].lower().strip() == 'post'

#     r = session.post(d.attrs['action'], d)
#     assert r.ok

def auth_canvas_session(credential, baseurl, sess=None):
    # make new session only existing not provided
    if sess is None:
        sess = requests.Session()

    try:
        parts = urlsplit(baseurl)
        loginurl = urlunsplit(parts._replace(path=str(Path(parts.path) / 'login')))

        r1 = sess.get(loginurl)
        assert r1.ok

        soup1 = BeautifulSoup(r1.text, 'html.parser')

        # unfortunately, this step is institution-dependent
        # currently requires that login:
        # - is one-page
        # - uses an HTML form with id 'fm1'
        # - HTML form has input field names 'username' and 'password'

        loginform = soup1.find(id='fm1')
        data = get_formdata(loginform)
        data.update({'username': credential.username, 'password': credential.password})

        r2 = sess.post(r1.url, data=data)
        assert r2.ok

        return sess
    except:
        return None

def auth_echo_session(credential, sess=None):
    # make new session only existing not provided
    if sess is None:
        sess = requests.Session()

    try:
        url1 = 'https://login.echo360.org/login'

        r1 = sess.get(url1)
        assert r1.ok

        soup1 = BeautifulSoup(r1.text, 'html.parser')
        loginform1 = soup1.find(id='login-form')
        data1 = get_formdata(loginform1)
        data1.update({'email': credential.username})
        dest2 = loginform1.attrs['action']
        url2 = urlunsplit(urlsplit(r1.url)._replace(path=dest2))

        r2 = sess.post(url2, data=data1)
        assert r2.ok

        soup2 = BeautifulSoup(r2.text, 'html.parser')
        loginform2 = soup2.find(id='login-form')
        data2 = get_formdata(loginform2)
        data2.update({'password': credential.password})
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
    except:
        return None

def auth_session(sess=None):
    # make new session only existing not provided
    if sess is None:
        sess = requests.Session()

    sess = auth_canvas_session(sess)
    sess = auth_echo_session(sess)

    return sess


# example of how it could be used

if __name__ == '__main__':
    pass
