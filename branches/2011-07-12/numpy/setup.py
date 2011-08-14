#!/usr/bin/env python
# $URL$
# $Rev$
#
# setup.py
#
# Filipe Fernandes, 2011-05-29

import os
import sys
import glob
from distutils.core import setup
from distutils.command.sdist import sdist

try:  # Python 3
    from distutils.command.build_py import build_py_2to3 as build_py
except ImportError:  # Python 2
    from distutils.command.build_py import build_py

gui = 'gui/run_gui.py'
mainscript = 'bin/ccc-gistemp'
ico = "gui/resources/ccf.ico"

def get_gui_files(files):
    lst = []
    for f in files:
        lst.extend(glob.glob(os.path.join('gui/resources', f)))
    return lst

data_files = [('', ['readme.txt', 'LICENSE.txt', 'release-notes.txt'] +
                     get_gui_files(['*.txt', '*.png', '*.png', '*.ico'])
              )]

includes = ['gui.lib.notify']

classifiers = """\
Development Status :: 5 - Production/Stable
Environment :: Console
Intended Audience :: Science/Research
Intended Audience :: Developers
Intended Audience :: Education
License :: OSI Approved :: BSD License
Operating System :: OS Independent
Programming Language :: Python
Topic :: Scientific/Engineering
Topic :: Education
Topic :: Software Development :: Libraries :: Python Modules
"""


def get_platform():
    """safer way to determine platform. """
    if sys.platform.startswith('win'):
        return 'windows'
    elif sys.platform.startswith('darwin'):
        return 'mac'
    return 'linux'

if get_platform() == 'mac':
    import py2app
    extra_options = dict(
         #app=[{"script": mainscript}],
         app=[{"script": gui}],
         options={"py2app": {
             "argv_emulation": True,
             "iconfile": ico,
             "includes": includes
             }}
        )
elif get_platform() == 'windows':
    import py2exe
    extra_options = dict(
        windows=[{"script": gui,
                  "icon_resources": [(1, ico)]}],
        console=[{"script": mainscript,
                  "icon_resources": [(1, ico)]}],
        options={"py2exe": {
            "compressed": 1,
            "optimize": 2,
            "bundle_files": 2,
            "dist_dir": 'dist',
            "xref": False,
            "skip_archive": False,
            "ascii": False,
            "custom_boot_script": '',
            "dll_excludes": ["MSVCP90.dll"],
            "includes": includes
            }},
        )
else:
    extra_options = dict(
        scripts=[mainscript],
        )

setup(name='ccc-gistemp',
      version='0.6.1',
      packages=['CCCgistemp', 'CCCgistemp.code', 'CCCgistemp.tool',
                'gui', 'gui.lib'],
      license='LICENSE.txt',
      description="""ccc-gistemp is a reimplementation of GISTEMP in Python""",
      long_description=open('readme.txt').read(),  # change to capitals
      author='Nick Barnes, David Jones',
      author_email='ccc-gistemp@climatecode.org',
      url='http://code.google.com/p/ccc-gistemp/',
      download_url='http://ccc-gistemp.googlecode.com/files/ccc-gistemp-0.6.1.tar.gz',
      classifiers=filter(None, classifiers.split("\n")),
      platforms='any',
      cmdclass={'build_py': build_py},
      keywords=['science', 'climate', 'GIS', 'temperature'],
      data_files=data_files,
      **extra_options
     )