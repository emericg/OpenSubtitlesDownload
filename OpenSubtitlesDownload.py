#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# OpenSubtitlesDownload.py / Version 6.2
# This software is designed to help you find and download subtitles for your favorite videos!

# You can browse the project's GitHub page:
# - https://github.com/emericg/OpenSubtitlesDownload

# Learn much more about it on the wiki:
# - https://github.com/emericg/OpenSubtitlesDownload/wiki

# Copyright (c) 2024 by Emeric GRANGE <emeric.grange@gmail.com>
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
import re
import sys
import time
import shutil
import struct
import argparse
import mimetypes
import subprocess

import json
import urllib
import urllib.request
import urllib.error

# ==== OpenSubtitles.com server settings =======================================

# Track API availability:
# > https://opensubtitles.stoplight.io/docs/opensubtitles-api/e3750fd63a100-getting-started#system-status

# API endpoints
API_URL = 'https://api.opensubtitles.com/api/v1/'
API_URL_LOGIN = API_URL + 'login'
API_URL_LOGOUT = API_URL + 'logout'
API_URL_SEARCH = API_URL + 'subtitles'
API_URL_DOWNLOAD = API_URL + 'download'

# This application is registered
APP_NAME = 'OpenSubtitlesDownload'
APP_VERSION = '6.2'
APP_API_KEY = 'FNyoC96mlztsk3ALgNdhfSNapfFY9lOi'

# ==== OpenSubtitles.com account (required) ====================================

# You can use your opensubtitles.com VIP account to avoid "in-subtitles" advertisement and bypass download limits.
# Be careful about your password security, it will be stored right here in plain text...
# Can be overridden at run time with '-u' and '-p' arguments.
osd_username = ''
osd_password = ''

# ==== Language settings =======================================================

# Full guide: https://github.com/emericg/OpenSubtitlesDownload/wiki/Adjust-settings

# 1/ Change the search language by using any supported 2-letter (ISO 639-1) language code:
#    > https://en.wikipedia.org/wiki/List_of_ISO_639-2_codes
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
# - hash_then_filename (search by hash, then if no results by filename) (default)
# - hash_and_filename (search using both methods)
# - hash (search by hash only)
# - filename (search by filename only)
opt_search_mode = 'hash_then_filename'

# Search and download a subtitles even if a subtitles file already exists.
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

# Ignore AI translated subtitles?
opt_ignore_ai = False

# ==== GUI settings ============================================================

# Select your GUI. Can be overridden at run time with '--gui=xxx' argument.
# - auto (autodetection, fallback on CLI)
# - gnome (GNOME/GTK based environments, using 'zenity' backend)
# - kde (KDE/Qt based environments, using 'kdialog' backend)
# - cli (Command Line Interface)
opt_gui = 'auto'

# Change the subtitles selection GUI size:
opt_gui_width  = 920
opt_gui_height = 400

# Various GUI columns to show/hide during subtitles selection. You can set them to 'on', 'off' or 'auto'.
opt_selection_hi       = 'auto'
opt_selection_language = 'auto'
opt_selection_match    = 'auto'
opt_selection_rating   = 'off'
opt_selection_count    = 'off'

# ==== Check file path & type ==================================================

def checkFileValidity(path):
    """Check mimetype and/or file extension to detect valid video file"""
    if os.path.isfile(path) is False:
        superPrint("info", "File not found", "The file provided was not found:\n<i>" + path + "</i>")
        return False

    fileMimeType, encoding = mimetypes.guess_type(path)
    if fileMimeType is None:
        fileExtension = path.rsplit('.', 1)
        if fileExtension[1] not in ['avi', 'mov', 'mp4', 'mp4v', 'm4v', 'mkv', 'mk3d', 'webm', \
                                    'ts', 'mts', 'm2ts', 'ps', 'vob', 'evo', 'mpeg', 'mpg', \
                                    'asf', 'wm', 'wmv', 'rm', 'rmvb', 'divx', 'xvid']:
            #superPrint("error", "File type error!", "This file is not a video (unknown mimetype AND invalid file extension):\n<i>" + path + "</i>")
            return False
    else:
        fileMimeType = fileMimeType.split('/', 1)
        if fileMimeType[0] != 'video':
            #superPrint("error", "File type error!", "This file is not a video (unknown mimetype):\n<i>" + path + "</i>")
            return False

    return True

# ==== Check for existing subtitles file =======================================

def checkSubtitlesExists(path):
    """Check if a subtitles already exists for the current file"""
    extList = ['srt', 'sub', 'mpl', 'webvtt', 'dfxp', 'txt',
               'sbv', 'smi', 'ssa', 'ass', 'usf']
    sepList = ['_', '-', '.']
    tryList = []

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
                superPrint("info", "Subtitles already downloaded!", "A subtitles file already exists for this file:\n<i>" + subPath + "</i>")
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
            superPrint("error", "File size error!", "File size error while generating hash for this file:\n<i>" + path + "</i>")
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
        superPrint("error", "I/O error!", "Input/Output error while generating hash for this file:\n<i>" + path + "</i>")
        return "IOError"

    except Exception:
        print("Unexpected error (line " + str(sys.exc_info()[-1].tb_lineno) + "): " + str(sys.exc_info()[0]))

# ==== Super Print =============================================================
# priority: info, warning, error
# title: only for zenity and kdialog messages
# message: full text, with tags and breaks (tags will be cleaned up for CLI)

def superPrint(priority, title, message):
    """Print messages through terminal, zenity or kdialog"""
    if opt_gui == 'gnome':
        subprocess.call(['zenity', '--width=' + str(opt_gui_width), '--' + priority, '--title=' + title, '--text=' + message])
    elif opt_gui == 'kde':
        # Adapt to kdialog
        message = message.replace("\n", "<br>")
        message = message.replace('\\"', '"')
        if priority == 'warning':
            priority = 'sorry'
        elif priority == 'info':
            priority = 'msgbox'
        # Print message
        subprocess.call(['kdialog', '--geometry=' + str(opt_gui_width) + 'x' + str(opt_gui_height), '--title=' + title, '--' + priority + '=' + message])
    else:
        # Clean up format tags from the zenity string
        message = message.replace("\n\n", "\n")
        message = message.replace('\\"', '"')
        message = message.replace("<i>", "")
        message = message.replace("</i>", "")
        message = message.replace("<b>", "")
        message = message.replace("</b>", "")
        # Print message
        print(">> " + message)

# ==== GNOME selection window ==================================================

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

    # Generate selection window content
    for idx, item in enumerate(subtitlesResultList['data']):
        if opt_ignore_hi and item['attributes'].get('hearing_impaired', False) == True:
            continue
        if opt_ignore_ai and item['attributes'].get('ai_translated', False) == True:
            continue

        if item['attributes'].get('moviehash_match', False) == True:
            subtitlesMatchedByHash += 1
        else:
            subtitlesMatchedByName += 1

        subtitlesItems += f'{idx} "' + item['attributes']['files'][0]['file_name'] + '" '

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
            subtitlesItems += '"' + str(item['attributes']['download_count']) + '" '

    if subtitlesMatchedByName == 0:
        tilestr = ' --title="Subtitles for: ' + videoTitle + '"'
        textstr = ' --text="<b>Video title:</b> ' + videoTitle + '\n<b>File name:</b> ' + videoFileName + '"'
    elif subtitlesMatchedByHash == 0:
        tilestr = ' --title="Subtitles for: ' + videoFileName + '"'
        textstr = ' --text="Search results using file name, NOT video detection. <b>May be unreliable...</b>\n<b>File name:</b> ' + videoFileName + '" '
    else: # a mix of the two
        tilestr = ' --title="Subtitles for: ' + videoTitle + '"'
        textstr = ' --text="Search results using file name AND video detection.\n<b>Video title:</b> ' + videoTitle + '\n<b>File name:</b> ' + videoFileName + '"'

    # Spawn zenity "list" dialog
    process_subtitlesSelection = subprocess.Popen('zenity --width=' + str(opt_gui_width) + ' --height=' + str(opt_gui_height) + ' --list' + tilestr + textstr
                                                  + ' --column "id" --column="Available subtitles" ' + columnHi + columnLn + columnMatch + columnRate + columnCount + subtitlesItems
                                                  + ' --hide-column=1 --print-column=ALL', shell=True, stdout=subprocess.PIPE)

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

# ==== KDE selection window ====================================================

def selectionKDE(subtitlesResultList):
    """KDE subtitles selection window using kdialog"""
    subtitlesSelectedName = u''
    subtitlesSelectedIndex = -1

    subtitlesItems = u''
    subtitlesMatchedByHash = 0
    subtitlesMatchedByName = 0

    # Generate selection window content
    # TODO doesn't support additional columns
    index = 0

    for idx, item in enumerate(subtitlesResultList['data']):
        if opt_ignore_hi and item['attributes'].get('hearing_impaired', False) == True:
            continue
        if opt_ignore_ai and item['attributes'].get('ai_translated', False) == True:
            continue

        if item['attributes'].get('moviehash_match', False) == True:
            subtitlesMatchedByHash += 1
        else:
            subtitlesMatchedByName += 1

        # key + subtitles name
        subtitlesItems += str(index) + ' "' + item['attributes']['files'][0]['file_name'] + '" '
        index += 1

    if subtitlesMatchedByName == 0:
        tilestr = ' --title="Subtitles for ' + videoTitle + '"'
        menustr = ' --menu="<b>Video title:</b> ' + videoTitle + '<br><b>File name:</b> ' + videoFileName + '" '
    elif subtitlesMatchedByHash == 0:
        tilestr = ' --title="Subtitles for ' + videoFileName + '"'
        menustr = ' --menu="Search results using file name, NOT video detection. <b>May be unreliable...</b><br><b>File name:</b> ' + videoFileName + '" '
    else: # a mix of the two
        tilestr = ' --title="Subtitles for ' + videoTitle + '" '
        menustr = ' --menu="Search results using file name AND video detection.<br><b>Video title:</b> ' + videoTitle + '<br><b>File name:</b> ' + videoFileName + '" '

    # Spawn kdialog "radiolist"
    process_subtitlesSelection = subprocess.Popen('kdialog --geometry=' + str(opt_gui_width) + 'x' + str(opt_gui_height) + tilestr + menustr + subtitlesItems,
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
        if opt_ignore_ai and item['attributes'].get('ai_translated', False) == True:
            continue

        subtitlesItemPre = u''
        subtitlesItem = u'"' + item['attributes']['files'][0]['file_name'] + '"'
        subtitlesItemPost = u''

        if opt_selection_language == 'on':
            subtitlesItemPre += '> ' + item['attributes']['language'].upper() + ' > '
        if opt_selection_hi == 'on' and item['attributes'].get('hearing_impaired', False) == True:
            subtitlesItemPre += '> "HI" > '
        if opt_selection_match == 'on':
            if item['attributes'].get('moviehash_match', False) == True:
                subtitlesItemPre += '> (hash) > '
            else:
                subtitlesItemPre += '> (name) > '
        if opt_selection_rating == 'on':
            subtitlesItemPost += ' > "Rating: ' + str(item['attributes']['ratings']) + '"'
        if opt_selection_count == 'on':
            subtitlesItemPost += ' > "Downloads: ' + str(item['attributes']['download_count']) + '"'

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

# ==== Check dependencies ======================================================

def pythonChecker():
    """Check the availability of python 3 interpreter"""
    if sys.version_info < (3, 0):
        superPrint("error", "Wrong Python version", "You need <b>Python 3</b> to use OpenSubtitlesDownload.")
        return False
    return True

def dependencyChecker():
    """Check the availability of tools used as dependencies"""
    if opt_gui != 'cli':
        for tool in ['gunzip', 'wget']:
            path = shutil.which(tool)
            if path is None:
                superPrint("error", "Missing dependency!", "The <b>'" + tool + "'</b> tool is not available, please install it!")
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
        req = urllib.request.Request(API_URL_LOGIN, data=data, headers=headers)
        with urllib.request.urlopen(req) as response:
            response_data = json.loads(response.read().decode('utf-8'))

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

        req = urllib.request.Request(API_URL_LOGOUT, headers=headers)
        with urllib.request.urlopen(req) as response:
            response_data = json.loads(response.read().decode('utf-8'))

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
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            response_data = json.loads(response.read().decode('utf-8'))

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
        req = urllib.request.Request(API_URL_DOWNLOAD, data=data, headers=headers)
        with urllib.request.urlopen(req) as response:
            result = response.read().decode('utf-8')

        return json.loads(result)

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

        req = urllib.request.Request(subURL, headers=headers)
        with urllib.request.urlopen(req) as response:
            decodedStr = response.read().decode('utf-8')
            byteswritten = open(subPath, 'w', encoding='utf-8', errors='replace').write(decodedStr)
            if byteswritten > 0:
                return 0

        return 1

    except (urllib.error.HTTPError, urllib.error.URLError) as err:
        print("Urllib error (", err.code, ") ", err.reason)
    except Exception:
        print("Unexpected error (line " + str(sys.exc_info()[-1].tb_lineno) + "): " + str(sys.exc_info()[0]))



# ==============================================================================
# ==== Main program (execution starts here) ====================================
# ==============================================================================

# ==== Exit code returned by the software. You can use them to improve scripting behaviours.
# 0: Success, and subtitles downloaded
# 1: Success, but no subtitles found or downloaded
# 2: Failure

ExitCode = 2

# ==== File and language lists

videoPathList = []
languageList = []

currentVideoPath = ""
currentLanguage = ""

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
    opt_ignore_ai = True
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

# Check for Python 3
if pythonChecker() is False:
    sys.exit(2)

# Check for the necessary tools (must be done after GUI auto detection)
if dependencyChecker() is False:
    sys.exit(2)

# Check for OSD credentials
if not osd_username or not osd_password:
    superPrint("warning", "OpenSubtitles.com account required!", "A valid OpenSubtitles.com account is <b>REQUIRED</b>, please register on the website!")
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
    time.sleep(3)

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

        if any(mode in opt_search_mode for mode in ['hash_then_filename', 'hash']):
            subtitlesResultList = searchSubtitles(moviehash=videoHash, languages=opt_languages)
            #print(f"SEARCH BY HASH >>>>> length {len(subtitlesResultList['data'])} >>>>> {subtitlesResultList['data']}")

        if ((opt_search_mode == 'filename') or
            (opt_search_mode == 'hash_then_filename' and len(subtitlesResultList['data']) == 0)):
            subtitlesResultList = searchSubtitles(query=videoFileName, languages=opt_languages)
            #print(f"SEARCH BY NAME >>>>> length {len(subtitlesResultList['data'])} >>>>> {subtitlesResultList['data']}")

    except Exception:
        superPrint("error", "Search error!", "Unable to reach opensubtitles.com servers!\n<b>Search error</b>")
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

        # Title and filename may need string sanitizing to avoid zenity/kdialog handling errors
        if opt_gui != 'cli':
            videoTitle = videoTitle.replace('"', '\\"')
            videoTitle = videoTitle.replace("'", "\\'")
            videoTitle = videoTitle.replace('`', '\\`')
            videoTitle = videoTitle.replace("&", "&amp;")
            videoFileName = videoFileName.replace('"', '\\"')
            videoFileName = videoFileName.replace("'", "\\'")
            videoFileName = videoFileName.replace('`', '\\`')
            videoFileName = videoFileName.replace("&", "&amp;")

        # If there is more than one subtitles and opt_selection_mode != 'auto',
        # then let the user decide which one will be downloaded
        if not subName:
            if opt_selection_mode == 'auto':
                # Automatic subtitles selection
                (subName, subIndex) = selectionAuto(subtitlesResultList, languageList)
            else:
                # Go through the list of subtitles and handle 'auto' settings activation
                for item in subtitlesResultList['data']:
                    if opt_selection_match == 'auto' and opt_search_mode == 'hash_and_filename':
                        opt_selection_match = 'on'
                    if opt_selection_language == 'auto' and languageCount_search > 1:
                        opt_selection_language = 'on'
                    if opt_selection_hi == 'auto' and item['attributes'].get('hearing_impaired', False) == True:
                        opt_selection_hi = 'on'
                    if opt_selection_rating == 'auto' and item['attributes']['ratings'] != '0.0':
                        opt_selection_rating = 'on'
                    if opt_selection_count == 'auto':
                        opt_selection_count = 'on'

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

            # quote the URL to avoid characters like brackets () causing errors in wget command below
            subURL = f"\'{fileInfo['link']}\'"
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

            # Escape non-alphanumeric characters from the subtitles download path
            if opt_gui != 'cli':
                subPath = re.escape(subPath)
                subPath = subPath.replace('"', '\\"')
                subPath = subPath.replace("'", "\\'")
                subPath = subPath.replace('`', '\\`')

            # Empty videoTitle?
            if not videoTitle:
                videoTitle = videoFileName

            ## Download and unzip the selected subtitles
            if opt_gui == 'gnome':
                process_subtitlesDownload = subprocess.call("(wget -q -O " + subPath + " " + subURL + ") 2>&1"
                                                            + ' | (zenity --auto-close --progress --pulsate --title="Downloading subtitles, please wait..." --text="Downloading <b>'
                                                            + subLangName + '</b> subtitles for <b>' + videoTitle + '</b>...")', shell=True)
            elif opt_gui == 'kde':
                process_subtitlesDownload = subprocess.call("(wget -q -O " + subPath + " " + subURL + ") 2>&1", shell=True)
            else: # CLI
                print(">> Downloading '" + subtitlesResultList['data'][subIndex]['attributes']['language'] + "' subtitles for '" + videoTitle + "'")
                process_subtitlesDownload = downloadSubtitles(USER_TOKEN, fileInfo['link'], subPath)

            # If an error occurs, say so
            if process_subtitlesDownload != 0:
                superPrint("error", "Subtitling error!",
                           "An error occurred while downloading or writing '<b>" + subtitlesResultList['data'][subIndex]['attributes']['language'] + "</b>'" +
                           "subtitles for <b>" + videoTitle + "</b>.")
                sys.exit(2)

        ## HOOK # Use a secondary tool after a successful download?
        #process_subtitlesDownload = subprocess.call("(custom_command" + " " + subPath + ") 2>&1", shell=True)

    ## Print a message if no subtitles have been found, for any of the languages
    if languageCount_results == 0:
        superPrint("info", "No subtitles available :-(", '<b>No subtitles found</b> for this video:\n<i>' + videoFileName + '</i>')
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
               "OpenSubtitlesDownload encountered an <b>unknown error</b>, sorry about that...\n\n" + \
               "Error: <b>" + str(sys.exc_info()[0]).replace('<', '[').replace('>', ']') + "</b>\n" + \
               "Line: <b>" + str(sys.exc_info()[-1].tb_lineno) + "</b>\n\n" + \
               "Just to be safe, please check:\n" + \
               "- Your Internet connection status\n" + \
               "- www.opensubtitles.com availability\n" + \
               "- Your download limits (10 subtitles per 24h for non VIP users)\n" + \
               "- That are using the latest version of this software ;-)")

except Exception:
    # Catch unhandled exceptions but do not spawn an error window
    print("Unexpected error (line " + str(sys.exc_info()[-1].tb_lineno) + "): " + str(sys.exc_info()[0]))
