#!/usr/bin/env python
# -*- coding: utf-8 -*-

# OpenSubtitlesDownload.py / Version 4.0
# This software is designed to help you find and download subtitles for your favorite videos!

# You can browse the official website:
# https://emericg.github.io/OpenSubtitlesDownload
# You can browse the project's GitHub page:
# https://github.com/emericg/OpenSubtitlesDownload
# Learn much more about OpenSubtitlesDownload.py on its wiki:
# https://github.com/emericg/OpenSubtitlesDownload/wiki

# Copyright (c) 2016 by Emeric GRANGE <emeric.grange@gmail.com>
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
# LenuX for his work on the Qt GUI
# jeroenvdw for his work on the 'subtitles automatic selection' and the 'search by filename'
# Gui13 for his work on the arguments parsing
# Tomáš Hnyk <tomashnyk@gmail.com> for his work on the 'multiple language' feature
# Carlos Acedo <carlos@linux-labs.net> for his work on the original script

import os
import re
import sys
import struct
import mimetypes
import subprocess
import argparse
import time
import StringIO
import gzip

if sys.version_info >= (3,0):
    import shutil
    import urllib.request
    from xmlrpc.client import ServerProxy, Error
    import configparser
else: # python2
    import urllib2
    from xmlrpclib import ServerProxy, Error
    import ConfigParser

try:
    from PyQt4 import QtCore, QtGui
except ImportError:
    print("PyQt4 is not available on your system, falling back to GTK.")

# ==== Opensubtitles.org server settings =======================================
# XML-RPC server domain for opensubtitles.org:
osd_server = ServerProxy('http://api.opensubtitles.org/xml-rpc')

# You can use your opensubtitles.org account to avoid "in-subtitles" advertisment and bypass download limits
# Be careful about your password security, it will be stored right here in plain text...
# You can also change opensubtitles.org language, it will be used for error codes and stuff
osd_username = ''
osd_password = ''
osd_language = 'en'

# ==== Language settings =======================================================
# Supported ISO codes: http://www.opensubtitles.org/addons/export_languages.php
#
# 1/ You can change the search language here by using either 2-letter (ISO 639-1)
# or 3-letter (ISO 639-2) language codes.
#
# 2/ You can also search for subtitles in several languages ​​at once:
# - opt_languages = ['eng','fre'] to search for subtitles in multiple languages. Highly recommended.
# - opt_languages = ['eng,fre'] to download the first language available only
opt_languages = ['eng']

# Write 2-letter language code (ex: _en) at the end of the subtitles file. 'on', 'off' or 'auto'.
# If you are regularly searching for several language at once, you sould use 'on'.
opt_language_suffix = 'auto'

# ==== GUI settings ============================================================

# Select your GUI. Can be overridden at run time with '--gui=xxx' argument.
# - auto (autodetection, fallback on CLI)
# - qt (pyQt4 interface)
# - gnome (GNOME/GTK based environments, using 'zenity' backend)
# - kde (KDE/Qt based environments, using 'kdialog' backend)
# - cli (Command Line Interface)
opt_gui = 'auto'

# Change the subtitles selection GUI size:
opt_gui_width  = 720
opt_gui_height = 320

# If the search by movie hash fails, search by file name will be used as backup
opt_backup_searchbyname = 'on'

# Subtitles selection mode. Can be overridden at run time with '-a' argument.
# - manual (in case of multiple results, let you choose the subtitles you want)
# - auto (automatically select the most downloaded subtitles)
opt_selection_mode     = 'manual'

# Various GUI options. You can set them to 'on', 'off' or 'auto'.
opt_selection_language = 'auto'
opt_selection_hi       = 'auto'
opt_selection_rating   = 'off'
opt_selection_count    = 'off'

# Enables extra output. Can be overridden at run time with '-v' argument.
opt_verbose            = 'off'

# ==== Super Print =============================================================
# priority: info, warning, error
# title: only for zenity messages
# message: full text, with tags and breaks (tag cleanup for terminal)
# verbose: is this message important?

def superPrint(priority, title, message):
    """Print messages through terminal, zenity, kdialog or Qt interface"""
    if opt_gui == 'qt':
        message = message.replace("\n", "<br>")
        alert = QtGui.QMessageBox()
        alert.setWindowTitle(title)
        alert.setWindowIcon(QtGui.QIcon.fromTheme("document-properties"))
        alert.setText(message)
        alert.exec_()

    elif opt_gui == 'gnome':
        if title:
            subprocess.call(['zenity', '--' + priority, '--title=' + title, '--text=' + message])
        else:
            subprocess.call(['zenity', '--' + priority, '--text=' + message])
    else:
        # Clean up formating tags from the zenity messages
        message = message.replace("\n\n", "\n")
        message = message.replace("<i>", "")
        message = message.replace("</i>", "")
        message = message.replace("<b>", "")
        message = message.replace("</b>", "")
        message = message.replace('\\"', '"')

        # Print message
        if opt_gui == 'kde':
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

# ==== QT Settings Management Window ===========================================
# If config file does not exists create it, put the default values and print the
# settings window, then get the values and write the config file.
#
# If config file does exists parse it and get the values.

subLang=[("Arabic","ara"),("Bengali","ben"),("Cantonese","yue"),("Dutch","nld"),("English","eng"),("Filipino","fil"),("French","fre"),("German","ger"),("Hindi","hin"),("Indonesian","ind"),("Italian","ita"),("Japanese","jpn"),("Korean","kor"),("Mandarin","mdr"),("Persian","per"),("Portuguese","por"),("Russian","rus"),("Spanish","spa"),("Swahili","swa"),("Turkish","tur"),("Vietnamese","vie")]

if "PyQt4" in sys.modules :
    class settingsWindow(QtGui.QDialog):
        def __init__(self,parent=None):
            super(settingsWindow,self).__init__(parent)
            QtGui.QMainWindow.__init__(self)
            self.setWindowTitle('OpenSubtitlesDownload  Settings ')
            self.setWindowIcon(QtGui.QIcon.fromTheme("document-properties"))

            # Languages selection gui (puchbuttons)
            self.langLabel = QtGui.QLabel("1/ Select the languages you need:")
            titleFont = QtGui.QFont()
            titleFont.setBold(True)
            titleFont.setUnderline(True)
            self.langLabel.setFont(titleFont)

            # Preferences selection gui (comboboxes)
            self.prefLabel = QtGui.QLabel("2/ Select your preferences:")
            self.prefLabel.setFont(titleFont)
            self.optLabel = QtGui.QLabel("Write 2-letter language code (ex: _en) at the end of the subtitles file ?")
            self.optBox = QtGui.QComboBox()
            self.optBox.setMaximumWidth(100)
            self.optBox.addItems(['auto','on','off'])
            self.modeLabel = QtGui.QLabel("Subtitles selection mode :")
            self.modeBox = QtGui.QComboBox()
            self.modeBox.setMaximumWidth(100)
            self.modeBox.addItems(['manual','auto'])

            # Columns in selection window (checkboxes)
            self.columnLabel = QtGui.QLabel("3/ Select the colums to show in the selection window:")
            self.columnLabel.setFont(titleFont)
            self.langBox = QtGui.QCheckBox("Subtitles language")
            self.hiBox = QtGui.QCheckBox("Hearing impaired version")
            self.rateBox = QtGui.QCheckBox("Users rating")
            self.countBox = QtGui.QCheckBox("Downloads count")

            # Help / Link to the wiki
            self.helpLabel = QtGui.QLabel("If you have some troubles: <a href=https://github.com/emericg/OpenSubtitlesDownload/wiki> Documentation </a> ")
            self.helpLabel.setOpenExternalLinks(True)

            # Finish button and its function
            self.finishButton = QtGui.QPushButton("Finish",self)
            self.connect(self.finishButton, QtCore.SIGNAL("clicked()"), self.doFinish)

            self.vbox = QtGui.QVBoxLayout()    # Main vertical layout
            self.grid = QtGui.QGridLayout()    # Grid layout for the languages buttons

            # Language section :
            self.vbox.addWidget(self.langLabel)
            self.vbox.addSpacing(30)

            # Create the buttons for languages from the list and add them to the layout
            x=0
            y=0
            self.pushLang=[]
            for i in range(0,len(subLang)) :
               self.pushLang.append(QtGui.QPushButton(subLang[i][0],self))
               self.pushLang[i].setCheckable(True)
               self.grid.addWidget(self.pushLang[i],x,y)
               y=(y+1)%3 # Coz we want 3 columns
               if y==0 : x=x+1

            self.vbox.addLayout(self.grid)

            # Add the other widgets to the layout vertical
            self.vbox.addSpacing(20)
            self.vbox.addWidget(self.prefLabel)
            self.vbox.addWidget(self.optLabel)
            self.vbox.addWidget(self.optBox)
            self.vbox.addWidget(self.modeLabel)
            self.vbox.addWidget(self.modeBox)
            self.vbox.addSpacing(30)
            self.vbox.addWidget(self.columnLabel)
            self.vbox.addWidget(self.langBox)
            self.vbox.addWidget(self.hiBox)
            self.vbox.addWidget(self.rateBox)
            self.vbox.addWidget(self.countBox)
            self.vbox.addSpacing(20)
            self.vbox.addWidget(self.helpLabel)
            self.vbox.addWidget(self.finishButton)

            self.setLayout(self.vbox)

        def doFinish(self):
            global opt_languages,opt_language_suffix, opt_selection_mode, opt_selection_language, opt_selection_hi, opt_selection_rating, opt_selection_count
            opt_languages = []

            # Get the values of the comboboxes and put them in the global ones :
            opt_language_suffix = self.optBox.currentText()
            opt_selection_mode = self.modeBox.currentText()
            
            # Same for the checkboxes :
            opt_selection_language='off'
            opt_selection_hi='off'
            opt_selection_rating='off'
            opt_selection_count='off'        
            if self.langBox.isChecked() : opt_selection_language='on'
            if self.hiBox.isChecked() : opt_selection_hi='on'
            if self.rateBox.isChecked() : opt_selection_rating='on'
            if self.countBox.isChecked() : opt_selection_count='on'

            # Get all the selected languages and construct the IDsList:
            check = 0
            for i in range(0,len(subLang)):
                if self.pushLang[i].isChecked() :
                    opt_languages.append(subLang[i][1])
                    check = 1

            # Close the window when its all saved (and if at least one lang is selected)
            if check == 1 : self.close()
            else : superPrint(self,self.windowTitle(),"Cannot save with those settings : choose at least one language please")

    def configQt(calledManually):
        global opt_languages, opt_language_suffix, opt_selection_mode, opt_selection_language, opt_selection_hi, opt_selection_rating, opt_selection_count
        # Try to get the xdg folder for the config file, if not we use $HOME/.config
        if os.getenv("XDG_CONFIG_HOME"):
            confdir = os.path.join (os.getenv("XDG_CONFIG_HOME"), "OpenSubtitlesDownload")
            confpath = os.path.join (confdir, "OpenSubtitlesDownload.conf")
        else:
            confdir = os.path.join (os.getenv("HOME"), ".config/OpenSubtitlesDownload/")
            confpath = os.path.join (confdir, "OpenSubtitlesDownload.conf")

        if sys.version_info >= (3,0):
            confparser = configparser.SafeConfigParser()
        else: # python2
            confparser = ConfigParser.SafeConfigParser()
        
        if not os.path.isfile(confpath) or calledManually :
            # Create the conf folder if it doesn't exist :
            try:
                os.stat(confdir)
            except:
                os.mkdir(confdir)

            # Print the settings window :
            gui = settingsWindow()
            gui.exec_()

            # Write the conf file with the parser :
            confparser.add_section('languagesIDs')
            i = 0
            for ids in opt_languages :
                confparser.set ('languagesIDs', 'sublanguageids'+str(i),ids)
                i+=1

            confparser.add_section('settings')
            confparser.set ('settings', 'opt_language_suffix', str(opt_language_suffix))
            confparser.set ('settings', 'opt_selection_mode', str(opt_selection_mode))
            confparser.set ('settings', 'opt_selection_language', str(opt_selection_language))
            confparser.set ('settings', 'opt_selection_hi', str(opt_selection_hi))
            confparser.set ('settings', 'opt_selection_rating', str(opt_selection_rating))
            confparser.set ('settings', 'opt_selection_count', str(opt_selection_count))

            with open(confpath, 'w') as confile:
                confparser.write(confile)
        
        # If the file is already there we get the values :
        else :
            confparser.read(confpath)
            opt_languages=[]
            languages = ""
            for i in range(0,len(confparser.items('languagesIDs'))) :
                languages += confparser.get('languagesIDs', 'sublanguageids'+str(i)) + ","
            opt_languages.append(languages)
            opt_language_suffix = confparser.get ('settings', 'opt_language_suffix')
            opt_selection_mode = confparser.get ('settings', 'opt_selection_mode')
            opt_selection_language = confparser.get ('settings', 'opt_selection_language')
            opt_selection_hi = confparser.get ('settings', 'opt_selection_hi')
            opt_selection_rating = confparser.get ('settings', 'opt_selection_rating')
            opt_selection_count = confparser.get ('settings', 'opt_selection_count')

# ==== Check file path & file ==================================================

def checkFile(path):
    """Check mimetype and/or file extension to detect valid video file"""
    if os.path.isfile(path) == False:
        superPrint("error", "File type error!", "This is not a file:\n<i>" + path + "</i>")
        return False

    fileMimeType, encoding = mimetypes.guess_type(path)
    if fileMimeType == None:
        fileExtension = path.rsplit('.', 1)
        if fileExtension[1] not in ['avi', 'mp4', 'mov', 'mkv', 'mk3d', 'webm', \
        'ts', 'mts', 'm2ts', 'ps', 'vob', 'evo', 'mpeg', 'mpg', \
        'm1v', 'm2p', 'm2v', 'm4v', 'movhd', 'movx', 'qt', \
        'mxf', 'ogg', 'ogm', 'ogv', 'rm', 'rmvb', 'flv', 'swf', \
        'asf', 'wm', 'wmv', 'wmx', 'divx', 'x264', 'xvid']:
            superPrint("error", "File type error!", "This file is not a video (unknown mimetype AND invalid file extension):\n<i>" + path + "</i>")
            return False
    else:
        fileMimeType = fileMimeType.split('/', 1)
        if fileMimeType[0] != 'video':
            superPrint("error", "File type error!", "This file is not a video (unknown mimetype):\n<i>" + path + "</i>")
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
            superPrint("error", "File size error!", "File size error while generating hash for this file:\n<i>" + path + "</i>")
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
        superPrint("error", "I/O error!", "Input/Output error while generating hash for this file:\n<i>" + path + "</i>")
        return "IOError"

# ==== Qt subs window : Cross platform subtitles selection window ==============

if "PyQt4" in sys.modules :
    class subsWindow(QtGui.QDialog):
        def __init__(self,parent=None):
            super(subsWindow,self).__init__(parent)
            QtGui.QMainWindow.__init__(self)
            self.setWindowTitle('OpenSubtitlesDownload : Choose you subtitle')
            self.setWindowIcon(QtGui.QIcon.fromTheme("document-properties"))
            self.resize(opt_gui_width, opt_gui_height)

            self.vBox = QtGui.QVBoxLayout()    # Main vertical layout

            # Title and filename of the video , each in a horizontal layout
            labelFont = QtGui.QFont()
            labelFont.setBold(True)
            self.titleTxtLabel = QtGui.QLabel("Title : ")
            self.titleTxtLabel.setFont(labelFont)
            self.titleLabel = QtGui.QLabel(videoTitle.replace("\\", ""))
            self.titleHBox = QtGui.QHBoxLayout()
            self.titleHBox.addWidget(self.titleTxtLabel)
            self.titleHBox.addWidget(self.titleLabel)
            self.titleHBox.addStretch(1)            

            self.nameTxtLabel = QtGui.QLabel("Filename : ")
            self.nameTxtLabel.setFont(labelFont)
            self.nameLabel = QtGui.QLabel(videoFileName)
            self.nameHBox = QtGui.QHBoxLayout()            
            self.nameHBox.addWidget(self.nameTxtLabel)
            self.nameHBox.addWidget(self.nameLabel)
            self.nameHBox.addStretch(1)

            # Table containing the list of the subtitles :
            self.subTable = QtGui.QTableWidget()
            self.subTable.setShowGrid(False)   # Don't show the table grid
            self.subTable.setSelectionBehavior(1) # 1 = QAbstractItemView::SelectRows, selecting only rows 
            self.subTable.verticalHeader().setVisible(False)  # Don't print the lines number
            self.subTable.horizontalHeader().setResizeMode(3) # 3 = mode resize based on the contents 
            self.subTable.horizontalHeader().setStretchLastSection(True)

            ## Set col and lines nunbers depending on on the user's choices and the number of item in the list 
            self.hLabels = "Available subtitles (synchronized)"
            self.colCount = 1 

            # Build the colums an their labels, depending on the user's choices
            if opt_selection_language == "on" :
                self.hLabels += ";Language"
                self.colCount += 1

            if opt_selection_hi == "on" :
                self.hLabels += ";HI"
                self.colCount += 1

            if opt_selection_rating == "on" :
                self.hLabels += ";Rating"
                self.colCount += 1

            if opt_selection_count == "on" :
                self.hLabels += ";Downloads"
                self.colCount += 1

            self.subTable.setColumnCount(self.colCount)
            self.subTable.setHorizontalHeaderLabels(self.hLabels.split(";"))
            self.subTable.setRowCount(len(subtitlesList['data']))

            # Set the content of the table :
            rowIndex = 0

            for sub in subtitlesList['data']:
                colIndex = 0
                item = QtGui.QTableWidgetItem(sub['SubFileName'])
                item.setFlags(QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsSelectable)  # Flags to disable editing of the cells   
                self.subTable.setItem(rowIndex,colIndex, item)

                if opt_selection_language == "on" :
                    colIndex += 1
                    item = QtGui.QTableWidgetItem(sub['LanguageName'])
                    item.setTextAlignment(0x0004) # Center the content of the cell
                    item.setFlags(QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsSelectable)
                    self.subTable.setItem(rowIndex,colIndex, item)

                if opt_selection_hi == 'on' :
                    colIndex += 1
                    if sub['SubHearingImpaired'] == '1' :
                        item = QtGui.QTableWidgetItem(u'\u2713')
                        self.subTable.setItem(rowIndex,colIndex, item)
                    else :
                        item = QtGui.QTableWidgetItem("")
                        self.subTable.setItem(rowIndex,colIndex, item)
                    item.setTextAlignment(0x0004)
                    item.setFlags(QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsSelectable)

                if opt_selection_rating == "on" :
                    colIndex += 1
                    item = QtGui.QTableWidgetItem(sub['SubRating'])
                    item.setTextAlignment(0x0004)         
                    item.setFlags(QtCore.Qt.ItemIsEnabled)       
                    item.setFlags(QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsSelectable)

                if opt_selection_count == "on" :
                    colIndex += 1
                    item = QtGui.QTableWidgetItem(sub['SubDownloadsCnt'])
                    item.setTextAlignment(0x0004)
                    item.setFlags(QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsSelectable)
                    self.subTable.setItem(rowIndex,colIndex, item)
                
                rowIndex += 1 # Next row
            self.subTable.selectRow(0) # select the first row by default 

            # Create the buttons and connect them to the right function
            self.settingsButton = QtGui.QPushButton("Settings",self)
            self.connect(self.settingsButton, QtCore.SIGNAL("clicked()"), self.doConfig)
            self.cancelButton = QtGui.QPushButton("Cancel",self)
            self.connect(self.cancelButton, QtCore.SIGNAL("clicked()"), self.doCancel)
            self.okButton = QtGui.QPushButton("Accept",self)
            self.okButton.setDefault(True)
            self.connect(self.okButton, QtCore.SIGNAL("clicked()"), self.doAccept)

            # Put the bottom buttons in a H layout, Cancel and validate buttons are pushed to the bottom right corner :
            self.buttonHBox = QtGui.QHBoxLayout()
            self.buttonHBox.addWidget(self.settingsButton)
            self.buttonHBox.addStretch(1)
            self.buttonHBox.addWidget(self.cancelButton)
            self.buttonHBox.addWidget(self.okButton)

            # Put the differents layouts in the main vertical one  
            self.vBox.addLayout(self.titleHBox)
            self.vBox.addLayout(self.nameHBox)
            self.vBox.addWidget(self.subTable)
            self.vBox.addLayout(self.buttonHBox)
            self.setLayout(self.vBox)

            self.next = False # Variable to know if we continue the script after this window

        def doCancel(self):
            self.close()

        def doAccept(self):
            self.next = True
            self.selectedSub = str(self.subTable.item(self.subTable.currentRow(),0).text())
            self.close()

        def doConfig(self):
            configQt(True)
            self.close()

        def closeEvent(self,event):
            if not self.next : # If cancel or X corner clicked, we close the script !
                sys.exit(0)

    def selectionQt(subtitlesList): 
        gui = subsWindow()
        gui.exec_()
        return gui.selectedSub

# ==== Qt download window, thread and function =================================

if "PyQt4" in sys.modules :
    class downloadWindow(QtGui.QDialog):
        def __init__(self,subtitleURL,subtitlePath,parent=None):
            super(downloadWindow,self).__init__(parent)
            QtGui.QMainWindow.__init__(self)
            self.setWindowTitle('OpenSubtitlesDownload : Downloading ...')
            self.setWindowIcon(QtGui.QIcon.fromTheme("document-properties"))
            self.resize(380,90)
            
            # Create a progress bar and a label, add them to the main vertical layout
            self.vBox = QtGui.QVBoxLayout()
            self.progressBar = QtGui.QProgressBar(self)
            self.progressBar.setRange(0,0)
            self.vBox.addWidget(self.progressBar)
            self.label = QtGui.QLabel("Please wait while the subtitles are being downloaded")
            self.label.setAlignment(QtCore.Qt.AlignCenter)
            self.vBox.addWidget(self.label)
            self.setLayout(self.vBox)

            def onFinished():
                self.progressBar.setRange(0,1)
                self.close()

            # Initiate the dowloading task in a thread
            self.task = downloadThread(subtitleURL, subtitlePath)
            self.task.finished.connect(onFinished)
            self.task.start()

    # Thread for downloading the sub and when done emit the signal to close the window
    class downloadThread(QtCore.QThread):
        def __init__(self, subtitleURL, subtitlePath, parent=None) :
            super(downloadThread,self).__init__(parent)
            finished = QtCore.pyqtSignal()
            self.subURL = subtitleURL
            self.subPath = subtitlePath
             
        def run(self):
            if sys.version_info >= (3,0):            
                response = urllib.urlretrieve(self.subURL)
            else :
                response = urllib2.urlopen(self.subURL)

            tmpFile = gzip.GzipFile(fileobj=StringIO.StringIO(response.read()))

            with open(self.subPath, 'w') as outfile:
                outfile.write(tmpFile.read())

            self.finished.emit()

    def downloadQt(subtitleURL,subtitlePath):
        gui = downloadWindow(subtitleURL,subtitlePath)
        gui.exec_()

        if os.path.isfile(subtitlePath) :
            return 0
        else :
            return 1

# ==== Gnome selection window ==================================================

def selectionGnome(subtitlesList):
    """Gnome subtitles selection window using zenity"""
    searchMode = 'moviehash'
    subtitlesSelected = ''
    subtitlesItems = ''
    columnLn = ''
    columnHi = ''
    columnRate = ''
    columnCount = ''

    # Generate selection window content
    for item in subtitlesList['data']:
        if item['MatchedBy'] != 'moviehash':
            searchMode = item['MatchedBy']
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
        if opt_selection_rating == 'on':
            columnRate = '--column="Rating" '
            subtitlesItems += '"' + item['SubRating'] + '" '
        if opt_selection_count == 'on':
            columnCount = '--column="Downloads" '
            subtitlesItems += '"' + item['SubDownloadsCnt'] + '" '

    # Spawn zenity "list" dialog
    if searchMode == 'moviehash':
        process_subtitlesSelection = subprocess.Popen('zenity --width=' + str(opt_gui_width) + ' --height=' + str(opt_gui_height) + \
            ' --list --title="Synchronized subtitles for: ' + videoTitle + '"' + \
            ' --text="<b>Title:</b> ' + videoTitle + '\n<b>Filename:</b> ' + videoFileName + '"' + \
            ' --column="Available subtitles (synchronized)" ' + columnHi + columnLn + columnRate + columnCount + subtitlesItems,
            shell=True, stdout=subprocess.PIPE)
    else:
        process_subtitlesSelection = subprocess.Popen('zenity --width=' + str(opt_gui_width) + ' --height=' + str(opt_gui_height) + \
            ' --list --title="Subtitles found!"' + \
            ' --text="<b>Filename:</b> ' + videoFileName + '\n<b>>> These results comes from search by file name (not using movie hash) and may be unreliable...</b>"' + \
            ' --column="Available subtitles" ' + columnHi + columnLn + columnRate + columnCount + subtitlesItems,
            shell=True, stdout=subprocess.PIPE)

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
    """Automatic subtitles selection using filename match"""

    videoFileParts = videoFileName.replace('-','.').replace(' ','.').replace('_','.').lower().split('.')
    maxScore = -1

    for subtitle in subtitlesList['data']:
        subFileParts = subtitle['SubFileName'].replace('-','.').replace(' ','.').replace('_','.').lower().split('.');
        score = 0
        if subtitle['MatchedBy'] == 'moviehash':
            score = score + 1 # extra point if the sub is found by hash, which is the preferred way to find subs
        for subPart in subFileParts:
            for filePart in videoFileParts:
                if subPart == filePart:
                    score = score + 1
        if score > maxScore:
            maxScore = score
            subtitlesSelected = subtitle['SubFileName']

    return subtitlesSelected

# ==== Check dependencies ======================================================

def dependencyChecker():
    """Check the availability of tools used as dependencies"""

    if sys.version_info >= (3,3):
        for tool in ['gunzip', 'wget']:
            path = shutil.which(tool)
            if path is None:
                superPrint("error", "Missing dependency!", "The <b>'" + tool + "'</b> tool is not available, please install it!")
                return False

    return True

# ==== Main program (execution starts here) ====================================
# ==============================================================================

# ==== Argument parsing

# Get OpenSubtitlesDownload.py script path
execPath = str(sys.argv[0])

# Setup parser
parser = argparse.ArgumentParser(prog='OpenSubtitlesDownload.py',
    description='This software is designed to help you find and download subtitles for your favorite videos!',
    formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('-g', '--gui', help="Select the GUI you want from: auto, kde, gnome, cli (default: auto)")
parser.add_argument('-a', '--auto', help="Automatically choose the best subtitles, without human interaction (default: disabled)", action='store_true')
parser.add_argument('-v', '--verbose', help="Enables verbose output (default: disabled)", action='store_true')
parser.add_argument('-l', '--lang', help="Specify the language in which the subtitles should be downloaded (default: eng).\nSyntax:\n-l eng,fre : search in both language\n-l eng -l fre : download both language", nargs='?', action='append')
parser.add_argument('filePathListArg', help="The video file(s) for which subtitles should be searched and downloaded", nargs='+')

# Only use ArgumentParser if we have arguments...
if len(sys.argv) > 1:

    # Parsing
    result = parser.parse_args()

    # Handle results
    if result.gui:
        opt_gui = result.gui
    if result.auto:
        opt_selection_mode = 'auto'
    if result.verbose:
        opt_verbose = 'on'
    if result.lang:
        if opt_languages != result.lang:
            opt_languages = result.lang
            opt_selection_language = 'on'
            if opt_language_suffix != 'off':
                opt_language_suffix = 'on'

# ==== GUI auto detection

if opt_gui == 'auto':
    # Note: "ps cax" only output the first 15 characters of the executable's names
    ps = str(subprocess.Popen(['ps', 'cax'], stdout=subprocess.PIPE).communicate()[0]).split('\n')
    for line in ps:
        if "PyQt4" in sys.modules:
            opt_gui = 'qt'
            break
        if ('gnome-session' in line) or ('cinnamon-sessio' in line) or ('mate-session' in line) or ('xfce4-session' in line):
            opt_gui = 'gnome'
            break
        elif ('ksmserver' in line):
            opt_gui = 'kde'
            break

# Fallback
if opt_gui not in ['qt', 'gnome', 'kde', 'cli']:
    opt_gui = 'cli'
    opt_selection_mode = 'auto'
    print("Unknown GUI, falling back to an automatic CLI mode")

# ==== Check for the necessary tools (must be done after GUI auto detection)

if dependencyChecker() == False:
    sys.exit(1)

# ==== Get valid video paths

videoPathList = []

if 'result' in locals():
    # Go through the paths taken from arguments, and extract only valid video paths
    for i in result.filePathListArg:
        if checkFile(os.path.abspath(i)):
            videoPathList.append(os.path.abspath(i))
else:
    # No filePathListArg from the arg parser? Try selected file(s) from nautilus environment variables:
    # $NAUTILUS_SCRIPT_SELECTED_FILE_PATHS (only for local storage)
    # $NAUTILUS_SCRIPT_SELECTED_URIS
    if opt_gui == 'gnome':
        # Try to get file(s) provided by nautilus
        filePathListEnv = os.environ.get('NAUTILUS_SCRIPT_SELECTED_URIS')
        if filePathListEnv != None:
            # Check file(s) type and validity
            for filePath in filePathListEnv.splitlines():
                # Work a little bit of magic (Make sure we have a clean and absolute path, even from an URI)
                filePath = os.path.abspath(os.path.basename(filePath))
                if sys.version_info >= (3,0):
                    filePath = urllib.request.url2pathname(filePath)
                else: # python2
                    filePath = urllib2.url2pathname(filePath)
                if checkFile(filePath):
                    videoPathList.append(filePath)

# ==== Instances dispatcher

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
    command = execPath + " -g " + opt_gui
    if opt_selection_mode == 'auto':
        command += " -a "
    if opt_verbose == 'on':
        command += " -v "
    if not (len(opt_languages) == 1 and opt_languages[0] == 'eng'):
        for resultlangs in opt_languages:
            command += " -l " + resultlangs

    # Split command string
    command_splitted = command.split()
    # The videoPath filename can contain spaces, but we do not want to split that, so add it right after the split
    command_splitted.append(videoPathDispatch)

    if opt_gui == 'cli' and opt_selection_mode == 'manual':
        # Synchronous call
        process_videoDispatched = subprocess.call(command_splitted)
    else:
        # Asynchronous call
        process_videoDispatched = subprocess.Popen(command_splitted)

    # Do not spawn too many instances at the same time
    time.sleep(0.33)

# ==== Main program ============================================================
# ==== Search and download subtitles

if opt_gui == 'qt' :
    app = QtGui.QApplication(sys.argv)
    configQt(False)

try:
    try:
        # Connection to opensubtitles.org server
        session = osd_server.LogIn(osd_username, osd_password, osd_language, 'opensubtitles-download 4.0')
    except Exception:
        # Retry once, it could be a momentary overloaded server?
        time.sleep(3)
        try:
            # Connection to opensubtitles.org server
            session = osd_server.LogIn(osd_username, osd_password, osd_language, 'opensubtitles-download 4.0')
        except Exception:
            # Failed connection attempts?
            superPrint("error", "Connection error!", "Unable to reach opensubtitles.org servers!\n\nPlease check:\n- Your Internet connection status\n- www.opensubtitles.org availability\n- Your downloads limit (200 subtitles per 24h)\nThe subtitles search and download service is powered by opensubtitles.org. Be sure to donate if you appreciate the service provided!")
            sys.exit(1)

    # Connection refused?
    if session['status'] != '200 OK':
        superPrint("error", "Connection error!", "Opensubtitles.org servers refused the connection: " + session['status'] + ".\n\nPlease check:\n- Your Internet connection status\n- www.opensubtitles.org availability\n- Your 200 downloads per 24h limit")
        sys.exit(1)

    searchLanguage = 0
    searchLanguageResult = 0
    videoTitle = 'Unknown video title'
    videoHash = hashFile(videoPath)
    videoSize = os.path.getsize(videoPath)
    videoFileName = os.path.basename(videoPath)

    # Count languages marked for this search
    for SubLanguageID in opt_languages:
        searchLanguage += len(SubLanguageID.split(','))

    # Search for available subtitles using file hash and size
    for SubLanguageID in opt_languages:
        searchList = []
        searchList.append({'sublanguageid':SubLanguageID, 'moviehash':videoHash, 'moviebytesize':str(videoSize)})
        try:
            subtitlesList = osd_server.SearchSubtitles(session['token'], searchList)
        except Exception:
            # Retry once, we are already connected, the server is probably momentary overloaded
            time.sleep(3)
            try:
                subtitlesList = osd_server.SearchSubtitles(session['token'], searchList)
            except Exception:
                superPrint("error", "Search error!", "Unable to reach opensubtitles.org servers!\n<b>Search error</b>")

        # No results using search by hash? Retry with filename
        if (not subtitlesList['data']) and (opt_backup_searchbyname == 'on'):
            searchList = []
            searchList.append({'sublanguageid':SubLanguageID, 'query':videoFileName})
            try:
                subtitlesList = osd_server.SearchSubtitles(session['token'], searchList)
            except Exception:
                # Retry once, we are already connected, the server is probably momentary overloaded
                time.sleep(3)
                try:
                    subtitlesList = osd_server.SearchSubtitles(session['token'], searchList)
                except Exception:
                    superPrint("error", "Search error!", "Unable to reach opensubtitles.org servers!\n<b>Search error</b>")
        else:
            opt_backup_searchbyname = 'off'

        # Parse the results of the XML-RPC query
        if subtitlesList['data']:

            # Mark search as successful
            searchLanguageResult += 1
            subtitlesSelected = ''

            # If there is only one subtitles, which wasn't found by filename, auto-select it
            if (len(subtitlesList['data']) == 1) and (opt_backup_searchbyname == 'off'):
                subtitlesSelected = subtitlesList['data'][0]['SubFileName']

            # Get video title
            videoTitle = subtitlesList['data'][0]['MovieName']

            # Title and filename may need string sanitizing to avoid zenity/kdialog handling errors
            if opt_gui != 'cli':
                videoTitle = videoTitle.replace('"', '\\"')
                videoTitle = videoTitle.replace("'", "\'")
                videoTitle = videoTitle.replace('`', '\`')
                videoTitle = videoTitle.replace("&", "&amp;")
                videoFileName = videoFileName.replace('"', '\\"')
                videoFileName = videoFileName.replace("'", "\'")
                videoFileName = videoFileName.replace('`', '\`')
                videoFileName = videoFileName.replace("&", "&amp;")

            # If there is more than one subtitles and opt_selection_mode != 'auto',
            # then let the user decide which one will be downloaded
            if subtitlesSelected == '':
                # Automatic subtitles selection?
                if opt_selection_mode == 'auto':
                    subtitlesSelected = selectionAuto(subtitlesList)
                else:
                    # Go through the list of subtitles and handle 'auto' settings activation
                    for item in subtitlesList['data']:
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

                    # Spaw selection window
                    if opt_gui == 'qt':
                        subtitlesSelected = selectionQt(subtitlesList)
                    elif opt_gui == 'gnome':
                        subtitlesSelected = selectionGnome(subtitlesList)
                    elif opt_gui == 'kde':
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
                if ((opt_language_suffix == 'on') or
                    (opt_language_suffix == 'auto' and searchLanguageResult > 1)):
                    subPath = videoPath.rsplit('.', 1)[0] + subLangId + '.' + subtitlesList['data'][subIndex]['SubFormat']

                # Escape non-alphanumeric characters from the subtitles path
                subPath = re.escape(subPath)

                # Download and unzip the selected subtitles (with progressbar)
                if opt_gui == 'qt':
                    subPath = subPath.replace("\\", "")
                    process_subtitlesDownload = downloadQt(subURL,subPath)
                elif opt_gui == 'gnome':
                    process_subtitlesDownload = subprocess.call("(wget -q -O - " + subURL + " | gunzip > " + subPath + ") 2>&1" + ' | (zenity --auto-close --progress --pulsate --title="Downloading subtitles, please wait..." --text="Downloading <b>' + subtitlesList['data'][subIndex]['LanguageName'] + '</b> subtitles for <b>' + videoTitle + '</b>...")', shell=True)
                elif opt_gui == 'kde':
                    process_subtitlesDownload = subprocess.call("(wget -q -O - " + subURL + " | gunzip > " + subPath + ") 2>&1", shell=True)
                else: # CLI
                    print(">> Downloading '" + subtitlesList['data'][subIndex]['LanguageName'] + "' subtitles for '" + videoTitle + "'")
                    process_subtitlesDownload = subprocess.call("wget -nv -O - " + subURL + " | gunzip > " + subPath, shell=True)

                # If an error occurs, say so
                if process_subtitlesDownload != 0:
                    superPrint("error", "Subtitling error!", "An error occurred while downloading or writing <b>" + subtitlesList['data'][subIndex]['LanguageName'] + "</b> subtitles for <b>" + videoTitle + "</b>.")
                    osd_server.LogOut(session['token'])
                    sys.exit(1)

    # Print a message if no subtitles have been found, for any of the languages
    if searchLanguageResult == 0:
        superPrint("info", "No subtitles found for: " + videoFileName, '<b>No subtitles found</b> for this video:\n<i>' + videoFileName + '</i>')

    # Disconnect from opensubtitles.org server, then exit
    if session['token']: osd_server.LogOut(session['token'])
    sys.exit(0)

except (RuntimeError, TypeError, NameError, IOError, OSError):

    # Do not warn about remote disconnection # bug/feature of python 3.5
    if "http.client.RemoteDisconnected" in str(sys.exc_info()[0]):
        sys.exit(1)

    # An unknown error occur, let's apologize before exiting
    superPrint("error", "Unknown error!", "OpenSubtitlesDownload encountered an <b>unknown error</b>, sorry about that...\n\n" + \
               "Error: <b>" + str(sys.exc_info()[0]).replace('<', '[').replace('>', ']') + "</b>\n\n" + \
               "Just to be safe, please check:\n- www.opensubtitles.org availability\n- Your downloads limit (200 subtitles per 24h)\n- Your Internet connection status\n- That are using the latest version of this software ;-)")

    # Disconnect from opensubtitles.org server, then exit
    if session['token']: osd_server.LogOut(session['token'])

    sys.exit(1)
