#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# OpenSubtitlesDownload.py / Version 6.5
# This software is designed to help you find and download subtitles for your favorite videos!

# You can browse the project's GitHub page:
# - https://github.com/emericg/OpenSubtitlesDownload

# Learn much more about it on the wiki:
# - https://github.com/emericg/OpenSubtitlesDownload/wiki

# Copyright (c) 2026 by Emeric GRANGE <emeric.grange@gmail.com>
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import sys
import time
import shutil
import struct
import argparse
import mimetypes
import subprocess

from threading import Lock
from collections import deque

import json
import urllib
import urllib.request
import urllib.error

# ==== OpenSubtitles.com server settings =======================================

# Track API availability:
# > https://92500a62-df9e-42ed-82a4-e6b3eeb89365.site.hbuptime.com/

# API endpoints
API_URL = 'https://api.opensubtitles.com/api/v1/'
API_URL_LOGIN = API_URL + 'login'
API_URL_LOGOUT = API_URL + 'logout'
API_URL_SEARCH = API_URL + 'subtitles'
API_URL_DOWNLOAD = API_URL + 'download'

# This application is registered:
APP_NAME = 'OpenSubtitlesDownload'
APP_VERSION = '6.5'
APP_API_KEY = 'FNyoC96mlztsk3ALgNdhfSNapfFY9lOi'

# ==== OpenSubtitles.com account (required) ====================================

# A valid account from opensubtitles.com is REQUIRED.
# You can use a VIP account to avoid "in-subtitles" advertisement and bypass download limits.

# The username is NOT your account email address, but in fact, your username...
# Be careful about your password security, it will be stored right here, in plain text...
# Can be overridden at run time with '-u' and '-p' arguments.
# Can be overridden at run time with 'OSD_ENV_USERNAME' and 'OSD_ENV_PASSWORD' environment variables.
osd_username = ''
osd_password = ''

# ==== Language settings =======================================================

# Full guide: https://github.com/emericg/OpenSubtitlesDownload/wiki/Adjust-settings

# 1/ Change the search language by using any supported 2-letter (ISO 639-1) language code:
#    > https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes
#    > Supported language codes: https://opensubtitles.stoplight.io/docs/opensubtitles-api/1de776d20e873-languages
#    > Ex: opt_languages = 'en'
# 2/ Search for subtitles in several languages by using multiple codes separated by a comma:
#    > Ex: opt_languages = 'en,fr'
opt_languages = 'en'

# Write language code (ex: _en) at the end of the subtitles file. 'on', 'off' or 'auto'.
# If you are regularly searching for several language at once, you sould use 'on'.
opt_language_suffix = 'auto'

# Character used to separate file path from the language code (ex: file_en.srt).
opt_language_suffix_separator = '_'

# ==== Search settings =========================================================

# Subtitles search mode. Can be overridden at run time with '-s' argument.
# - hash (search using file hash only)
# - filename (search using filename only)
# - hash_then_filename (search using file hash, then if no results, by filename) (default)
# - hash_and_filename (search using both methods)
opt_search_mode = 'hash_then_filename'

# Search and download a subtitles even if one already exists.
opt_search_overwrite = True

# Subtitles selection mode. Can be overridden at run time with '-t' argument.
# - default (in case of multiple results, lets you choose the subtitles you want)
# - manual (always let you choose the subtitles you want)
# - auto (automatically select the best subtitles found)
opt_selection_mode = 'default'

# Customize subtitles download path. Can be overridden at run time with '-o' argument.
# By default, subtitles are downloaded next to their video file.
opt_output_path = ''

# Ignore Hearing Impaired (HI) subtitles?
opt_ignore_hi = False

# Ignore machine translated subtitles?
opt_ignore_machine_translated = True

# Ignore AI translated subtitles?
opt_ignore_ai_translated = False

# Ignore "foreign parts only" subtitles?
opt_ignore_foreign_parts_only = False

# ==== GUI settings ============================================================

# Select your GUI. Can be overridden at run time with '--gui=xxx' argument.
# - auto (autodetection, fallback on CLI)
# - gnome (GNOME/GTK based environments, using 'zenity' backend)
# - kde (KDE/Qt based environments, using 'kdialog' backend)
# - cli (Command Line Interface)
opt_gui = 'auto'

# Change the subtitles selection GUI size:
opt_gui_width  = 940
opt_gui_height = 480

# Various GUI columns to show/hide during subtitles selection. You can set them to 'on', 'off' or 'auto'.
opt_selection_language = 'auto'
opt_selection_match    = 'auto'
opt_selection_hi       = 'auto'
opt_selection_fps      = 'off'
opt_selection_rating   = 'off'
opt_selection_count    = 'off'

# ==== HOOK ====================================================================

# Use a secondary tool on the subtitles file after a successful download?
custom_command = ""

# ==== Check file path & type ==================================================

def checkFileValidity(path):
    """Check mimetype and/or file extension to detect valid video file"""
    if os.path.isfile(path) is False:
        superPrint("info", "File not found", f"The file provided was not found:<br><i>{path}</i>")
        return False

    fileMimeType, encoding = mimetypes.guess_type(path)
    if fileMimeType is None:
        fileExtension = path.rsplit('.', 1)
        if fileExtension[1] not in ['avi', 'mov', 'mp4', 'mp4v', 'm4v', 'mkv', 'mk3d', 'webm', \
                                    'ts', 'mts', 'm2ts', 'ps', 'vob', 'evo', 'mpeg', 'mpg', \
                                    'asf', 'wm', 'wmv', 'rm', 'rmvb', 'divx', 'xvid']:
            #superPrint("error", "File type error!", f"This file is not a video (unknown mimetype AND invalid file extension):<br><i>{path}</i>")
            return False
    else:
        fileMimeType = fileMimeType.split('/', 1)
        if fileMimeType[0] != 'video':
            #superPrint("error", "File type error!", f"This file is not a video (unknown mimetype):<br><i>{path}</i>")
            return False

    return True

# ==== Check for existing subtitles file =======================================

def checkSubtitlesExists(path):
    """Check if a subtitles already exists for the current file"""
    extList = ['srt', 'sub', 'mpl', 'webvtt', 'dfxp', 'txt', 'sbv', 'smi', 'ssa', 'ass', 'usf']
    sepList = ['_', '-', '.']
    tryList = ['']

    if opt_language_suffix_separator not in sepList:
        sepList.append(opt_language_suffix_separator)

    if opt_language_suffix in ('on', 'auto'):
        for language in languageList:
            for sep in sepList:
                tryList.append(sep + language)

    for ext in extList:
        for teststring in tryList:
            subPath = path.rsplit('.', 1)[0] + teststring + '.' + ext
            if os.path.isfile(subPath) is True:
                superPrint("info", "Subtitles already downloaded!", f"A subtitles file already exists for this file:<br><i>{subPath}</i>")
                return True

    return False

# ==== Hashing algorithm =======================================================
# Info: https://trac.opensubtitles.org/projects/opensubtitles/wiki/HashSourceCodes
# This particular implementation is coming from SubDownloader: https://subdownloader.net

def hashFile(path):
    """Produce a hash for a video file: size + 64bit chksum of the first and
    last 64k (even if they overlap because the file is smaller than 128k)"""
    try:
        longlongformat = 'Q' # unsigned long long little endian
        bytesize = struct.calcsize(longlongformat)
        fmt = "<%d%s" % (65536//bytesize, longlongformat)

        f = open(path, "rb")

        filesize = os.fstat(f.fileno()).st_size
        filehash = filesize

        if filesize < 65536 * 2:
            superPrint("error", "File size error!", f"File size error while generating hash for this file:<br><i>{path}</i>")
            return "SizeError"

        buf = f.read(65536)
        longlongs = struct.unpack(fmt, buf)
        filehash += sum(longlongs)

        f.seek(-65536, os.SEEK_END) # size is always > 131072
        buf = f.read(65536)
        longlongs = struct.unpack(fmt, buf)
        filehash += sum(longlongs)
        filehash &= 0xFFFFFFFFFFFFFFFF

        f.close()
        returnedhash = "%016x" % filehash
        return returnedhash

    except IOError:
        superPrint("error", "I/O error!", f"Input/Output error while generating hash for this file:<br><i>{path}</i>")
        return "IOError"

    except Exception:
        print("Unexpected error (line " + str(sys.exc_info()[-1].tb_lineno) + "): " + str(sys.exc_info()[0]))

# ==== String escaping =========================================================
# Title and filename may need string sanitizing to avoid zenity/kdialog handling errors

def escapeGUI_title(string):
    if opt_gui != 'cli':
        string = string.replace('"', '\\"')
    return string

def escapeGUI_zenity(string):
    if opt_gui == 'gnome':
        string = string.replace('"', '\\"')
        string = string.replace("'", "\\'")
        string = string.replace('`', '\\`')
        string = string.replace("&", "&amp;")
    return string

def escapeGUI_kdialog(string):
    if opt_gui == 'kde':
        string = string.replace('"', '\\"')
        string = string.replace('`', '\\`')
    return string

def escapePath_wget(string):
    string = string.replace('"', '\\"')
    string = string.replace('`', '\\`')
    return string

# ==== Super Print =============================================================
# priority: info, warning, error
# title: only for zenity and kdialog messages
# message: full text, with tags and breaks (tags will be cleaned up for CLI)

def superPrint(priority, title, message):
    """Print messages through terminal, zenity or kdialog"""
    if opt_gui == 'gnome':
        # Adapt to zenity
        message = message.replace("<br>", "\n")
        # Escape
        message = escapeGUI_zenity(message)
        # Print message
        subprocess.call(['zenity', '--width=' + str(opt_gui_width), f'--{priority}', f'--title={title}', f'--text={message}'])
    elif opt_gui == 'kde':
        # Adapt to kdialog
        message = message.replace("\n", "<br>")
        if priority == 'warning':
            priority = 'sorry'
        elif priority == 'info':
            priority = 'msgbox'
        # Print message
        subprocess.call(['kdialog', '--geometry=' + str(opt_gui_width-220) + 'x' + str(opt_gui_height-128) + '+128+128', f'--title={title}', f'--{priority}={message}'])
    else:
        # Clean up format tags and line breaks
        message = message.replace("\n\n", "\n")
        message = message.replace("<br><br>", "\n")
        message = message.replace("<br>", "\n")
        message = message.replace("<i>", "")
        message = message.replace("</i>", "")
        message = message.replace("<b>", "")
        message = message.replace("</b>", "")
        # Print message
        print(">> " + message)

# ==== GNOME (zenity) selection window =========================================

def selectionGnome(subtitlesResultList):
    """GNOME subtitles selection window using zenity"""
    subtitlesSelectedName = u''
    subtitlesSelectedIndex = -1

    subtitlesItems = u''
    subtitlesMatchedByHash = 0
    subtitlesMatchedByName = 0
    columnHi = ''
    columnLn = ''
    columnMatch = ''
    columnRate = ''
    columnCount = ''
    columnFPS = ''

    videoTitle_window = escapeGUI_title(videoTitle)
    videoTitle_escaped = escapeGUI_zenity(videoTitle)
    videoFileName_escaped = escapeGUI_zenity(videoFileName)

    # Generate selection window content
    for idx, item in enumerate(subtitlesResultList['data']):
        if opt_ignore_hi and item['attributes'].get('hearing_impaired', False) == True:
            continue
        if opt_ignore_foreign_parts_only and item['attributes'].get('foreign_parts_only', False) == True:
            continue
        if opt_ignore_ai_translated and item['attributes'].get('ai_translated', False) == True:
            continue
        if opt_ignore_machine_translated and item['attributes'].get('machine_translated', False) == True:
            continue

        if item['attributes'].get('moviehash_match', False) == True:
            subtitlesMatchedByHash += 1
        else:
            subtitlesMatchedByName += 1

        subtitlesItems += f'{idx} "' + escapeGUI_zenity(item['attributes']['files'][0]['file_name']) + '" '

        if opt_selection_hi == 'on':
            columnHi = '--column="HI" '
            if item['attributes'].get('hearing_impaired', False) == True:
                subtitlesItems += u'"✔" '
            else:
                subtitlesItems += '"" '
        if opt_selection_language == 'on':
            columnLn = '--column="Language" '
            subtitlesItems += '"' + item['attributes']['language'] + '" '
        if opt_selection_match == 'on':
            columnMatch = '--column="MatchedBy" '
            if item['attributes'].get('moviehash_match', False) == True:
                subtitlesItems += '"HASH" '
            else:
                subtitlesItems += '"name" '
        if opt_selection_rating == 'on':
            columnRate = '--column="Rating" '
            subtitlesItems += '"' + str(item['attributes']['ratings']) + '" '
        if opt_selection_count == 'on':
            columnCount = '--column="Downloads" '
            subtitlesItems += '"' + str(item['attributes']['download_count']).zfill(5) + '" '
        if opt_selection_fps == 'on':
            columnFPS = '--column="FPS" '
            subtitlesItems += '"' + str(item['attributes']['fps']) + '" '

    if subtitlesMatchedByName == 0:
        tilestr = f' --title="Subtitles for: {videoTitle_window}" '
        textstr = f' --text="<b>Video title:</b> {videoTitle_escaped}\n<b>File name:</b> {videoFileName_escaped}" '
    elif subtitlesMatchedByHash == 0:
        tilestr = ' --title="Subtitles Search" '
        textstr = f' --text="Search results using file name, NOT video detection. <b>May be unreliable...</b>\n<b>File name:</b> {videoFileName_escaped}" '
    else: # a mix of the two
        tilestr = f' --title="Subtitles for: {videoTitle_window}" '
        textstr = f' --text="Search results using file name AND video detection.\n<b>Video title:</b> {videoTitle_escaped}\n<b>File name:</b> {videoFileName_escaped}" '

    # Spawn zenity "list" dialog
    process_subtitlesSelection = subprocess.Popen('zenity --width=' + str(opt_gui_width) + ' --height=' + str(opt_gui_height) + ' --list' + tilestr + textstr + ' --column "id" --hide-column=1 ' +
                                                  '--column="Available subtitles" ' + columnHi + columnLn + columnMatch + columnRate + columnCount + columnFPS + subtitlesItems + ' --print-column=ALL',
                                                  shell=True, stdout=subprocess.PIPE)

    # Get back the user's choice
    result_subtitlesSelection = process_subtitlesSelection.communicate()

    # The results contain a subtitles?
    if result_subtitlesSelection[0]:
        result = str(result_subtitlesSelection[0], 'utf-8', 'replace').strip("\n")

        # Get index and result
        [subtitlesSelectedIndex, subtitlesSelectedName] = result.split('|')[0:2]
    else:
        if process_subtitlesSelection.returncode == 0:
            subtitlesSelectedName = subtitlesResultList['data'][0]['attributes']['files'][0]['file_name']
            subtitlesSelectedIndex = 0

    # Return the result (selected subtitles name and index)
    return (subtitlesSelectedName, subtitlesSelectedIndex)

# ==== KDE (kdialog) selection window ==========================================

def selectionKDE(subtitlesResultList):
    """KDE subtitles selection window using kdialog"""
    subtitlesSelectedName = u''
    subtitlesSelectedIndex = -1

    subtitlesItems = u''
    subtitlesMatchedByHash = 0
    subtitlesMatchedByName = 0

    videoTitle_window = videoTitle
    videoTitle_escaped = videoTitle
    videoFileName_escaped = escapeGUI_kdialog(videoFileName)

    # Generate selection window content
    # TODO doesn't support additional columns
    index = 0

    for idx, item in enumerate(subtitlesResultList['data']):
        if opt_ignore_hi and item['attributes'].get('hearing_impaired', False) == True:
            continue
        if opt_ignore_foreign_parts_only and item['attributes'].get('foreign_parts_only', False) == True:
            continue
        if opt_ignore_ai_translated and item['attributes'].get('ai_translated', False) == True:
            continue
        if opt_ignore_machine_translated and item['attributes'].get('machine_translated', False) == True:
            continue

        if item['attributes'].get('moviehash_match', False) == True:
            subtitlesMatchedByHash += 1
        else:
            subtitlesMatchedByName += 1

        # key + subtitles name
        subtitlesItems += str(index) + ' "' + item['attributes']['files'][0]['file_name'] + '" '
        index += 1

    if subtitlesMatchedByName == 0:
        tilestr = f' --title="Subtitles for {videoTitle_window}" '
        menustr = f' --menu="<b>Video title:</b> {videoTitle_escaped}<br><b>File name:</b> {videoFileName_escaped}" '
    elif subtitlesMatchedByHash == 0:
        tilestr = ' --title="Subtitles Search" '
        menustr = f' --menu="Search results using file name, NOT video detection. <b>May be unreliable...</b><br><b>File name:</b> {videoFileName_escaped}" '
    else: # a mix of the two
        tilestr = f' --title="Subtitles for {videoTitle_window}" '
        menustr = f' --menu="Search results using file name AND video detection.<br><b>Video title:</b> {videoTitle_escaped}<br><b>File name:</b> {videoFileName_escaped}" '

    # Spawn kdialog "radiolist"
    process_subtitlesSelection = subprocess.Popen('kdialog --geometry=' + str(opt_gui_width-220) + 'x' + str(opt_gui_height-128) + f'+128+128 {tilestr} {menustr} {subtitlesItems}',
                                                  shell=True, stdout=subprocess.PIPE)

    # Get back the user's choice
    result_subtitlesSelection = process_subtitlesSelection.communicate()

    # The results contain the key matching a subtitles?
    if result_subtitlesSelection[0]:
        subtitlesSelectedIndex = int(str(result_subtitlesSelection[0], 'utf-8', 'replace').strip("\n"))
        subtitlesSelectedName = subtitlesResultList['data'][subtitlesSelectedIndex]['attributes']['files'][0]['file_name']

    # Return the result (selected subtitles name and index)
    return (subtitlesSelectedName, subtitlesSelectedIndex)

# ==== CLI selection mode ======================================================

def selectionCLI(subtitlesResultList):
    """Command Line Interface, subtitles selection inside your current terminal"""
    subtitlesSelectedName = u''
    subtitlesSelectedIndex = -1

    subtitlesMatchedByHash = 0
    subtitlesMatchedByName = 0

    # Check if search has results by hash or name
    for item in subtitlesResultList['data']:
        if item['attributes'].get('moviehash_match', False) == True:
            subtitlesMatchedByHash += 1
        else:
            subtitlesMatchedByName += 1

    # Print video infos
    if subtitlesMatchedByName == 0:
        print("\n>> Subtitles for: " + videoTitle)
    elif subtitlesMatchedByHash == 0:
        print("\n>> Subtitles for file: " + videoFileName)
        print(">> Search results using file name, NOT video detection. May be unreliable...")
    else: # a mix of the two
        print("\n>> Subtitles for: " + videoTitle)
        print(">> Search results using using file name AND video detection.")

    print("\n>> Available subtitles:")

    # Print subtitles list on the terminal
    for idx, item in enumerate(subtitlesResultList['data']):
        if opt_ignore_hi and item['attributes'].get('hearing_impaired', False) == True:
            continue
        if opt_ignore_foreign_parts_only and item['attributes'].get('foreign_parts_only', False) == True:
            continue
        if opt_ignore_ai_translated and item['attributes'].get('ai_translated', False) == True:
            continue
        if opt_ignore_machine_translated and item['attributes'].get('machine_translated', False) == True:
            continue

        subtitlesItemPre = u'> '
        subtitlesItem = u'"' + item['attributes']['files'][0]['file_name'] + u'"'
        subtitlesItemPost = u''

        if opt_selection_match == 'on':
            if item['attributes'].get('moviehash_match', False) == True:
                subtitlesItemPre += '(hash) > '
            else:
                subtitlesItemPre += '(name) > '
        if opt_selection_language == 'on':
            subtitlesItemPre += item['attributes']['language'].upper() + ' > '

        if opt_selection_hi == 'on' and item['attributes'].get('hearing_impaired', False) == True:
            subtitlesItemPost += ' > ' + '\033[44m' + ' HI ' + '\033[0m'
        if opt_selection_fps == 'on':
            subtitlesItemPost += ' > ' + '\033[100m' + str(item['attributes']['fps']) + ' FPS' + '\033[0m'
        if opt_selection_rating == 'on':
            subtitlesItemPost += ' > ' + '\033[100m' + 'Rating: ' + str(item['attributes']['ratings']) + '\033[0m'
        if opt_selection_count == 'on':
            subtitlesItemPost += ' > ' + '\033[100m' + 'Downloads: ' + str(item['attributes']['download_count']) + '\033[0m'

        # type # season_number # episode_number
        if (item['attributes']['feature_details'].get('season_number', 0) != 0 and item['attributes']['feature_details'].get('episode_number', 0) != 0):
            subtitlesItemPost += ' > ' + '\033[100m' + 'S' + str(item['attributes']['feature_details']['season_number']).zfill(2) + 'E' + str(item['attributes']['feature_details']['episode_number']).zfill(2) + '\033[0m'

        idx += 1 # We display subtitles indexes starting from 1, 0 is reserved for cancel

        if item['attributes'].get('moviehash_match', False) == True:
            print("\033[92m[" + str(idx).rjust(2, ' ') + "]\033[0m " + subtitlesItemPre + subtitlesItem + subtitlesItemPost)
        else:
            print("\033[93m[" + str(idx).rjust(2, ' ') + "]\033[0m " + subtitlesItemPre + subtitlesItem + subtitlesItemPost)

    # Ask user to selected a subtitles
    print("\033[91m[ 0]\033[0m Cancel search")
    while (subtitlesSelectedIndex < 0 or subtitlesSelectedIndex > idx):
        try:
            subtitlesSelectedIndex = int(input("\n>> Enter your choice [0-" + str(idx) + "]: "))
        except KeyboardInterrupt:
            sys.exit(1)
        except:
            subtitlesSelectedIndex = -1

    if subtitlesSelectedIndex <= 0:
        print("Cancelling search...")
        return ("", -1)

    subtitlesSelectedIndex -= 1
    subtitlesSelectedName = subtitlesResultList['data'][subtitlesSelectedIndex]['attributes']['files'][0]['file_name']

    # Return the result (selected subtitles name and index)
    return (subtitlesSelectedName, subtitlesSelectedIndex)

# ==== Automatic selection mode ================================================

def selectionAuto(subtitlesResultList, languageList):
    """Automatic subtitles selection using filename match"""
    subtitlesSelectedName = u''
    subtitlesSelectedIndex = -1

    videoFileParts = videoFileName.replace('-', '.').replace(' ', '.').replace('_', '.').lower().split('.')
    languageListReversed = list(reversed(languageList))
    maxScore = -1

    for idx, item in enumerate(subtitlesResultList['data']):
        score = 0
        # points to respect languages priority
        score += languageListReversed.index(item['attributes']['language']) * 100
        # extra point if the sub is found by hash
        if item['attributes'].get('moviehash_match', False) == True:
            score += 1
        # points for filename mach
        subFileParts = item['attributes']['files'][0]['file_name'].replace('-', '.').replace(' ', '.').replace('_', '.').lower().split('.')
        for subPart in subFileParts:
            for filePart in videoFileParts:
                if subPart == filePart:
                    score += 1
        if score > maxScore:
            maxScore = score
            subtitlesSelectedIndex = idx
            subtitlesSelectedName = subtitlesResultList['data'][subtitlesSelectedIndex]['attributes']['files'][0]['file_name']

    # Return the result (selected subtitles name and index)
    return (subtitlesSelectedName, subtitlesSelectedIndex)

# ==== Dependency checkers =====================================================

def pythonChecker():
    """Check the availability of Python 3.6 interpreter"""
    if sys.version_info < (3, 6):
        superPrint("error", "Wrong Python version", "You need <b>Python 3.6</b> to use OpenSubtitlesDownload.")
        return False
    return True

def dependencyChecker():
    """Check the availability of tools used as dependencies"""
    if opt_gui == 'gnome':
        for tool in ['wget']:
            path = shutil.which(tool)
            if path is None:
                superPrint("error", "Missing dependency!", f"<b>{tool}</b> is not available, please install it!")
                return False
    return True

# ==== REST API helpers ========================================================

def getUserToken(username, password):
    try:
        headers = {
            "User-Agent": f"{APP_NAME} v{APP_VERSION}",
            "Api-key": f"{APP_API_KEY}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "username": username,
            "password": password
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib_request_Request(API_URL_LOGIN, data=data, headers=headers)
        with urllib_request_urlopen(req) as response:
            response_data = json.loads(response.read().decode('utf-8'))

        #print("getUserToken() response data: " + str(response_data))
        return response_data['token']

    except (urllib.error.HTTPError, urllib.error.URLError) as err:
        print("Urllib error (", err.code, ") ", err.reason)
        superPrint("error", "OpenSubtitles.com login error!", "An error occurred while connecting to the OpenSubtitles.com server")
        sys.exit(2)
    except Exception:
        print("Unexpected error (line " + str(sys.exc_info()[-1].tb_lineno) + "): " + str(sys.exc_info()[0]))
        superPrint("error", "OpenSubtitles.com login error!", "An error occurred while connecting to the OpenSubtitles.com server")
        sys.exit(2)

def destroyUserToken(USER_TOKEN):
    try:
        headers = {
            "User-Agent": f"{APP_NAME} v{APP_VERSION}",
            "Api-key": f"{APP_API_KEY}",
            "Authorization": f"Bearer {USER_TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        req = urllib_request_Request(API_URL_LOGOUT, headers=headers)
        with urllib_request_urlopen(req) as response:
            response_data = json.loads(response.read().decode('utf-8'))

        #print("destroyUserToken() response data: " + str(response_data))
        return response_data

    except (urllib.error.HTTPError, urllib.error.URLError) as err:
        print("Urllib error (", err.code, ") ", err.reason)
    except Exception:
        print("Unexpected error (line " + str(sys.exc_info()[-1].tb_lineno) + "): " + str(sys.exc_info()[0]))

def searchSubtitles(**kwargs):
    try:
        headers = {
            "User-Agent": f"{APP_NAME} v{APP_VERSION}",
            "Api-key": f"{APP_API_KEY}"
        }

        query_params = urllib.parse.urlencode(kwargs)
        url = f"{API_URL_SEARCH}?{query_params}"
        req = urllib_request_Request(url, headers=headers)
        with urllib_request_urlopen(req) as response:
            response_data = json.loads(response.read().decode('utf-8'))

        #print("searchSubtitles() response data: " + str(response_data))
        return response_data

    except (urllib.error.HTTPError, urllib.error.URLError) as err:
        print("Urllib error (", err.code, ") ", err.reason)
    except Exception:
        print("Unexpected error (line " + str(sys.exc_info()[-1].tb_lineno) + "): " + str(sys.exc_info()[0]))

def getSubtitlesInfo(USER_TOKEN, file_id):
    try:
        headers = {
            "User-Agent": f"{APP_NAME} v{APP_VERSION}",
            "Api-key": f"{APP_API_KEY}",
            "Authorization": f"Bearer {USER_TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "file_id": file_id
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib_request_Request(API_URL_DOWNLOAD, data=data, headers=headers)
        with urllib_request_urlopen(req) as response:
            response_data = json.loads(response.read().decode('utf-8'))

        #print("getSubtitlesInfo() response data:" + response_data)
        return response_data

    except (urllib.error.HTTPError, urllib.error.URLError) as err:
        print("Urllib error (", err.code, ") ", err.reason)
    except Exception:
        print("Unexpected error (line " + str(sys.exc_info()[-1].tb_lineno) + "): " + str(sys.exc_info()[0]))

def downloadSubtitles(USER_TOKEN, subURL, subPath):
    try:
        headers = {
            "User-Agent": f"{APP_NAME} v{APP_VERSION}",
            "Api-key": f"{APP_API_KEY}",
            "Authorization": f"Bearer {USER_TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        req = urllib_request_Request(subURL, headers=headers)
        with urllib_request_urlopen(req) as response:
            decodedStr = response.read().decode('utf-8')
            byteswritten = open(subPath, 'w', encoding='utf-8', errors='replace').write(decodedStr)
            if byteswritten > 0:
                return 0

        return 1

    except (urllib.error.HTTPError, urllib.error.URLError) as err:
        print("Urllib error (", err.code, ") ", err.reason)
    except Exception:
        print("Unexpected error (line " + str(sys.exc_info()[-1].tb_lineno) + "): " + str(sys.exc_info()[0]))

# ==== Rate-limit handling =====================================================

class OpenSubtitlesRateLimiter:
    def __init__(self, max_requests=10, time_window=60, min_delay=0.1, max_retries=3):
        """Rate-limited wrapper for urllib.request with OpenSubtitles 429 handling"""

        # max_requests: Maximum requests allowed in time_window (fallback)
        # time_window: Time window in seconds (fallback)
        # min_delay: Minimum delay between requests in seconds
        # max_retries: Maximum number of retry attempts for 429 errors

        self.max_requests = max_requests
        self.time_window = time_window
        self.min_delay = min_delay
        self.max_retries = max_retries

        self.request_times = deque()
        self.lock = Lock()
        self.last_request_time = 0

        self.api_limit = None
        self.api_remaining = None
        self.api_reset_time = None

    def _parse_rate_limit_headers(self, headers):
        """Parse OpenSubtitles rate limit headers"""
        try:
            if 'X-RateLimit-Limit' in headers:
                self.api_limit = int(headers['X-RateLimit-Limit'])
            if 'X-RateLimit-Remaining' in headers:
                self.api_remaining = int(headers['X-RateLimit-Remaining'])
            if 'X-RateLimit-Reset' in headers:
                # Convert to timestamp if needed
                reset_value = headers['X-RateLimit-Reset']
                if isinstance(reset_value, str) and reset_value.isdigit():
                    self.api_reset_time = int(reset_value)
                else:
                    self.api_reset_time = int(time.time()) + 60 # fallback
        except (ValueError, KeyError):
            pass # Ignore parsing errors, fall back to local rate limiting

    def _should_wait_for_api_limits(self):
        """Check if we should wait based on API-provided rate limit info"""
        if self.api_remaining is not None and self.api_remaining <= 0:
            if self.api_reset_time:
                current_time = int(time.time())
                if current_time < self.api_reset_time:
                    wait_time = self.api_reset_time - current_time
                    print(f"API rate limit exhausted. Waiting {wait_time}s until reset...")
                    return wait_time
        return 0

    def _wait_if_needed(self):
        """Implement rate limiting logic with API feedback"""
        with self.lock:
            current_time = time.time()

            # First check API-provided limits
            api_wait = self._should_wait_for_api_limits()
            if api_wait > 0:
                time.sleep(api_wait)
                current_time = time.time()

            # Fallback to local rate limiting if no API info
            if self.api_remaining is None:
                # Remove old requests outside the time window
                while self.request_times and current_time - self.request_times[0] > self.time_window:
                    self.request_times.popleft()

                # Check if we've hit the local rate limit
                if len(self.request_times) >= self.max_requests:
                    sleep_time = self.time_window - (current_time - self.request_times[0]) + 0.1
                    if sleep_time > 0:
                        print(f"Local rate limit reached. Sleeping for {sleep_time:.2f} seconds...")
                        time.sleep(sleep_time)
                        current_time = time.time()

            # Ensure minimum delay between requests
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_delay:
                sleep_time = self.min_delay - time_since_last
                time.sleep(sleep_time)
                current_time = time.time()

            # Record this request for local tracking
            self.request_times.append(current_time)
            self.last_request_time = current_time

    def _handle_429_retry(self, url, data, headers, retry_count=0):
        """Handle 429 responses with proper retry logic"""
        if retry_count >= self.max_retries:
            raise urllib.error.HTTPError(url, 429, "Max retries exceeded for 429 Too Many Requests", headers, None)

        try:
            # Create and execute request
            req = urllib.request.Request(
                url=url,
                data=data,
                headers=headers or {}
            )

            response = urllib.request.urlopen(req)

            # Parse rate limit headers from successful response
            self._parse_rate_limit_headers(response.headers)

            return response

        except urllib.error.HTTPError as e:
            if e.code == 406: # 406 Not Acceptable - Account out of downloads for 24hr period
                superPrint("error", "HTTP error!",
                           "OpenSubtitlesDownload encountered an <b>HTTP error</b>, sorry about that...<br><br>" + \
                           "Error: <b>HTTP 406 Not Acceptable</b> Account has exceeded daily download quota<br>" + \
                           "Your OpenSubtitles account is out of downloads for the current 24-hour period<br>." + \
                           "Please wait until your quota resets or upgrade your account.")
                sys.exit(1)

            if e.code == 429: # 429 Too Many Requests
                print(f"Received 429 Too Many Requests (attempt {retry_count + 1}/{self.max_retries})")

                # Parse rate limit headers from error response
                if hasattr(e, 'headers') and e.headers:
                    self._parse_rate_limit_headers(e.headers)

                # Get retry delay from Retry-After header or API reset time
                retry_after = None
                if hasattr(e, 'headers') and e.headers:
                    retry_after = e.headers.get('Retry-After')

                if retry_after:
                    wait_time = int(retry_after)
                    print(f"Retry-After header suggests waiting {wait_time} seconds")
                elif self.api_reset_time:
                    wait_time = max(1, self.api_reset_time - int(time.time()))
                    print(f"Using API reset time, waiting {wait_time} seconds")
                else:
                    # Exponential backoff as fallback
                    wait_time = min(300, (2 ** retry_count) * 10) # Cap at 5 minutes
                    print(f"Using exponential backoff, waiting {wait_time} seconds")

                time.sleep(wait_time)

                # Reset API remaining counter since we waited
                self.api_remaining = None

                # Recursive retry
                return self._handle_429_retry(url, data, headers, retry_count + 1)

            else:
                # Re-raise non-429 errors
                raise

    def Request(self, url, data=None, headers=None, origin_req_host=None, unverifiable=False, method=None):
        """
        Rate-limited replacement for urllib.request.Request with 429 handling
        Returns the actual response object, not just a Request object
        """
        self._wait_if_needed()

        # Convert headers dict to the format urllib expects
        if headers is None:
            headers = {}

        # Handle the request with 429 retry logic
        return self._handle_429_retry(url, data, headers)

class OpenSubtitlesRequestWrapper:
    """
    Wrapper that maintains the original urllib.request.Request interface
    but adds rate limiting and 429 handling behind the scenes
    """
    def __init__(self, max_requests=10, time_window=60, min_delay=0.1, max_retries=1):
        self.rate_limiter = OpenSubtitlesRateLimiter(max_requests, time_window, min_delay, max_retries)

    def Request(self, url, data=None, headers=None, origin_req_host=None, unverifiable=False, method=None):
        """
        Drop-in replacement for urllib.request.Request
        This returns a Request object like the original, but the actual HTTP call
        happens when you use urllib.request.urlopen()
        """
        # Create the request object as normal
        req = urllib.request.Request(
            url=url,
            data=data,
            headers=headers or {},
            origin_req_host=origin_req_host,
            unverifiable=unverifiable,
            method=method
        )

        # Add rate limiting metadata to the request object
        req._rate_limiter = self.rate_limiter
        return req

# Enhanced urlopen function that handles the rate limiting
def rate_limited_urlopen(url_or_request, data=None, timeout=None):
    """Rate-limited replacement for urllib.request.urlopen """
    if hasattr(url_or_request, '_rate_limiter'):
        # This is our wrapped request object
        rate_limiter = url_or_request._rate_limiter
        return rate_limiter.Request(
            url=url_or_request.full_url,
            data=url_or_request.data,
            headers=dict(url_or_request.headers)
        )
    else:
        # Fallback to regular urlopen for unwrapped requests
        return urllib.request.urlopen(url_or_request, data, timeout)

# Global instances # Adjust these parameters based on OpenSubtitles API documentation
request_wrapper = OpenSubtitlesRequestWrapper(
    max_requests=40,    # Conservative limit (adjust based on your API tier)
    time_window=10,     # 10-second windows for responsive limiting
    min_delay=0.25,     # 250ms minimum between requests
    max_retries=5       # Retry 429 errors up to 5 times
)

def urllib_request_Request(*args, **kwargs):
    """Drop-in replacement for urllib.request.Request with OpenSubtitles rate limiting"""
    return request_wrapper.Request(*args, **kwargs)

def urllib_request_urlopen(*args, **kwargs):
    """Drop-in replacement for urllib.request.urlopen with rate limiting"""
    return rate_limited_urlopen(*args, **kwargs)

# ==============================================================================
# ==== Main program (execution starts here) ====================================
# ==============================================================================

# ==== Exit code returned by the software. You can use them to improve scripting behaviours.
# 0: Success, and subtitles downloaded
# 1: Success, but no subtitles found or downloaded
# 2: Failure

ExitCode = 2

# ==== File and language lists initialization

videoPathList = []
languageList = []

currentVideoPath = u""
currentLanguage = u""

# ==== Environment parsing

if osd_username == '':
    osd_username = os.getenv('OSD_ENV_USERNAME', '')

if osd_password == '':
    osd_password = os.getenv('OSD_ENV_PASSWORD', '')

# ==== Argument parsing

# Get OpenSubtitlesDownload.py script absolute path
if os.path.isabs(sys.argv[0]):
    scriptPath = sys.argv[0]
else:
    scriptPath = os.getcwd() + "/" + str(sys.argv[0])

# Setup ArgumentParser
parser = argparse.ArgumentParser(prog='OpenSubtitlesDownload.py',
                                 description='Automatically find and download the right subtitles for your favorite videos!',
                                 formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('--cli', help="Force CLI mode", action='store_true')
parser.add_argument('-g', '--gui', help="Select the GUI you want from: auto, kde, gnome, cli (default: auto)")
parser.add_argument('-u', '--username', help="Set opensubtitles.com account username")
parser.add_argument('-p', '--password', help="Set opensubtitles.com account password")
parser.add_argument('-l', '--lang', help="Specify the language in which the subtitles should be downloaded (default: en).\nSyntax:\n-l en,fr: search in both language")
parser.add_argument('-s', '--search', help="Search mode: hash, filename, hash_then_filename, hash_and_filename (default: hash_then_filename)")
parser.add_argument('-t', '--select', help="Selection mode: manual, default, auto")
parser.add_argument('-a', '--auto', help="Force automatic selection and download of the best subtitles found", action='store_true')
parser.add_argument('-i', '--skip', help="Skip search if an existing subtitles file is detected", action='store_true')
parser.add_argument('-o', '--output', help="Override subtitles download path, instead of next to their video file")
parser.add_argument('-x', '--suffix', help="Force language code file suffix", action='store_true')
parser.add_argument('--noai', help="Ignore AI or machine translated subtitles", action='store_true')
parser.add_argument('--nohi', help="Ignore HI (hearing impaired) subtitles", action='store_true')
parser.add_argument('searchPathList', help="The video file(s) or folder(s) for which subtitles should be searched and downloaded", nargs='+')
arguments = parser.parse_args()

# Handle arguments
if arguments.cli:
    opt_gui = 'cli'
if arguments.gui:
    opt_gui = arguments.gui
if arguments.username and arguments.password:
    osd_username = arguments.username
    osd_password = arguments.password
if arguments.lang:
    opt_languages = arguments.lang
if arguments.search:
    opt_search_mode = arguments.search
if arguments.skip:
    opt_search_overwrite = False
if arguments.select:
    opt_selection_mode = arguments.select
if arguments.auto:
    opt_selection_mode = 'auto'
if arguments.output:
    opt_output_path = arguments.output
if arguments.suffix:
    opt_language_suffix = 'on'
if arguments.noai:
    opt_ignore_ai_translated = True
if arguments.nohi:
    opt_ignore_hi = True

# GUI auto detection
if opt_gui == 'auto':
    # Note: "ps cax" only output the first 15 characters of the executable's names
    ps = str(subprocess.Popen(['ps', 'cax'], stdout=subprocess.PIPE).communicate()[0]).split('\n')
    for line in ps:
        if ('gnome-session' in line) or ('cinnamon-sessio' in line) or ('mate-session' in line) or ('xfce4-session' in line):
            opt_gui = 'gnome'
            break
        elif 'ksmserver' in line:
            opt_gui = 'kde'
            break

# Sanitize some settings
if opt_gui not in ['gnome', 'kde', 'cli']:
    opt_gui = 'cli'
    opt_search_mode = 'hash_then_filename'
    opt_selection_mode = 'auto'
    print("Unknown GUI, falling back to an automatic CLI mode")

if opt_search_mode not in ['hash', 'filename', 'hash_then_filename', 'hash_and_filename']:
    opt_search_mode = 'hash_then_filename'

if opt_selection_mode not in ['manual', 'default', 'auto']:
    opt_selection_mode = 'default'

# ==== Various checks

# Check for Python 3.6
if pythonChecker() is False:
    sys.exit(2)

# Check for the necessary tools (must be done after GUI auto detection)
if dependencyChecker() is False:
    sys.exit(2)

# Check for OSD credentials
if not osd_username or not osd_password:
    superPrint("warning", "OpenSubtitles.com account required!", "A valid account from OpenSubtitles.com is <b>REQUIRED</b>, please register on the website!")
    sys.exit(2)

# ==== Count languages selected for this search

if isinstance(opt_languages, list):
    languageList = opt_languages
else:
    languageList = opt_languages.split(',')

languageCount_search = len(languageList)

# ==== Get video paths, validate them, and if needed check if subtitles already exists

for i in arguments.searchPathList:
    path = os.path.abspath(i)
    if os.path.isdir(path): # if it's a folder
        if opt_gui == 'cli': # check all of the folder's (recursively)
            for root, _, items in os.walk(path):
                for item in items:
                    localPath = os.path.join(root, item)
                    if checkFileValidity(localPath):
                        if opt_search_overwrite or (not opt_search_overwrite and not checkSubtitlesExists(localPath)):
                            videoPathList.append(localPath)
        else: # check all of the folder's files
            for item in os.listdir(path):
                localPath = os.path.join(path, item)
                if checkFileValidity(localPath):
                    if opt_search_overwrite or (not opt_search_overwrite and not checkSubtitlesExists(localPath)):
                        videoPathList.append(localPath)
    elif checkFileValidity(path): # if it is a file
        if opt_search_overwrite or (not opt_search_overwrite and not checkSubtitlesExists(path)):
            videoPathList.append(path)

# If videoPathList is empty, abort!
if not videoPathList:
    sys.exit(1)

# ==== Instances dispatcher ====================================================

# The first video file will be processed by this instance
currentVideoPath = videoPathList[0]
videoPathList.pop(0)

# The remaining file(s) are dispatched to new instance(s) of this script
for videoPathDispatch in videoPathList:

    # Pass settings
    command = [ sys.executable, scriptPath,
                "-g", opt_gui, "-s", opt_search_mode, "-t", opt_selection_mode, "-l", opt_languages ]

    if not opt_search_overwrite:
        command.append("-i")

    if opt_language_suffix == 'on':
        command.append("-x")

    if opt_output_path:
        command.append("-o")
        command.append(opt_output_path)

    if arguments.username and arguments.password:
        command.append("-u")
        command.append(arguments.username)
        command.append("-p")
        command.append(arguments.password)

    # Pass video file
    command.append(videoPathDispatch)

    # Do not spawn too many instances at once, avoid error '429 Too Many Requests'
    time.sleep(2)

    if opt_gui == 'cli' and opt_selection_mode != 'auto':
        # Synchronous call
        process_videoDispatched = subprocess.call(command)
    else:
        # Asynchronous call
        process_videoDispatched = subprocess.Popen(command)

# ==== Search and download subtitles ===========================================

try:
    USER_TOKEN = []
    subtitlesResultList = []
    languageCount_results = 0

    ## Get file hash, size and name
    videoTitle = u''
    videoHash = hashFile(currentVideoPath)
    videoSize = os.path.getsize(currentVideoPath)
    videoFileName = os.path.basename(currentVideoPath)

    ## Search for subtitles
    try:
        if (opt_search_mode == 'hash_and_filename'):
            subtitlesResultList = searchSubtitles(moviehash=videoHash, query=videoFileName, languages=opt_languages)
            #print(f"SEARCH BY HASH AND NAME >>>>> length {len(subtitlesResultList['data'])} >>>>> {subtitlesResultList['data']}")
        else:
            if any(mode in opt_search_mode for mode in ['hash_then_filename', 'hash']):
                subtitlesResultList = searchSubtitles(moviehash=videoHash, languages=opt_languages)
                #print(f"SEARCH BY HASH >>>>> length {len(subtitlesResultList['data'])} >>>>> {subtitlesResultList['data']}")
            if ((opt_search_mode == 'filename') or
                (opt_search_mode == 'hash_then_filename' and len(subtitlesResultList['data']) == 0)):
                subtitlesResultList = searchSubtitles(query=videoFileName, languages=opt_languages)
                #print(f"SEARCH BY NAME >>>>> length {len(subtitlesResultList['data'])} >>>>> {subtitlesResultList['data']}")

    except Exception:
        superPrint("error", "Search error!", "Unable to reach opensubtitles.com servers!<br><b>Search error</b>")
        sys.exit(2)

    ## Parse the results of the search query
    if subtitlesResultList and 'data' in subtitlesResultList and len(subtitlesResultList['data']) > 0:
        # Mark search as successful
        languageCount_results += 1

        subName = u''
        subIndex = 0

        # If there is only one subtitles (matched by file hash), auto-select it (except in CLI mode)
        if (len(subtitlesResultList['data']) == 1) and (subtitlesResultList['data'][0]['attributes'].get('moviehash_match', False) == True):
            if opt_selection_mode != 'manual':
                subName = subtitlesResultList['data'][0]['attributes']['files'][0]['file_id']

        # Check if we have a valid title, found by hash
        for item in subtitlesResultList['data']:
            if item['attributes'].get('moviehash_match', False) == True:
                videoTitle = item['attributes']['feature_details']['movie_name']
                break

        # If there is more than one subtitles and opt_selection_mode != 'auto',
        # then let the user decide which one will be downloaded
        if not subName:
            if opt_selection_mode == 'auto':
                # Automatic subtitles selection
                (subName, subIndex) = selectionAuto(subtitlesResultList, languageList)
            else:
                # Go through the list of subtitles and handle 'auto' settings activation
                for item in subtitlesResultList['data']:
                    if opt_selection_match == 'auto':
                        if (opt_search_mode == 'hash_and_filename' or opt_search_mode == 'hash_then_filename'):
                            if item['attributes'].get('moviehash_match', False) == False:
                                opt_selection_match = 'on'
                    if opt_selection_language == 'auto' and languageCount_search > 1:
                        opt_selection_language = 'on'
                    if opt_selection_hi == 'auto' and item['attributes'].get('hearing_impaired', False) == True:
                        opt_selection_hi = 'on'
                    if opt_selection_rating == 'auto' and item['attributes']['ratings'] != '0.0':
                        opt_selection_rating = 'on'
                    if opt_selection_count == 'auto':
                        opt_selection_count = 'on'
                    if opt_selection_fps == 'auto' and item['attributes'].get('fps', '0.0') != '0.0':
                        opt_selection_fps = 'on'

                # Spaw selection window
                if opt_gui == 'gnome':
                    (subName, subIndex) = selectionGnome(subtitlesResultList)
                elif opt_gui == 'kde':
                    (subName, subIndex) = selectionKDE(subtitlesResultList)
                else: # CLI
                    (subName, subIndex) = selectionCLI(subtitlesResultList)

        ## At this point a subtitles should be selected
        if subName:
            # Log-in to the API
            USER_TOKEN = getUserToken(username=osd_username, password=osd_password)

            # Prepare download
            fileId = subtitlesResultList['data'][int(subIndex)]['attributes']['files'][0]['file_id']
            fileInfo = getSubtitlesInfo(USER_TOKEN, fileId)

            # Quote the URL to avoid characters like brackets () causing errors in wget command below
            subURL = fileInfo['link']
            subSuffix = subURL.split('.')[-1].strip("'")
            subLangName = subtitlesResultList['data'][int(subIndex)]['attributes']['language']
            subPath = u''

            if opt_output_path and os.path.isdir(os.path.abspath(opt_output_path)):
                # Use the output path provided by the user
                subPath = os.path.abspath(opt_output_path) + "/" + currentVideoPath.rsplit('.', 1)[0].rsplit('/', 1)[1] + '.' + subSuffix
            else:
                # Use the path of the input video, and the suffix of the subtitles file
                subPath = currentVideoPath.rsplit('.', 1)[0] + '.' + subSuffix

            # Write language code into the filename?
            if opt_language_suffix == 'on':
                subPath = subPath.rsplit('.', 1)[0] + opt_language_suffix_separator + subtitlesResultList['data'][int(subIndex)]['attributes']['language'] + '.' + subSuffix

            # Empty videoTitle? Use filename
            if not videoTitle:
                videoTitle = videoFileName

            ## Download and unzip the selected subtitles
            if opt_gui == 'gnome':
                # Escape non-alphanumeric characters from the subtitles download path for wget, and video title for zenity
                subPathEscaped = escapePath_wget(subPath)
                videoTitleEscaped = escapeGUI_zenity(videoTitle)
                # Download with wget, piped into zenity --progress
                process_subtitlesDownload = subprocess.call(f'(wget -q -O "{subPathEscaped}" "{subURL}") 2>&1 ' +
                                                             '| (zenity --auto-close --progress --pulsate --title="Downloading subtitles, please wait..." ' +
                                                            f'--text="Downloading <b>{subLangName}</b> subtitles for <b>{videoTitleEscaped}</b>...")', shell=True)
            else:
                if opt_gui == 'cli':
                    print(f">> Downloading '{subLangName}' subtitles for '{videoTitle}'")
                process_subtitlesDownload = downloadSubtitles(USER_TOKEN, fileInfo['link'], subPath)

            # If an error occurs, say so
            if process_subtitlesDownload != 0:
                superPrint("error", "Subtitling error!", f"An error occurred while downloading or writing <b>{subLangName}</b> subtitles for <b>{videoTitle}</b>.")
                sys.exit(2)

            ## HOOK # Use a secondary tool on the subtitles file after a successful download?
            if process_subtitlesDownload == 0 and len(custom_command) > 0:
                subPathEscaped = escapePath_wget(subPath)
                process_subtitlesDownload = subprocess.call(f'{custom_command} "{subPathEscaped}"', shell=True)

    ## Print a message if no subtitles have been found, for any of the languages
    if languageCount_results == 0:
        superPrint("info", "No subtitles available :-(", f"<b>No subtitles found</b> for this video:<br><i>{videoFileName}</i>")
        ExitCode = 1
    else:
        ExitCode = 0

except KeyboardInterrupt:
    sys.exit(1)

except urllib.error.HTTPError as e:
    superPrint("error", "Network error", "Network error: " + e.reason)

except (OSError, IOError, RuntimeError, AttributeError, TypeError, NameError, KeyError):
    # An unknown error occur, let's apologize before exiting
    superPrint("error", "Unexpected error!",
               "OpenSubtitlesDownload encountered an <b>unknown error</b>, sorry about that...<br><br>" + \
               "Error: <b>" + str(sys.exc_info()[0]).replace('<', '[').replace('>', ']') + "</b><br>" + \
               "Line: <b>" + str(sys.exc_info()[-1].tb_lineno) + "</b><br><br>" + \
               "Just to be safe, please check:<br>" + \
               "- Your Internet connection status<br>" + \
               "- www.opensubtitles.com availability<br>" + \
               "- Your download limits (10 subtitles per 24h for non VIP users)<br>" + \
               "- That are using the latest version of this software ;-)")

except Exception:
    # Catch unhandled exceptions but do not spawn an error window
    print("Unexpected error (line " + str(sys.exc_info()[-1].tb_lineno) + "): " + str(sys.exc_info()[0]))
