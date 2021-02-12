#!/usr/bin/env python
# -*- coding: utf-8 -*-

# OpenSubtitlesDownload.py / Version 4.2
# This software is designed to help you find and download subtitles for your favorite videos!

# You can browse the project's GitHub page:
# - https://github.com/emericg/OpenSubtitlesDownload
# Learn much more about configuring OpenSubtitlesDownload.py on its wiki:
# - https://github.com/emericg/OpenSubtitlesDownload/wiki

# Copyright (c) 2020 by Emeric GRANGE <emeric.grange@gmail.com>
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

# Contributors / special thanks:
# Thiago Alvarenga Lechuga <thiagoalz@gmail.com> for his work on the 'Windows CLI' and the 'folder search'
# jeroenvdw for his work on the 'subtitles automatic selection' and the 'search by filename'
# Gui13 for his work on the arguments parsing
# Tomáš Hnyk <tomashnyk@gmail.com> for his work on the 'multiple language' feature
# Carlos Acedo <carlos@linux-labs.net> for his work on the original script

import os
import re
import sys
import time
import gzip
import struct
import hashlib
import argparse
import mimetypes
import subprocess

if sys.version_info >= (3, 0):
    import shutil
    import urllib.request
    from xmlrpc.client import ServerProxy, Error
else: # python2
    import urllib
    from xmlrpclib import ServerProxy, Error

# ==== OpenSubtitles.org server settings =======================================

# XML-RPC server domain for opensubtitles.org:
osd_server = ServerProxy('https://api.opensubtitles.org/xml-rpc')

# You can use your opensubtitles.org VIP account to avoid "in-subtitles" advertisement and bypass download limits.
# Be careful about your password security, it will be stored right here in plain text...
# You can also change opensubtitles.org language, it will be used for error codes and stuff.
# Can be overridden at run time with '-u' and '-p' arguments.
osd_username = ''
osd_password = ''
osd_language = 'en'

# ==== Language settings =======================================================

# 1/ Change the search language by using any supported 3-letter (ISO639-2) language code:
#    > Supported language codes: https://www.opensubtitles.org/addons/export_languages.php
#    > Full guide: https://github.com/emericg/OpenSubtitlesDownload/wiki/Adjust-settings
#    > Ex: opt_languages = ['eng']
# 2/ Search for subtitles in several languages (at once, select one) by using multiple codes separated by a comma:
#    > Ex: opt_languages = ['eng,fre']
# 3/ Search for subtitles in several languages (separately, select one of each) by using multiple codes separated by a comma:
#    > Ex: opt_languages = ['eng','fre']
opt_languages = ['eng']

# Write language code (ex: _en) at the end of the subtitles file. 'on', 'off' or 'auto'.
# If you are regularly searching for several language at once, you sould use 'on'.
opt_language_suffix = 'auto'
# - auto: same language code size than set in opt_languages
# - 2: 2-letter (ISO639-3) language code
# - 3: 3-letter (ISO639-2) language code
opt_language_suffix_size = 'auto'
# Character used to separate file path from the language code (ex: file_en.srt).
opt_language_suffix_separator = '_'

# Force downloading and storing UTF-8 encoded subtitles files.
opt_force_utf8 = True

# ==== Search settings =========================================================

# Subtitles search mode. Can be overridden at run time with '-s' argument.
# - hash (search by hash only)
# - filename (search by filename only)
# - hash_then_filename (search by hash, then if no results by filename)
# - hash_and_filename (search using both methods)
opt_search_mode = 'hash_then_filename'

# Search and download a subtitles even if a subtitles file already exists.
opt_search_overwrite = True

# Subtitles selection mode. Can be overridden at run time with '-t' argument.
# - manual (always let you choose the subtitles you want)
# - default (in case of multiple results, let you choose the subtitles you want)
# - auto (automatically select the best subtitles found)
opt_selection_mode = 'default'

# Customize subtitles download path. Can be overridden at run time with '-o' argument.
# By default, subtitles are downloaded next to their video file.
opt_output_path = ''

# ==== GUI settings ============================================================

# Select your GUI. Can be overridden at run time with '--gui=xxx' argument.
# - auto (autodetection, fallback on CLI)
# - gnome (GNOME/GTK based environments, using 'zenity' backend)
# - kde (KDE/Qt based environments, using 'kdialog' backend)
# - cli (Command Line Interface)
opt_gui = 'auto'

# Change the subtitles selection GUI size:
opt_gui_width  = 720
opt_gui_height = 320

# Various GUI columns to show/hide during subtitles selection. You can set them to 'on', 'off' or 'auto'.
opt_selection_hi       = 'auto'
opt_selection_language = 'auto'
opt_selection_match    = 'auto'
opt_selection_rating   = 'off'
opt_selection_count    = 'off'

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

# ==== Check file path & type ==================================================

def checkFileValidity(path):
    """Check mimetype and/or file extension to detect valid video file"""
    if os.path.isfile(path) is False:
        return False

    fileMimeType, encoding = mimetypes.guess_type(path)
    if fileMimeType is None:
        fileExtension = path.rsplit('.', 1)
        if fileExtension[1] not in ['avi', 'mp4', 'mov', 'mkv', 'mk3d', 'webm', \
                                    'ts', 'mts', 'm2ts', 'ps', 'vob', 'evo', 'mpeg', 'mpg', \
                                    'm1v', 'm2p', 'm2v', 'm4v', 'movhd', 'movx', 'qt', \
                                    'mxf', 'ogg', 'ogm', 'ogv', 'rm', 'rmvb', 'flv', 'swf', \
                                    'asf', 'wm', 'wmv', 'wmx', 'divx', 'x264', 'xvid']:
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
    extList = ['srt', 'sub', 'sbv', 'smi', 'ssa', 'ass', 'usf']
    lngList = ['']

    if opt_language_suffix in ('on', 'auto'):
        for language in opt_languages:
            for l in list(language.split(',')):
                lngList.append(opt_language_suffix_separator + l)
                # Rough method to try 2 and 3 letters language codes
                if len(l) == 3: lngList.append(opt_language_suffix_separator + l[0:2])

    for ext in extList:
        for lng in lngList:
            subPath = path.rsplit('.', 1)[0] + lng + '.' + ext
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

# ==== GNOME selection window ==================================================

def selectionGnome(subtitlesResultList):
    """GNOME subtitles selection window using zenity"""
    subtitlesSelected = ''
    subtitlesItems = ''
    subtitlesMatchedByHash = 0
    subtitlesMatchedByName = 0
    columnHi = ''
    columnLn = ''
    columnMatch = ''
    columnRate = ''
    columnCount = ''

    # Generate selection window content
    for item in subtitlesResultList['data']:
        if item['MatchedBy'] == 'moviehash':
            subtitlesMatchedByHash += 1
        else:
            subtitlesMatchedByName += 1

        subtitlesItems += '"' + item['SubFileName'] + '" '

        if opt_selection_hi == 'on':
            columnHi = '--column="HI" '
            if item['SubHearingImpaired'] == '1':
                subtitlesItems += '"✔" '
            else:
                subtitlesItems += '"" '
        if opt_selection_language == 'on':
            columnLn = '--column="Language" '
            subtitlesItems += '"' + item['LanguageName'] + '" '
        if opt_selection_match == 'on':
            columnMatch = '--column="MatchedBy" '
            if item['MatchedBy'] == 'moviehash':
                subtitlesItems += '"HASH" '
            else:
                subtitlesItems += '"" '
        if opt_selection_rating == 'on':
            columnRate = '--column="Rating" '
            subtitlesItems += '"' + item['SubRating'] + '" '
        if opt_selection_count == 'on':
            columnCount = '--column="Downloads" '
            subtitlesItems += '"' + item['SubDownloadsCnt'] + '" '

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
    process_subtitlesSelection = subprocess.Popen('zenity --width=' + str(opt_gui_width) + ' --height=' + str(opt_gui_height) + ' --list' + tilestr + textstr \
        + ' --column="Available subtitles" ' + columnHi + columnLn + columnMatch + columnRate + columnCount + subtitlesItems, shell=True, stdout=subprocess.PIPE)

    # Get back the result
    result_subtitlesSelection = process_subtitlesSelection.communicate()

    # The results contain a subtitles?
    if result_subtitlesSelection[0]:
        if sys.version_info >= (3, 0):
            subtitlesSelected = str(result_subtitlesSelection[0], 'utf-8').strip("\n")
        else: # python2
            subtitlesSelected = str(result_subtitlesSelection[0]).strip("\n")

        # Hack against recent zenity version?
        if len(subtitlesSelected.split("|")) > 1:
            if subtitlesSelected.split("|")[0] == subtitlesSelected.split("|")[1]:
                subtitlesSelected = subtitlesSelected.split("|")[0]
    else:
        if process_subtitlesSelection.returncode == 0:
            subtitlesSelected = subtitlesResultList['data'][0]['SubFileName']

    # Return the result
    return subtitlesSelected

# ==== KDE selection window ====================================================

def selectionKde(subtitlesResultList):
    """KDE subtitles selection window using kdialog"""
    subtitlesSelected = ''
    subtitlesItems = ''
    subtitlesMatchedByHash = 0
    subtitlesMatchedByName = 0

    # Generate selection window content
    # TODO doesn't support additional columns
    index = 0
    for item in subtitlesResultList['data']:
        if item['MatchedBy'] == 'moviehash':
            subtitlesMatchedByHash += 1
        else:
            subtitlesMatchedByName += 1

        # key + subtitles name
        subtitlesItems += str(index) + ' "' + item['SubFileName'] + '" '
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
    process_subtitlesSelection = subprocess.Popen('kdialog --geometry=' + str(opt_gui_width) + 'x' + str(opt_gui_height) + tilestr + menustr + subtitlesItems, shell=True, stdout=subprocess.PIPE)

    # Get back the result
    result_subtitlesSelection = process_subtitlesSelection.communicate()

    # The results contain the key matching a subtitles?
    if result_subtitlesSelection[0]:
        if sys.version_info >= (3, 0):
            keySelected = int(str(result_subtitlesSelection[0], 'utf-8').strip("\n"))
        else: # python2
            keySelected = int(str(result_subtitlesSelection[0]).strip("\n"))

        subtitlesSelected = subtitlesResultList['data'][keySelected]['SubFileName']

    # Return the result
    return subtitlesSelected

# ==== CLI selection mode ======================================================

def selectionCLI(subtitlesResultList):
    """Command Line Interface, subtitles selection inside your current terminal"""
    subtitlesIndex = 0
    subtitlesItem = ''

    # Print video infos
    print("\n>> Title: " + videoTitle)
    print(">> Filename: " + videoFileName)

    # Print subtitles list on the terminal
    print(">> Available subtitles:")
    for item in subtitlesResultList['data']:
        subtitlesIndex += 1
        subtitlesItem = '"' + item['SubFileName'] + '" '

        if opt_selection_hi == 'on' and item['SubHearingImpaired'] == '1':
            subtitlesItem += '> "HI" '
        if opt_selection_language == 'on':
            subtitlesItem += '> "Language: ' + item['LanguageName'] + '" '
        if opt_selection_match == 'on':
            subtitlesItem += '> "MatchedBy: ' + item['MatchedBy'] + '" '
        if opt_selection_rating == 'on':
            subtitlesItem += '> "SubRating: ' + item['SubRating'] + '" '
        if opt_selection_count == 'on':
            subtitlesItem += '> "SubDownloadsCnt: ' + item['SubDownloadsCnt'] + '" '

        if item['MatchedBy'] == 'moviehash':
            print("\033[92m[" + str(subtitlesIndex) + "]\033[0m " + subtitlesItem)
        else:
            print("\033[93m[" + str(subtitlesIndex) + "]\033[0m " + subtitlesItem)

    # Ask user to selected a subtitles
    print("\033[91m[0]\033[0m Cancel search")
    sub_selection = -1
    while (sub_selection < 0 or sub_selection > subtitlesIndex):
        try:
            if sys.version_info >= (3, 0):
                sub_selection = int(input(">> Enter your choice (0-" + str(subtitlesIndex) + "): "))
            else: # python 2
                sub_selection = int(raw_input(">> Enter your choice (0-" + str(subtitlesIndex) + "): "))
        except KeyboardInterrupt:
            sys.exit(1)
        except:
            sub_selection = -1

    # Return the result
    if sub_selection == 0:
        print("Cancelling search...")
        return ""

    return subtitlesResultList['data'][sub_selection-1]['SubFileName']

# ==== Automatic selection mode ================================================

def selectionAuto(subtitlesResultList):
    """Automatic subtitles selection using filename match"""

    videoFileParts = videoFileName.replace('-', '.').replace(' ', '.').replace('_', '.').lower().split('.')
    languageListReversed = list(reversed(languageList))
    maxScore = -1

    for subtitle in subtitlesResultList['data']:
        score = 0
        # points to respect languages priority
        score += languageListReversed.index(subtitle['SubLanguageID']) * 100
        # extra point if the sub is found by hash
        if subtitle['MatchedBy'] == 'moviehash':
            score += 1
        # points for filename mach
        subFileParts = subtitle['SubFileName'].replace('-', '.').replace(' ', '.').replace('_', '.').lower().split('.')
        for subPart in subFileParts:
            for filePart in videoFileParts:
                if subPart == filePart:
                    score += 1
        if score > maxScore:
            maxScore = score
            subtitlesSelected = subtitle['SubFileName']

    return subtitlesSelected

# ==== Check dependencies ======================================================

def dependencyChecker():
    """Check the availability of tools used as dependencies"""

    if opt_gui != 'cli':
        if sys.version_info >= (3, 3):
            for tool in ['gunzip', 'wget']:
                path = shutil.which(tool)
                if path is None:
                    superPrint("error", "Missing dependency!", "The <b>'" + tool + "'</b> tool is not available, please install it!")
                    return False

    return True

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
parser.add_argument('-l', '--lang', help="Specify the language in which the subtitles should be downloaded (default: eng).\nSyntax:\n-l eng,fre: search in both language\n-l eng -l fre: download both language", nargs='?', action='append')
parser.add_argument('-i', '--skip', help="Skip search if an existing subtitles file is detected", action='store_true')
parser.add_argument('-s', '--search', help="Search mode: hash, filename, hash_then_filename, hash_and_filename (default: hash_then_filename)")
parser.add_argument('-t', '--select', help="Selection mode: manual, default, auto")
parser.add_argument('-a', '--auto', help="Force automatic selection and download of the best subtitles found", action='store_true')
parser.add_argument('-o', '--output', help="Override subtitles download path, instead of next their video file")
parser.add_argument('-x', '--suffix', help="Force language code file suffix", action='store_true')
parser.add_argument('-u', '--username', help="Set opensubtitles.org account username")
parser.add_argument('-p', '--password', help="Set opensubtitles.org account password")
parser.add_argument('searchPathList', help="The video file(s) or folder(s) for which subtitles should be searched and downloaded", nargs='+')

# Parse arguments
arguments = parser.parse_args()

# Handle arguments
if arguments.cli:
    opt_gui = 'cli'
if arguments.gui:
    opt_gui = arguments.gui
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
if arguments.lang:
    opt_languages = arguments.lang
if arguments.suffix:
    opt_language_suffix = 'on'
if arguments.username and arguments.password:
    osd_username = arguments.username
    osd_password = arguments.password

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

# ==== Check for the necessary tools (must be done after GUI auto detection)

if dependencyChecker() is False:
    sys.exit(2)

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
    command = [ sys.executable, scriptPath, "-g", opt_gui, "-s", opt_search_mode, "-t", opt_selection_mode ]

    for language in opt_languages:
        command.append("-l")
        command.append(language)

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

    # Pass file
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
    # ==== Connection to OpenSubtitlesDownload
    try:
        session = osd_server.LogIn(osd_username, hashlib.md5(osd_password[0:32].encode('utf-8')).hexdigest(), osd_language, 'opensubtitles-download 4.2')
    except Exception:
        # Retry once after a delay (could just be a momentary overloaded server?)
        time.sleep(3)
        try:
            session = osd_server.LogIn(osd_username, osd_password, osd_language, 'opensubtitles-download 4.2')
        except Exception:
            superPrint("error", "Connection error!", "Unable to reach OpenSubtitles.org servers!\n\nPlease check:\n" + \
                "- Your Internet connection status\n" + \
                "- www.opensubtitles.org availability\n" + \
                "The subtitles search and download service is powered by <a href=\"https://opensubtitles.org\">opensubtitles.org</a>.\n" + \
                "Be sure to donate if you appreciate the service provided!")
            sys.exit(2)

    # Login not accepted?
    if session['status'] != '200 OK':
        if session['status'] == '401 Unauthorized':
            superPrint("error", "Connection error!", "OpenSubtitles.org servers refused the connection: <b>" + session['status'] + "</b>.\n\n" + \
                "- You MUST use a valid OpenSubtitles.org account!\n" + \
                "- Check out <a href=\"https://github.com/emericg/OpenSubtitlesDownload/wiki/Log-in-with-a-registered-user\">how and why</a> on our wiki page")
        else:
            superPrint("error", "Connection error!", "OpenSubtitles.org servers refused the connection: <b>" + session['status'] + "</b>.\n\nPlease check:\n" + \
                "- www.opensubtitles.org availability\n" + \
                "- Your download limits (200 subtitles per 24h, 40 subtitles per 10s)\n\n" + \
                "The subtitles search and download service is powered by <a href=\"https://opensubtitles.org\">opensubtitles.org</a>.\n" + \
                "Be sure to donate if you appreciate the service provided!")
        sys.exit(2)

    # ==== Count languages selected for this search
    for language in opt_languages:
        languageList += list(language.split(','))

    languageCount_search = len(languageList)
    languageCount_results = 0

    if opt_language_suffix == 'auto' and languageCount_search > 1:
        opt_language_suffix = 'on'

    # ==== Get file hash, size and name
    videoTitle = ''
    videoHash = hashFile(currentVideoPath)
    videoSize = os.path.getsize(currentVideoPath)
    videoFileName = os.path.basename(currentVideoPath)

    # ==== Search for available subtitles
    for currentLanguage in opt_languages:
        subtitlesSearchList = []
        subtitlesResultList = {}

        if opt_search_mode in ('hash', 'hash_then_filename', 'hash_and_filename'):
            subtitlesSearchList.append({'sublanguageid':currentLanguage, 'moviehash':videoHash, 'moviebytesize':str(videoSize)})
        if opt_search_mode in ('filename', 'hash_and_filename'):
            subtitlesSearchList.append({'sublanguageid':currentLanguage, 'query':videoFileName})

        ## Primary search
        try:
            subtitlesResultList = osd_server.SearchSubtitles(session['token'], subtitlesSearchList)
        except Exception:
            # Retry once after a delay (we are already connected, the server may be momentary overloaded)
            time.sleep(3)
            try:
                subtitlesResultList = osd_server.SearchSubtitles(session['token'], subtitlesSearchList)
            except Exception:
                superPrint("error", "Search error!", "Unable to reach opensubtitles.org servers!\n<b>Search error</b>")

        #if (opt_search_mode == 'hash_and_filename'):
        #    TODO Cleanup duplicate between moviehash and filename results

        ## Secondary search
        if ((opt_search_mode == 'hash_then_filename') and (('data' in subtitlesResultList) and (not subtitlesResultList['data']))):
            subtitlesSearchList[:] = [] # subtitlesSearchList.clear()
            subtitlesSearchList.append({'sublanguageid':currentLanguage, 'query':videoFileName})
            subtitlesResultList.clear()
            try:
                subtitlesResultList = osd_server.SearchSubtitles(session['token'], subtitlesSearchList)
            except Exception:
                # Retry once after a delay (we are already connected, the server may be momentary overloaded)
                time.sleep(3)
                try:
                    subtitlesResultList = osd_server.SearchSubtitles(session['token'], subtitlesSearchList)
                except Exception:
                    superPrint("error", "Search error!", "Unable to reach opensubtitles.org servers!\n<b>Search error</b>")

        ## Parse the results of the XML-RPC query
        if ('data' in subtitlesResultList) and (subtitlesResultList['data']):
            # Mark search as successful
            languageCount_results += 1
            subtitlesSelected = ''

            # If there is only one subtitles (matched by file hash), auto-select it (except in CLI mode)
            if (len(subtitlesResultList['data']) == 1) and (subtitlesResultList['data'][0]['MatchedBy'] == 'moviehash'):
                if opt_selection_mode != 'manual':
                    subtitlesSelected = subtitlesResultList['data'][0]['SubFileName']

            # Get video title
            videoTitle = subtitlesResultList['data'][0]['MovieName']

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
            if not subtitlesSelected:
                if opt_selection_mode == 'auto':
                    # Automatic subtitles selection
                    subtitlesSelected = selectionAuto(subtitlesResultList)
                else:
                    # Go through the list of subtitles and handle 'auto' settings activation
                    for item in subtitlesResultList['data']:
                        if opt_selection_match == 'auto' and opt_search_mode == 'hash_and_filename':
                            opt_selection_match = 'on'
                        if opt_selection_language == 'auto' and languageCount_search > 1:
                            opt_selection_language = 'on'
                        if opt_selection_hi == 'auto' and item['SubHearingImpaired'] == '1':
                            opt_selection_hi = 'on'
                        if opt_selection_rating == 'auto' and item['SubRating'] != '0.0':
                            opt_selection_rating = 'on'
                        if opt_selection_count == 'auto':
                            opt_selection_count = 'on'

                    # Spaw selection window
                    if opt_gui == 'gnome':
                        subtitlesSelected = selectionGnome(subtitlesResultList)
                    elif opt_gui == 'kde':
                        subtitlesSelected = selectionKde(subtitlesResultList)
                    else: # CLI
                        subtitlesSelected = selectionCLI(subtitlesResultList)

            # At this point a subtitles should be selected
            if subtitlesSelected:
                subIndex = 0
                subIndexTemp = 0

                # Find it on the list
                for item in subtitlesResultList['data']:
                    if item['SubFileName'] == subtitlesSelected:
                        subIndex = subIndexTemp
                        break
                    else:
                        subIndexTemp += 1

                # Prepare download
                subURL = subtitlesResultList['data'][subIndex]['SubDownloadLink']
                subEncoding = subtitlesResultList['data'][subIndex]['SubEncoding']
                subLangName = subtitlesResultList['data'][subIndex]['LanguageName']
                subPath = ''

                if opt_output_path and os.path.isdir(os.path.abspath(opt_output_path)):
                    # Use the output path provided by the user
                    subPath = os.path.abspath(opt_output_path) + "/" + subPath.rsplit('/', 1)[1]
                else:
                    # Use the path of the input video
                    subPath = currentVideoPath.rsplit('.', 1)[0] + '.' + subtitlesResultList['data'][subIndex]['SubFormat']

                # Write language code into the filename?
                if (opt_language_suffix == 'on'):
                    if (str(opt_language_suffix_size) == 'auto' and len(currentLanguage) == 2) or str(opt_language_suffix_size) == '2': subLangId = opt_language_suffix_separator + subtitlesResultList['data'][subIndex]['ISO639']
                    elif (str(opt_language_suffix_size) == 'auto' and len(currentLanguage) == 3) or str(opt_language_suffix_size) == '3': subLangId = opt_language_suffix_separator + subtitlesResultList['data'][subIndex]['SubLanguageID']
                    else: subLangId = opt_language_suffix_separator + currentLanguage

                    subPath = subPath.rsplit('.', 1)[0] + subLangId + '.' + subtitlesResultList['data'][subIndex]['SubFormat']

                # Escape non-alphanumeric characters from the subtitles download path
                if opt_gui != 'cli':
                    subPath = re.escape(subPath)
                    subPath = subPath.replace('"', '\\"')
                    subPath = subPath.replace("'", "\\'")
                    subPath = subPath.replace('`', '\\`')

                # Make sure we are downloading an UTF8 encoded file
                if opt_force_utf8:
                    downloadPos = subURL.find("download/")
                    if downloadPos > 0:
                        subURL = subURL[:downloadPos+9] + "subencoding-utf8/" + subURL[downloadPos+9:]

                ## Download and unzip the selected subtitles (with progressbar)
                if opt_gui == 'gnome':
                    process_subtitlesDownload = subprocess.call("(wget -q -O - " + subURL + " | gunzip > " + subPath + ") 2>&1" + ' | (zenity --auto-close --progress --pulsate --title="Downloading subtitles, please wait..." --text="Downloading <b>' + subtitlesResultList['data'][subIndex]['LanguageName'] + '</b> subtitles for <b>' + videoTitle + '</b>...")', shell=True)
                elif opt_gui == 'kde':
                    process_subtitlesDownload = subprocess.call("(wget -q -O - " + subURL + " | gunzip > " + subPath + ") 2>&1", shell=True)
                else: # CLI
                    print(">> Downloading '" + subtitlesResultList['data'][subIndex]['LanguageName'] + "' subtitles for '" + videoTitle + "'")

                    if sys.version_info >= (3, 0):
                        tmpFile1, headers = urllib.request.urlretrieve(subURL)
                        tmpFile2 = gzip.GzipFile(tmpFile1)
                        byteswritten = open(subPath, 'wb').write(tmpFile2.read())
                        if byteswritten > 0:
                            process_subtitlesDownload = 0
                        else:
                            process_subtitlesDownload = 1
                    else: # python 2
                        tmpFile1, headers = urllib.urlretrieve(subURL)
                        tmpFile2 = gzip.GzipFile(tmpFile1)
                        open(subPath, 'wb').write(tmpFile2.read())
                        process_subtitlesDownload = 0

                # If an error occurs, say so
                if process_subtitlesDownload != 0:
                    superPrint("error", "Subtitling error!", "An error occurred while downloading or writing <b>" + subtitlesResultList['data'][subIndex]['LanguageName'] + "</b> subtitles for <b>" + videoTitle + "</b>.")
                    osd_server.LogOut(session['token'])
                    sys.exit(2)

                # Use a secondary tool after a successful download?
                #process_subtitlesDownload = subprocess.call("(custom_command" + " " + subPath + ") 2>&1", shell=True)

    ## Print a message if no subtitles have been found, for any of the languages
    if languageCount_results == 0:
        superPrint("info", "No subtitles available :-(", '<b>No subtitles found</b> for this video:\n<i>' + videoFileName + '</i>')
        ExitCode = 1
    else:
        ExitCode = 0

except KeyboardInterrupt:
    sys.exit(1)

except (OSError, IOError, RuntimeError, AttributeError, TypeError, NameError, KeyError):
    # Do not warn about remote disconnection # bug/feature of python 3.5?
    if "http.client.RemoteDisconnected" in str(sys.exc_info()[0]):
        sys.exit(ExitCode)

    # An unknown error occur, let's apologize before exiting
    superPrint("error", "Unexpected error!",
        "OpenSubtitlesDownload encountered an <b>unknown error</b>, sorry about that...\n\n" + \
        "Error: <b>" + str(sys.exc_info()[0]).replace('<', '[').replace('>', ']') + "</b>\n" + \
        "Line: <b>" + str(sys.exc_info()[-1].tb_lineno) + "</b>\n\n" + \
        "Just to be safe, please check:\n" + \
        "- www.opensubtitles.org availability\n" + \
        "- Your Internet connection status\n" + \
        "- Your download limits (200 subtitles per 24h, 40 subtitles per 10s)\n" + \
        "- That are using the latest version of this software ;-)")

except Exception:
    # Catch unhandled exceptions but do not spawn an error window
    print("Unexpected error (line " + str(sys.exc_info()[-1].tb_lineno) + "): " + str(sys.exc_info()[0]))

# Disconnect from opensubtitles.org server, then exit
if session and session['token']: osd_server.LogOut(session['token'])
sys.exit(ExitCode)
