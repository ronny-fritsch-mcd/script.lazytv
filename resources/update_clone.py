#!/usr/bin/python
# -*- coding: utf-8 -*-

#  Copyright (C) 2013 KodeKarnage
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html

''' A script to update this cloned version of LazyTV from the main LazyTV install '''

import shutil
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import re
import sys
import time
import os
from xml.etree import ElementTree as et
import fileinput
import traceback

src_path   = sys.argv[1]
new_path   = sys.argv[2]
san_name   = sys.argv[3]
clone_name = sys.argv[4]

__addon__        = xbmcaddon.Addon('script.lazytv')
__addonid__      = __addon__.getAddonInfo('id')
__setting__      = __addon__.getSetting
dialog           = xbmcgui.Dialog()

start_time       = time.time()
base_time        = time.time()

keep_logs        = True if __setting__('logging') == 'true' else False

def lang(id):
	return __addon__.getLocalizedString(id)

def log(message, label = '', reset = False):
	if keep_logs:
		global start_time
		global base_time
		new_time     = time.time()
		gap_time     = "%5f" % (new_time - start_time)
		start_time   = new_time
		total_gap    = "%5f" % (new_time - base_time)
		logmsg       = '%s : %s :: %s ::: %s - %s ' % ('lazyTV addon updater', total_gap, gap_time, label, message)
		xbmc.log(msg=logmsg, level=xbmc.LOGINFO)
		base_time    = start_time if reset else base_time


def errorHandle(exception, trace, new_path=False):
		log('An error occurred while creating the clone.')
		log(str(exception))
		log(str(trace))
		dialog.ok('LazyTV', lang(32140),lang(32141))
		if new_path and os.path.exists(new_path):
			shutil.rmtree(new_path, ignore_errors=True)
		sys.exit()


def Main():
	try:
		if os.path.exists(new_path):
			shutil.rmtree(new_path)

		IGNORE_PATTERNS = ('.pyc','CVS','.git','tmp','.svn')
		shutil.copytree(xbmcvfs.translatePath(src_path), new_path, ignore=shutil.ignore_patterns(*IGNORE_PATTERNS))

		addon_file = os.path.join(new_path,'addon.xml')
		if os.path.exists(os.path.join(new_path,'service.py')): os.remove(os.path.join(new_path,'service.py'))
		if os.path.exists(addon_file): os.remove(addon_file)
		if os.path.exists(os.path.join(new_path,'resources','settings.xml')): os.remove(os.path.join(new_path,'resources','settings.xml'))
		if os.path.exists(os.path.join(new_path,'resources','clone.py')): os.remove(os.path.join(new_path,'resources','clone.py'))

		shutil.move( os.path.join(new_path,'resources','addon_clone.xml') , addon_file )
		shutil.move( os.path.join(new_path,'resources','settings_clone.xml') , os.path.join(new_path,'resources','settings.xml') )

	except Exception as e:
		ex_type, ex, tb = sys.exc_info()
		errorHandle(e, traceback.format_tb(tb), new_path)

	tree = et.parse(addon_file)
	root = tree.getroot()
	root.set('id', san_name)
	root.set('name', clone_name)
	summary = tree.find('.//summary')
	if summary is not None:
		summary.text = clone_name
	tree.write(addon_file, encoding='utf-8', xml_declaration=True)

	py_files = [os.path.join(new_path,'resources','selector.py') , os.path.join(new_path,'resources','playlists.py'),os.path.join(new_path,'resources','update_clone.py')]
	for py in py_files:
		if not os.path.exists(py): continue
		with fileinput.FileInput(py, inplace=True) as file:
			for line in file:
				print(line.replace('script.lazytv', san_name), end='')

	try:
		log('trying to disable then enable addon')
		xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,"params":{"addonid":"%s","enabled":false}}' % san_name)
		xbmc.sleep(1000)
		xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,"params":{"addonid":"%s", "enabled":true}}' % san_name)
	except:
		log('restart failed')
		pass

	dialog.ok('LazyTV', lang(32149),lang(32147))

if __name__ == "__main__":
	log('Updating started')
	Main()
	log('Updating complete')