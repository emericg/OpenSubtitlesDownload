#!/usr/bin/python
# -*- coding: utf-8 -*-

## OpenSubtitles-download / Version 3.0
## https://github.com/emericg/opensubtitles-download
## This software is designed to help you find and download subtitles for your favorite videos!

# Copyright (c) 2013 by Emeric GRANGE <emeric.grange@gmail.com>
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

# Contributors / special thanks:
# Tomáš Hnyk <tomashnyk@gmail.com> for his work on the 'multiple language' feature
# Carlos Acedo <carlos@linux-labs.net> for his work on the original script

import os
import sys
import struct
import mimetypes
import subprocess
import argparse

if sys.version_info >= (3,0):
    from xmlrpc.client import ServerProxy, Error
else: # python2
    from xmlrpclib import ServerProxy, Error

# ==== Argument parsing  =======================================================
# 
parser = argparse.ArgumentParser(description="""This program can be used to automatically download subtitles for a movie.""",
    formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('movie_files',  help="The movie file for which subtitles should be searched", nargs='+')
parser.add_argument('-g', '--gui', help="Select the gui type, from these options: auto, kde, gnome, terminal (default: auto)", default='auto')
parser.add_argument('-a', '--auto',help="Automatically choose the best subtitle (default: you will be asked to choose)", default='manual')
parser.add_argument('-l', '--lang',
    help="""Specify the language in which the subtitle should be downloaded.
The syntax is the following:
    -l eng,fre : download the first language available, in french or english
    -l eng fre : download both language subtitles""", 
    default='eng',
    nargs='?', 
    action='append')
parser.add_argument('-v', '--verbose', help="Enables verbose output", action='store_true')


result = parser.parse_args()

# ==== Language selection ======================================================
# Supported ISO codes: http://www.opensubtitles.org/addons/export_languages.php
#
# 1/ You can change the search language here by using either 2-letter (ISO 639-1)
# or 3-letter (ISO 639-2) language codes.
#
# 2/ You can also search for subtitles in several languages ​​at once:
# - SubLanguageIDs = ['eng,fre'] to download the first language available only
# - SubLanguageIDs = ['eng','fre'] to download all selected languages

SubLanguageIDs = result.lang

# ==== Settings ================================================================
# For a complete documentation of these options, please refer to the wiki.

# Select your gui. Can be overriden at run time with '--gui=xxx'.
# - auto (autodetect, fallback on terminal)
# - gnome (using 'zenity' backend)
# - kde (using 'kdialog' backend)
# - terminal (no dependency)
gui = result.gui

# Change the subtitles selection GUI size:
gui_width  = 720
gui_height = 320

# Various GUI options. You can set them to 'on', 'off' or 'auto' mode.
opt_file_languagecode  = 'off'
opt_selection_language = 'auto'
opt_selection_hi       = 'auto'
opt_selection_rating   = 'off'
opt_selection_count    = 'off'

# Subtitles selection mode. Can be 'manual' or 'auto'.
subtitles_selection = result.auto

# ==== Server selection ========================================================
# XML-RPC server domain for opensubtitles.org:
server = ServerProxy('http://api.opensubtitles.org/xml-rpc')

# ==== Super Print =============================================================
# priority: info, warning, error
# title: only for zenity messages
# message: full text, with tags and breaks (tag cleanup for terminal)
# verbose: is this message important ?
def superPrint(priority, title, message):
    """Print messages through terminal, zenity or kdialog"""
    if gui == 'gnome':
        if title:
            subprocess.call(['zenity', '--' + priority, '--title=' + title, '--text=' + message])
        else:
            subprocess.call(['zenity', '--' + priority, '--text=' + message])
    
    else:
        # Clean up the tags from the message
        message = message.replace("\n\n", "\n")
        message = message.replace("<i>", "")
        message = message.replace("</i>", "")
        message = message.replace("<b>", "")
        message = message.replace("</b>", "")
        
        # Print message
        if gui == 'kde':
            if priority == 'warning':
                priority = 'sorry'
            elif priority == 'info':
                priority = 'msgbox'
            
            if title:
                subprocess.call(['kdialog', '--' + priority, '--title=' + title, '--text=' + message])
            else:
                subprocess.call(['kdialog', '--' + priority, '--text=' + message])
        
        else: # terminal
            print(">> " + message)

# ==== Check file path & file ==================================================
def checkFile(path):
    """Check mimetype and/or file extension to detect valid video file"""
    if os.path.isfile(path) == False:
        superPrint("error", "", "This is not a file:\n<i>" + path + "</i>")
        return False
    
    fileMimeType, encoding = mimetypes.guess_type(path)
    if fileMimeType == None:
        fileExtension = path.rsplit('.', 1)
        if fileExtension[1] not in ['3g2', '3gp', '3gp2', '3gpp', 'ajp', \
        'asf', 'asx', 'avchd', 'avi', 'bik', 'bix', 'box', 'cam', 'dat', \
        'divx', 'dmf', 'dv', 'dvr-ms', 'evo', 'flc', 'fli', 'flic', 'flv', \
        'flx', 'gvi', 'gvp', 'h264', 'm1v', 'm2p', 'm2ts', 'm2v', 'm4e', \
        'm4v', 'mjp', 'mjpeg', 'mjpg', 'mkv', 'moov', 'mov', 'movhd', 'movie', \
        'movx', 'mp4', 'mpe', 'mpeg', 'mpg', 'mpv', 'mpv2', 'mxf', 'nsv', \
        'nut', 'ogg', 'ogm', 'ogv', 'omf', 'ps', 'qt', 'ram', 'rm', 'rmvb', \
        'swf', 'ts', 'vfw', 'vid', 'video', 'viv', 'vivo', 'vob', 'vro', \
        'webm', 'wm', 'wmv', 'wmx', 'wrap', 'wvx', 'wx', 'x264', 'xvid']:
            superPrint("error", "", "This file is not a video (unknown mimetype AND invalid file extension):\n<i>" + path + "</i>")
            return False
    else:
        fileMimeType = fileMimeType.split('/', 1)
        if fileMimeType[0] != 'video':
            superPrint("error", "", "This file is not a video (unknown mimetype):\n<i>" + path + "</i>")
            return False
    
    return True

# ==== Hashing algorithm =======================================================
# Infos: http://trac.opensubtitles.org/projects/opensubtitles/wiki/HashSourceCodes
# This particular implementation is coming from SubDownloader: http://subdownloader.net/
def hashFile(path):
    """Produce a hash for a video file: size + 64bit chksum of the first and 
    last 64k (even if they overlap because the file is smaller than 128k)"""
    try:
        longlongformat = 'Q' # unsigned long long little endian
        bytesize = struct.calcsize(longlongformat)
        format = "<%d%s" % (65536//bytesize, longlongformat)
        
        f = open(path, "rb")
        
        filesize = os.fstat(f.fileno()).st_size
        hash = filesize
        
        if filesize < 65536 * 2:
            superPrint("error", "", "File size error while generating hash for this file:\n<i>" + path + "</i>")
            return "SizeError"
        
        buffer = f.read(65536)
        longlongs = struct.unpack(format, buffer)
        hash += sum(longlongs)
        
        f.seek(-65536, os.SEEK_END) # size is always > 131072
        buffer = f.read(65536)
        longlongs = struct.unpack(format, buffer)
        hash += sum(longlongs)
        hash &= 0xFFFFFFFFFFFFFFFF
        
        f.close()
        returnedhash = "%016x" % hash
        return returnedhash
    
    except IOError:
        superPrint("error", "", "Input/Output error while generating hash for this file:\n<i>" + path + "</i>")
        return "IOError"

# ==== Gnome selection window ==================================================
def selectionGnome(subtitlesList):
    """Gnome subtitles selection window using zenity"""
    subtitlesSelected = ''
    subtitlesItems = ''
    columnLn = ''
    columnHi = ''
    columnRate = ''
    columnCount = ''
    
    # Generate selection window content
    for item in subtitlesList['data']:
        subtitlesItems += '"' + item['SubFileName'] + '" '
        if opt_selection_hi == 'on':
            columnHi = '--column="HI" '
            if item['SubHearingImpaired'] == '1':
                subtitlesItems += '"✓" '
            else:
                subtitlesItems += '"" '
        if opt_selection_language == 'on':
            columnLn = '--column="Language" '
            subtitlesItems += '"' + item['LanguageName'] + '" '
        if opt_selection_rating == 'on':
            columnRate = '--column="Rating" '
            subtitlesItems += '"' + item['SubRating'] + '" '
        if opt_selection_count == 'on':
            columnCount = '--column="Downloads" '
            subtitlesItems += '"' + item['SubDownloadsCnt'] + '" '
    
    # Spawn zenity "list" dialog
    process_subtitlesSelection = subprocess.Popen('zenity --width=' + str(gui_width) + ' --height=' + str(gui_height) + \
        ' --list --title="' + item['MovieName'] + ' (file: ' + movieFileName + ')"' + \
        ' --column="Available subtitles" ' + columnHi + columnLn + columnRate + columnCount + subtitlesItems, shell=True, stdout=subprocess.PIPE)
    
    # Get back the result
    result_subtitlesSelection = process_subtitlesSelection.communicate()
    
    # The results contain a subtitles ?
    if result_subtitlesSelection[0]:
        if sys.version_info >= (3,0):
            subtitlesSelected = str(result_subtitlesSelection[0], 'utf-8').strip("\n")
        else: # python2
            subtitlesSelected = str(result_subtitlesSelection[0]).strip("\n")
        
        # Hack against recent zenity version ?
        if subtitlesSelected.split("|")[0] == subtitlesSelected.split("|")[1]:
            subtitlesSelected = subtitlesSelected.split("|")[0]
    else:
        if process_subtitlesSelection.returncode == 0:
            subtitlesSelected = subtitlesList['data'][0]['SubFileName']
    
    return subtitlesSelected

# ==== KDE selection window ====================================================
def selectionKde(subtitlesList):
    """KDE subtitles selection window using kdialog"""
    return selectionAuto(subtitlesList)

# ==== Terminal selection window ===============================================
def selectionTerminal(subtitlesList):
    """Subtitles selection inside your current terminal"""
    subtitlesIndex = 0
    subtitlesItem = ''
    
    # Print subtitles list on the terminal
    print(">> Available subtitles:")
    for item in subtitlesList['data']:
        subtitlesIndex += 1
        subtitlesItem = '"' + item['SubFileName'] + '" '
        if opt_selection_hi == 'on':
            if item['SubHearingImpaired'] == '1':
                subtitlesItem += '"HI" '
        if opt_selection_language == 'on':
            subtitlesItem += '"LanguageName: ' + item['LanguageName'] + '" '
        if opt_selection_rating == 'on':
            subtitlesItem += '"SubRating: ' + item['SubRating'] + '" '
        if opt_selection_count == 'on':
            subtitlesItem += '"SubDownloadsCnt: ' + item['SubDownloadsCnt'] + '" '
        print("\033[93m[" + str(subtitlesIndex) + "]\033[0m " + subtitlesItem)
    
    # Ask user selection
    sub_selection = 0
    while( sub_selection < 1 or sub_selection > subtitlesIndex ):
        try:
            sub_selection = int(input(">> Enter your choice (1-" + str(subtitlesIndex) + "): "))
        except:
            sub_selection = 0
    
    return subtitlesList['data'][sub_selection-1]['SubFileName']

# ==== Automatic selection mode ================================================
def selectionAuto(subtitlesList):
    """Automatic subtitles selection using donwload count"""
    """todo: handle filename match instead of download count?"""
    subtitlesSelected = ''
    subtitlesScore = 0
    
    for item in subtitlesList['data']:
        if item['SubDownloadsCnt'] > subtitlesScore:
            subtitlesScore = item['SubDownloadsCnt']
            subtitlesSelected = item['SubFileName']
    
    return subtitlesSelected

# ==== Parse script argument(s)  and get file paths ============================

filePathList = []
moviePathList = []

# Get opensubtitles-download script path, then remove it from argv list
execPath = str(sys.argv[0])

# Go through 'argv' list and extract all options or valid video paths
for i in result.movie_files:
    if checkFile(os.path.abspath(i)):
        moviePathList.append(os.path.abspath(i))

# Empty moviePathList? Try selected file(s) from nautilus
# if gui == 'gnome':
#     if not moviePathList:
#         # Get file(s) from nautilus
#         filePathList = os.environ['NAUTILUS_SCRIPT_SELECTED_FILE_PATHS'].splitlines()
#         # Check file(s) type and validity
#         for filePath in filePathList:
#             if checkFile(filePath):
#                 moviePathList.append(filePath)

# ==== GUI auto detection ======================================================

if gui == 'auto':
    gui = 'terminal'
    ps = str(subprocess.Popen(['ps', 'cax'], stdout=subprocess.PIPE).communicate()[0]).split('\n')
    for line in ps:
        if ('gnome-session' in line) or ('mate-session' in line) or ('xfce-mcs-manage' in line):
            gui = 'gnome'
            break
        elif 'ksmserver' in line:
            gui = 'kde'
            break


# ==== Dispatcher ==============================================================

# If moviePathList is empty, abort!
if len(moviePathList) == 0:
    parser.print_help()
    sys.exit(1)
if len(moviePathList) > 1 and gui == 'terminal':
    print "The terminal gui of the script doesn't support multiple files"
    sys.exit(1)

# The first file will be processed by this instance
moviePath = moviePathList[0]
moviePathList.pop(0)

# The remaining file(s) are dispatched to new instance(s) of this script
for moviePathDispatch in moviePathList:
    process_movieDispatched = subprocess.Popen([execPath, '--gui=' + gui, moviePathDispatch])

# ==== Main program ============================================================
try:
    try:
        # Connection to opensubtitles.org server
        session = server.LogIn('', '', 'en', 'opensubtitles-download 3.0')
        if session['status'] != '200 OK':
            superPrint("error", "", "Unable to reach opensubtitles.org server: " + session['status'] + ".\n\nPlease check:\n- Your Internet connection status\n- www.opensubtitles.org availability")
            sys.exit(1)
        token = session['token']
    except Exception:
        superPrint("error", "", "Unable to reach opensubtitles.org server.\n\nPlease check:\n- Your Internet connection status\n- www.opensubtitles.org availability")
        sys.exit(1)
    
    searchLanguage = 0
    searchLanguageResult = 0
    movieHash = hashFile(moviePath)
    movieSize = os.path.getsize(moviePath)
    movieFileName = os.path.basename(moviePath)
    
    # Count languages marked for this search
    for SubLanguageID in SubLanguageIDs:
        searchLanguage += len(SubLanguageID.split(','))
    
    # Search for available subtitles (using file hash and size)
    for SubLanguageID in SubLanguageIDs:
        searchList = []
        searchList.append({'sublanguageid':SubLanguageID, 'moviehash':movieHash, 'moviebytesize':str(movieSize)})
        subtitlesList = server.SearchSubtitles(token, searchList)
        subtitlesSelected = ''
        
        # Parse the results of the XML-RPC query
        if subtitlesList['data']:
            
            # Mark search as successful
            searchLanguageResult += 1
            
            # If there is only one subtitles, auto-select it
            if len(subtitlesList['data']) == 1:
                subtitlesSelected = subtitlesList['data'][0]['SubFileName']
            
            # If there is more than one subtitles and selection_mode != 'auto',
            # then let the user decide which one will be downloaded
            if len(subtitlesList['data']) > 1:
                
                # Automatic subtitles selection?
                if subtitles_selection == 'auto':
                    subtitlesSelected = selectionAuto(subtitlesList)
                else:
                    # Go through the list of subtitles
                    for item in subtitlesList['data']:
                        # Sanitize the title string to avoid handling errors (gui only)
                        item['MovieName'] = item['MovieName'].replace('"', '\\"')
                        item['MovieName'] = item['MovieName'].replace("'", "\'")
                        # Handle 'auto' options
                        if opt_selection_language == 'auto':
                            if searchLanguage > 1:
                                opt_selection_language = 'on'
                        if opt_selection_hi == 'auto':
                            if item['SubHearingImpaired'] == '1':
                                opt_selection_hi = 'on'
                        if opt_selection_rating == 'auto':
                            if item['SubRating'] != '0.0':
                                opt_selection_rating = 'on'
                        if opt_selection_count == 'auto':
                            opt_selection_count = 'on'
                    
                    # Selection window
                    if gui == 'gnome':
                        subtitlesSelected = selectionGnome(subtitlesList)
                    elif gui == 'kde':
                        subtitlesSelected = selectionKde(subtitlesList)
                    else: # terminal
                        subtitlesSelected = selectionTerminal(subtitlesList)
            
            # If a subtitles has been auto or manually selected, download it
            if subtitlesSelected:
                subIndex = 0
                subIndexTemp = 0
                
                # Select the subtitles file to download
                for item in subtitlesList['data']:
                    if item['SubFileName'] == subtitlesSelected:
                        subIndex = subIndexTemp
                        break
                    else:
                        subIndexTemp += 1
                
                subLangId = '_' + subtitlesList['data'][subIndex]['ISO639']
                subLangName = subtitlesList['data'][subIndex]['LanguageName']
                subURL = subtitlesList['data'][subIndex]['SubDownloadLink']
                subPath = moviePath.rsplit('.', 1)[0] + '.' + subtitlesList['data'][subIndex]['SubFormat']
                
                # Write language code into the filename ?
                if opt_file_languagecode != 'off' and searchLanguageResult > 1:
                    subPath = moviePath.rsplit('.', 1)[0] + subLangId + '.' + subtitlesList['data'][subIndex]['SubFormat']
                
                # Download and unzip the selected subtitles (with progressbar)
                if gui == 'gnome':
                    process_subtitlesDownload = subprocess.call('(wget -q -O - ' + subURL + ' | gunzip > "' + subPath + '") 2>&1 | (zenity --auto-close --progress --pulsate --title="Downloading subtitles, please wait..." --text="Downloading <b>' + subtitlesList['data'][subIndex]['LanguageName'] + '</b> subtitles for <b>' + subtitlesList['data'][subIndex]['MovieName'] + '</b>")', shell=True)
                elif gui == 'kde':
                    process_subtitlesDownload = subprocess.call('(wget -q -O - ' + subURL + ' | gunzip > "' + subPath + '") 2>&1', shell=True)
                else: # terminal
                    print(">> Downloading '" + subtitlesList['data'][subIndex]['LanguageName'] + "' subtitles for '" + subtitlesList['data'][subIndex]['MovieName'] + "'")
                    process_subtitlesDownload = subprocess.call('wget -nv -O - ' + subURL + ' | gunzip > "' + subPath + '"', shell=True)
                
                # If an error occur, say so
                if process_subtitlesDownload != 0:
                    superPrint("error", "", "An error occurred while downloading or writing <b>" + subtitlesList['data'][subIndex]['LanguageName'] + "</b> subtitles for <b>" + subtitlesList['data'][subIndex]['MovieName'] + "</b>.")
                    sys.exit(1)
    
    # Print a message if none of the subtitles languages have been found
    if searchLanguageResult == 0:
        superPrint("info", "No subtitles found for " + movieFileName, 'No subtitles found for this video:\n<i>' + movieFileName + '</i>')
    
    # Disconnect from opensubtitles.org server, then exit
    server.LogOut(token)
    sys.exit(0)

except Error:
    # If an unknown error occur, say so (and apologize)
    superPrint("error", "", "An <b>unknown error</b> occurred, sorry about that...\n\nPlease check:\n- Your Internet connection status\n- www.opensubtitles.org availability")
    sys.exit(1)
