# Python Canvas (Courseworks) GUI

This project builds on the open-source Python package [CanvasAPI](https://canvasapi.readthedocs.io/en/stable/index.html), which is itself built to interact with Instructure's RESTful [HTTP API](https://canvas.instructure.com/doc/api/index.html). Using this package (and Qt for Python), I have built an interactive app allowing a user to browse (and download) courses, files, assignments, and other content.

Below is a depiction of content from my own classes, viewed at the "module" level.

<img src="screenshot.png" width="800">

Login is accomplished with an OAuth token (generated online via the user's profile page, as explained [here](https://canvas.instructure.com/doc/api/file.oauth.html#manual-token-generation)). That token, along with an institution-specific base URL, can be included in a file or entered manually.

The (hidden) preferences file is called `.canvasdefaults` and lives in the user's home directory (i.e. /Users/\<username\>/.canvasdefaults). It is a json file with the following keys:
```
"baseurl": <institution-specific url>
"token": <personal generated oauth token>
"downloadfolder": <path to a local folder>
"defaultcontent": <"modules", "files", "assignments", "tools", or "announcements">
```
If any of these are deemed invalid (or no file is detected), a GUI will prompt the user to fill them in. This interface also allows the user to save entered credentials for future use.

### Echo360 Support

My instution uses the [Echo360](https://echo360.com/) platform to host recorded lectures. The Canvas API presents this feature as an "external tool" without much access to the associated data. Because this is a feature I use frequently, I built the ability to access this data into my app. While the Echo360 platform exposes a RESTful API, it is not accessible to the average (student) user. Therefore, data is simply accessed via an authenticated `requests.session`. This means that the only credentials needed are those normally used with the web interface.

Credentials can be included in a file analagous to `.canvasdefaults`, called `.echocredentials`, also located in the user's home directory (/Users/\<username\>/.echocredentials). It is also a json file and must have the (self-explanatory) keys `email` and `password`. If this file is not present (or incorrectly configured), the application will simply treat Echo360 features like any other external tool.

### Nonstandard (Direct) Dependencies
(All available on PyPI)

- [PyQt5](https://pypi.org/project/PyQt5/)
- [CanvasAPI](https://pypi.org/project/canvasapi/)
- [dateutil](https://pypi.org/project/python-dateutil/)
- [BeautifulSoup](https://pypi.org/project/beautifulsoup4/)

Installing these packages via pip will automatically trigger installation of all other dependencies. See `requirements.txt` for the full list.

### To do list:

- [X] Pereferences UI allowing specification of login credentials, download destination, default view
- [X] Autosaving/setting defaults file
- [X] Editing of preferences during app operation
- [X] Test changing user/auth credentials during app operation (i.e. resetting)
- [X] Context menus for everything but expand
- [ ] Handling of right clicking on multiple items
- [X] Different course icons to indicate current content mode
- [X] Course nicknaming by editing item (right click -> Rename)
- [X] Folder (recursive) downloading
- [X] Module downloading
- [X] Announcement/discussion topic support
- [X] Automatic conversion of Excel files to PDFs (as with Word and Powerpoint files)
- [X] Filtering by semester
- [X] Better column resizing
- [X] Convert from widget to model architecture
- [X] Sorting by date
- [X] Select external tools from "tabs" rather than directly
- [X] Replace terminal printed lines with status bar text
- [X] Dealing with duplicate children
- [X] Deployment into macOS (.app) standalone application
- [X] Testing standalone .app on other machine
- [ ] Conveying information about echo360 credentials to user (e.g. included, incorrect, etc.)
- [ ] Create menu for showing profile, opening preferences editor
- [ ] Application-level error handling?
- [ ] Multithreaded retrieval of data for "expand all" (back burner)
