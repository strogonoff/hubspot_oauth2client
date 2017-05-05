# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function

import sys

from setuptools import find_packages
from setuptools import setup

import hubspot_oauth2client


if sys.version_info < (2, 7):
    print(
        'hubspot_oauth2client requires Python 2 version >= 2.7.',
        file=sys.stderr)
    sys.exit(1)

install_requires = [
    'requests>=2.13',
]

long_desc = (
    "hubspot_oauth2client is a lightweight client library for OAuth 2.0 "
    "that works with Hubspot and mimics a subset of Google’s oauth2client "
    "API.")

version = hubspot_oauth2client.__version__

setup(
    name='hubspot_oauth2client',
    version=version,
    description='Hubspot OAuth 2.0 client library',
    long_description=long_desc,
    author='Anton Strogonoff',
    url='http://github.com/strogonoff/hubspot_oauth2client/',
    install_requires=install_requires,
    packages=find_packages(),
    license='BSD 2-clause',
    keywords='hubspot oauth 2.0 http client',
    classifiers=[
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX',
        'Topic :: Internet :: WWW/HTTP',
    ],
)
