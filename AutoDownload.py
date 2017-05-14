#!/usr/bin/env python
# -*- coding: utf-8 -*-

# AutoDownload.py / Version 0.1
# https://github.com/emericg/OpenSubtitlesDownload
# This software is designed to help you find and download subtitles for your favorite videos!

# Copyright (c) 2014 by Julie Koubova <juliekoubova@icloud.com>
#                       Emeric GRANGE <emeric.grange@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import os
import re
import subprocess
import sys

# don't download more than that many subtitles at once.
# i hear opensubtitles has some pretty strict policy about that.

MAX_MOVIES = 50

MOVIE_EXT = ['3g2', '3gp', '3gp2', '3gpp', 'ajp', \
        'asf', 'asx', 'avchd', 'avi', 'bik', 'bix', 'box', 'cam', 'dat', \
        'divx', 'dmf', 'dv', 'dvr-ms', 'evo', 'flc', 'fli', 'flic', 'flv', \
        'flx', 'gvi', 'gvp', 'h264', 'm1v', 'm2p', 'm2ts', 'm2v', 'm4e', \
        'm4v', 'mjp', 'mjpeg', 'mjpg', 'mkv', 'moov', 'mov', 'movhd', 'movie', \
        'movx', 'mp4', 'mpe', 'mpeg', 'mpg', 'mpv', 'mpv2', 'mxf', 'nsv', \
        'nut', 'ogg', 'ogm', 'ogv', 'omf', 'ps', 'qt', 'ram', 'rm', 'rmvb', \
        'swf', 'ts', 'vfw', 'vid', 'video', 'viv', 'vivo', 'vob', 'vro', \
        'webm', 'wm', 'wmv', 'wmx', 'wrap', 'wvx', 'wx', 'x264', 'xvid']

SUBTITLE_EXT = [ 'srt', 'sub' ]

movie_regex = re.compile(r'^.*\.({0})$'.format(
        '|'.join(MOVIE_EXT)
    ))

def find_movies(roots):
    for root in roots:
        for current, dirs, files in os.walk(root):
            for f in files:
                if movie_regex.match(f):
                    yield os.path.join(current, f)

def has_subtitles(path):
    name, _ = os.path.splitext(path)
    for sub_ext in SUBTITLE_EXT:
        if os.path.isfile('{0}.{1}'.format(name, sub_ext)):
            return True
    return False

def main(roots):
    movies_without_subs = [
        m for m in find_movies(roots) if not has_subtitles(m)
    ]

    if not movies_without_subs:
        return

    if len(movies_without_subs) > MAX_MOVIES:
        print("found {0} movies without subtitles, downloading only first {1}".format(
                len(movies_without_subs), MAX_MOVIES
            ), file=sys.stderr)
        movies_without_subs = movies_without_subs[0:MAX_MOVIES]

    this_dir = os.path.dirname(os.path.realpath(__file__))
    downloader = os.path.join(this_dir, 'OpenSubtitlesDownload.py')

    cmd = [ downloader, '--auto', '--gui', 'cli' ]
    cmd.extend(movies_without_subs)

    subprocess.check_call(cmd)

if len(sys.argv) < 2:
    sys.exit("usage: {0} directory_with_movies...".format(sys.argv[0]))

main(sys.argv[1:])
