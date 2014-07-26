# Copyright (C) 2014 Matthieu Caneill <matthieu.caneill@gmail.com>
#
# This file is part of Debsources.
#
# Debsources is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import glob
from setuptools import setup, find_packages

with open('requirements.txt') as f:
    install_requires = [l for l in f.read().splitlines()
                        if not l.startswith('#')]

description = 'Browse, query and make stats on Debian packages source code.'
long_description = (
'This tool allows you to set up a Debsources instance, and synchronize\n'
'the packages sources you want, in order to browse them via a web\n'
'application, produce statistics through plugins, and play with source code.')

setup(
    name='debsources',
    version='0.1',
    packages=find_packages(),
    install_requires=install_requires,
    scripts = glob.glob('bin/debsources-*'),
    include_package_data=True,
    author="Stefano Zacchiroli, Matthieu Caneill",
    author_email="info@sources.debian.net",
    long_description=long_description,
    description=description,
    license="AGPL3+",
    url="http://anonscm.debian.org/gitweb/?p=qa/debsources.git",
    platforms=['any'],
)
