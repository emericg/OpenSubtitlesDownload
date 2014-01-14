#!/usr/bin/python
# -*- coding: utf-8 -*-

# OpenSubtitlesDownload.py / Version 3.1
# https://github.com/emericg/OpenSubtitlesDownload
# This software is designed to help you find and download subtitles for your favorite videos!

# Copyright (c) 2014 by Emeric GRANGE <emeric.grange@gmail.com>
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
# Gui13 for his work on the arguments parsing
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

# ==== Language selection ======================================================
# Supported ISO codes: http://www.opensubtitles.org/addons/export_languages.php
#
# 1/ You can change the search language here by using either 2-letter (ISO 639-1)
# or 3-letter (ISO 639-2) language codes.
#
# 2/ You can also search for subtitles in several languages ​​at once:
# - SubLanguageIDs = ['eng,fre'] to download the first language available only
# - SubLanguageIDs = ['eng','fre'] to download all selected languages
SubLanguageIDs = ['eng']

# Write 2-letter language code (ex: _en) at the end of the subtitles file. 'on', 'off' or 'auto'.
# If you are regularly searching for several language at once, you sould use 'on'.
opt_write_languagecode = 'auto'

# ==== Settings ================================================================
# For a complete documentation, please use the wiki:
# https://github.com/emericg/OpenSubtitlesDownload/wiki

# Select your GUI. Can be overriden at run time with '--gui=xxx'.
# - auto (autodetect, fallback on CLI)
# - gnome (GNOME/GTK based environments, using 'zenity' backend)
# - kde (KDE/Qt based environments, using 'kdialog' backend)
# - cli (Command Line Interface)
gui = 'auto'

# Change the subtitles selection GUI size:
gui_width  = 720
gui_height = 320

# Subtitles selection mode:
# - manual (in case of multiple results, let you choose the subtitles you want)
# - auto (automatically select the most downloaded subtitles)
opt_selection_mode = 'manual'

# Various GUI options. You can set them to 'on', 'off' or 'auto'.
opt_selection_language = 'auto'
opt_selection_hi       = 'auto'
opt_selection_rating   = 'off'
opt_selection_count    = 'off'

# ==== Server selection ========================================================
# XML-RPC server domain for opensubtitles.org:

server = ServerProxy('http://api.opensubtitles.org/xml-rpc')

# ==== Super Print =============================================================
# priority: info, warning, error
# title: only for zenity messages
# message: full text, with tags and breaks (tag cleanup for terminal)
# verbose: is this message important?

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
        message = message.replace('\\"', '"')
        
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
        
        else: # CLI
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
        superPrint("error", "I/O error", "Input/Output error while generating hash for this file:\n<i>" + path + "</i>")
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
        ' --list --title="Subtitles for: ' + videoTitle + '"' + \
        ' --text="<b>Title:</b> ' + videoTitle + '\n<b>Filename:</b> ' + videoFileName + '"' + \
        ' --column="Available subtitles" ' + columnHi + columnLn + columnRate + columnCount + subtitlesItems, shell=True, stdout=subprocess.PIPE)
    
    # Get back the result
    result_subtitlesSelection = process_subtitlesSelection.communicate()
    
    # The results contain a subtitles?
    if result_subtitlesSelection[0]:
        if sys.version_info >= (3,0):
            subtitlesSelected = str(result_subtitlesSelection[0], 'utf-8').strip("\n")
        else: # python2
            subtitlesSelected = str(result_subtitlesSelection[0]).strip("\n")
        
        # Hack against recent zenity version?
        if len(subtitlesSelected.split("|")) > 1:
            if subtitlesSelected.split("|")[0] == subtitlesSelected.split("|")[1]:
                subtitlesSelected = subtitlesSelected.split("|")[0]
    else:
        if process_subtitlesSelection.returncode == 0:
            subtitlesSelected = subtitlesList['data'][0]['SubFileName']
    
    # Return the result
    return subtitlesSelected

# ==== KDE selection window ====================================================

def selectionKde(subtitlesList):
    """KDE subtitles selection window using kdialog"""
    return selectionAuto(subtitlesList)

# ==== CLI selection mode ======================================================

def selectionCLI(subtitlesList):
    """Command Line Interface, subtitles selection inside your current terminal"""
    subtitlesIndex = 0
    subtitlesItem = ''
    
    # Print video infos
    print("\n>> Title: " + videoTitle)
    print(">> Filename: " + videoFileName)
    
    # Print subtitles list on the terminal
    print(">> Available subtitles:")
    for item in subtitlesList['data']:
        subtitlesIndex += 1
        subtitlesItem = '"' + item['SubFileName'] + '" '
        if opt_selection_hi == 'on':
            if item['SubHearingImpaired'] == '1':
                subtitlesItem += '> "HI" '
        if opt_selection_language == 'on':
            subtitlesItem += '> "LanguageName: ' + item['LanguageName'] + '" '
        if opt_selection_rating == 'on':
            subtitlesItem += '> "SubRating: ' + item['SubRating'] + '" '
        if opt_selection_count == 'on':
            subtitlesItem += '> "SubDownloadsCnt: ' + item['SubDownloadsCnt'] + '" '
        print("\033[93m[" + str(subtitlesIndex) + "]\033[0m " + subtitlesItem)
    
    # Ask user selection
    print("\033[91m[0]\033[0m Cancel search")
    sub_selection = -1
    while( sub_selection < 0 or sub_selection > subtitlesIndex ):
        try:
            sub_selection = int(input(">> Enter your choice (0-" + str(subtitlesIndex) + "): "))
        except:
            sub_selection = -1
    
    # Return the result
    if sub_selection == 0:
        print("Cancelling search...")
        return
    else:
        return subtitlesList['data'][sub_selection-1]['SubFileName']

# ==== Automatic selection mode ================================================

def selectionAuto(subtitlesList):
    """Automatic subtitles selection using donwload count"""
    """todo: handle filename match instead of download count?"""
    
    # Auto-select the first subtitles
    subtitlesSelected = subtitlesList['data'][0]['SubFileName']
    
    ## Auto-select the most downloaded subtitles
    #subtitlesScore = 0
    #for item in subtitlesList['data']:
    #    if int(item['SubDownloadsCnt']) > subtitlesScore:
    #        subtitlesScore = int(item['SubDownloadsCnt'])
    #        subtitlesSelected = item['SubFileName']
    
    return subtitlesSelected

# ==== Argument parsing  =======================================================

# Get OpenSubtitlesDownload.py script path
execPath = str(sys.argv[0])

# Handle other arguments
parser = argparse.ArgumentParser(
    description="""This software is designed to help you find and download subtitles for your favorite videos!""",
    formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('filePathListArguments', help="The video file for which subtitles should be searched", nargs='+')
parser.add_argument('-v', '--verbose', help="Enables verbose output (default: disabled)", action='store_true')
parser.add_argument('-a', '--auto', help="Automatically choose the best subtitles, without human interaction (default: disabled)", action='store_true')
parser.add_argument('-g', '--gui', help="Select the gui type, from these options: auto, kde, gnome, cli (default: auto)")
parser.add_argument('-l', '--lang', help="Specify the language in which the subtitles should be downloaded (default: eng).\nSyntax:\n-l eng,fre : search in both language\n-l eng -l fre : download both language", nargs='?', action='append')

result = parser.parse_args()

# Save results
if result.gui:
    gui = result.gui
if result.auto:
    opt_selection_mode = 'auto'
if result.lang:
    if SubLanguageIDs != result.lang:
        SubLanguageIDs = result.lang
        opt_selection_language = 'on'
        if opt_write_languagecode != 'off':
            opt_write_languagecode = 'on'

# ==== GUI auto detection ======================================================

if gui == 'auto':
    # Note: "ps cax" only output the first 15 characters of the executable's names
    ps = str(subprocess.Popen(['ps', 'cax'], stdout=subprocess.PIPE).communicate()[0]).split('\n')
    for line in ps:
        if ('gnome-session' in line) or ('cinnamon-sessio' in line) or ('mate-session' in line) or ('xfce4-session' in line):
            gui = 'gnome'
            break
        elif ('ksmserver' in line):
            gui = 'kde'
            break

# Fallback
if gui not in ['gnome', 'kde', 'cli']:
    gui = 'cli'
    opt_selection_mode = 'auto'
    print("Unknow GUI, falling back to an automatic CLI mode")

# ==== Get valid video paths ===================================================

videoPathList = []

# Go through the paths taken from arguments, and extract only valid video paths
for i in result.filePathListArguments:
    if checkFile(os.path.abspath(i)):
        videoPathList.append(os.path.abspath(i))

# Empty videoPathList? Try selected file(s) from nautilus environment variable
#filePathListEnvironment = []
# if gui == 'gnome':
#     if not videoPathList:
#         # Get file(s) from nautilus
#         filePathListEnvironment = os.environ['NAUTILUS_SCRIPT_SELECTED_FILE_PATHS'].splitlines()
#         # Check file(s) type and validity
#         for filePath in filePathListEnvironment:
#             if checkFile(filePath):
#                 videoPathList.append(filePath)

# ==== Dispatcher ==============================================================

# If videoPathList is empty, abort!
if len(videoPathList) == 0:
    parser.print_help()
    sys.exit(1)

# The first video file will be processed by this instance
videoPath = videoPathList[0]
videoPathList.pop(0)

# The remaining file(s) are dispatched to new instance(s) of this script
for videoPathDispatch in videoPathList:
    
    # Handle current options
    command = execPath + " -g " + gui
    if opt_selection_mode == 'auto':
        command += " -a "
    if result.verbose == 'verbose':
        command += " -v "
    if result.lang:
        for resultlangs in result.lang:
            command += " -l " + resultlangs
    
    command_splitted = command.split()
    command_splitted.append(videoPathDispatch) # do not risk videoPath to be 'splitted'
    
    if gui == 'cli' and opt_selection_mode == 'manual':
        # Synchronous call
        process_videoDispatched = subprocess.call(command_splitted)
    else:
        # Asynchronous call
        process_videoDispatched = subprocess.Popen(command_splitted)

# ==== Main program ============================================================

try:
    try:
        # Connection to opensubtitles.org server
        session = server.LogIn('', '', 'en', 'opensubtitles-download 3.1')
        
        # Failed connection attempt?
        if session['status'] != '200 OK':
            superPrint("error", "Connection error!", "Unable to reach opensubtitles.org servers: " + session['status'] + ".\n\nPlease check:\n- Your Internet connection status\n- www.opensubtitles.org availability\n- Your 200 downloads per 24h limit\n\nThe subtitles search and download service is powered by opensubtitles.org. Be sure to donate if you appreciate the service provided!")
            sys.exit(1)
    except Exception:
        superPrint("error", "Connection error!", "Unable to reach opensubtitles.org servers!\n\nPlease check:\n- Your Internet connection status\n- www.opensubtitles.org availability\n- Your 200 downloads per 24h limit\n\nThe subtitles search and download service is powered by opensubtitles.org. Be sure to donate if you appreciate the service provided!")
        sys.exit(1)
    
    searchLanguage = 0
    searchLanguageResult = 0
    videoTitle = 'Unknow video'
    videoHash = hashFile(videoPath)
    videoSize = os.path.getsize(videoPath)
    videoFileName = os.path.basename(videoPath)
    
    # Count languages marked for this search
    for SubLanguageID in SubLanguageIDs:
        searchLanguage += len(SubLanguageID.split(','))
    
    # Search for available subtitles (using file hash and size)
    for SubLanguageID in SubLanguageIDs:
        searchList = []
        searchList.append({'sublanguageid':SubLanguageID, 'moviehash':videoHash, 'moviebytesize':str(videoSize)})
        subtitlesList = server.SearchSubtitles(session['token'], searchList)
        subtitlesSelected = ''
        
        # Parse the results of the XML-RPC query
        if subtitlesList['data']:
            
            # Mark search as successful
            searchLanguageResult += 1
            
            # If there is only one subtitles, auto-select it
            if len(subtitlesList['data']) == 1:
                subtitlesSelected = subtitlesList['data'][0]['SubFileName']
            
            # Get video title. If needed sanitize the string to avoid zenity/kdialog handling errors
            videoTitle = subtitlesList['data'][0]['MovieName']
            if gui != 'cli':
                videoTitle = videoTitle.replace('"', '\\"')
                videoTitle = videoTitle.replace("'", "\'")
                videoTitle = videoTitle.replace("&", "&amp;")
            
            # If there is more than one subtitles and opt_selection_mode != 'auto',
            # then let the user decide which one will be downloaded
            if len(subtitlesList['data']) > 1:
                
                # Automatic subtitles selection?
                if opt_selection_mode == 'auto':
                    subtitlesSelected = selectionAuto(subtitlesList)
                else:
                    # Go through the list of subtitles
                    for item in subtitlesList['data']:
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
                    else: # CLI
                        subtitlesSelected = selectionCLI(subtitlesList)
            
            # If a subtitles has been selected at this point, download it!
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
                subPath = videoPath.rsplit('.', 1)[0] + '.' + subtitlesList['data'][subIndex]['SubFormat']
                
                # Write language code into the filename?
                if ((opt_write_languagecode == 'on') or
                    (opt_write_languagecode == 'auto' and searchLanguageResult > 1)):
                    subPath = videoPath.rsplit('.', 1)[0] + subLangId + '.' + subtitlesList['data'][subIndex]['SubFormat']
                
                # Download and unzip the selected subtitles (with progressbar)
                if gui == 'gnome':
                    process_subtitlesDownload = subprocess.call('(wget -q -O - ' + subURL + ' | gunzip > "' + subPath + '") 2>&1 | (zenity --auto-close --progress --pulsate --title="Downloading subtitles, please wait..." --text="Downloading <b>' + subtitlesList['data'][subIndex]['LanguageName'] + '</b> subtitles for <b>' + videoTitle + '</b>")', shell=True)
                elif gui == 'kde':
                    process_subtitlesDownload = subprocess.call('(wget -q -O - ' + subURL + ' | gunzip > "' + subPath + '") 2>&1', shell=True)
                else: # CLI
                    print(">> Downloading '" + subtitlesList['data'][subIndex]['LanguageName'] + "' subtitles for '" + videoTitle + "'")
                    process_subtitlesDownload = subprocess.call('wget -nv -O - ' + subURL + ' | gunzip > "' + subPath + '"', shell=True)
                
                # If an error occur, say so
                if process_subtitlesDownload != 0:
                    superPrint("error", "", "An error occurred while downloading or writing <b>" + subtitlesList['data'][subIndex]['LanguageName'] + "</b> subtitles for <b>" + videoTitle + "</b>.")
                    sys.exit(1)
    
    # Print a message if none of the subtitles languages have been found
    if searchLanguageResult == 0:
        superPrint("info", "No synchronized subtitles found for " + videoFileName, 'No synchronized subtitles found for this video:\n<i>' + videoFileName + '</i>')
    
    # Disconnect from opensubtitles.org server, then exit
    server.LogOut(session['token'])
    sys.exit(0)

except Exception:
    # Disconnect from opensubtitles.org server, if still connected only
    if session['token']:
        server.LogOut(session['token'])
    
    # An unknown error occur, let's apologize before exiting
    superPrint("error", "Unknown error", "An <b>unknown error</b> occurred, sorry about that...\n\nPlease check:\n- Your Internet connection status\n- www.opensubtitles.org availability\n- Your 200 downloads per 24h limit\n- You are using the latest version of this software")
    sys.exit(1)
