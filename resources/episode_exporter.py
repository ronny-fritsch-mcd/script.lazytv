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

''' A script to copy all the latest episodes included in the LazyTV listview to a folder selected by the user'''

import os
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import sys
import shutil
import time
import traceback
import ast
import json


__addon__        = xbmcaddon.Addon('script.lazytv')
__addonid__      = __addon__.getAddonInfo('id')
__setting__      = __addon__.getSetting
dialog           = xbmcgui.Dialog()
scriptPath       = __addon__.getAddonInfo('path')
addon_path       = xbmcvfs.translatePath('special://home/addons')
keep_logs        = True if __setting__('logging') == 'true' else False
filterYN         = True if __setting__('filterYN') == 'true' else False
populate_by_d    = __setting__('populate_by_d')
default_playlist = __setting__('file')
select_pl        = __setting__('select_pl')


start_time       = time.time()
base_time        = time.time()

WINDOW           = xbmcgui.Window(10000)

try:
	spec_shows = ast.literal_eval(__setting__('selection'))
except:
	spec_shows = []

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
		logmsg       = '%s : %s :: %s ::: %s - %s ' % ('LazyTV episode_exporter', total_gap, gap_time, label, message)
		xbmc.log(msg=logmsg, level=xbmc.LOGINFO)


def json_query(query, ret):
	try:
		xbmc_request = json.dumps(query)
		result = xbmc.executeJSONRPC(xbmc_request)
		if ret:
			return json.loads(result)['result']
		else:
			return json.loads(result)
	except:
		return {}


def get_files():
	''' entry point for the file retrieval process_stored
		follows the same logic as creating a listview.
		'''
	try:
		provided_shows = sys.argv[1].split(':-exporter-:')
		return provided_shows
	
	except:

		if filterYN:

			if populate_by_d == '1':

				if select_pl == '0':
					selected_pl = playlist_selection_window()
					population = {'playlist': selected_pl}

				else:
					#get setting for default_playlist
					if not default_playlist:
						population = {'none':''}
					else:
						population = {'playlist': default_playlist}
			else:
				population = {'usersel':spec_shows}
		else:
			population = {'none':''}

		stored_file_data_filtered = process_stored(population)

		return stored_file_data_filtered


def process_stored(population):
	''' this function allows for the optional conversion of playlists to showlists
		'''

	stored_file_data = get_TVshows()

	if 'playlist' in population:
		extracted_showlist = convert_pl_to_showlist(population['playlist'])
	elif 'usersel' in population:
		extracted_showlist = population['usersel']
	else:
		extracted_showlist = False

	if extracted_showlist:
		stored_file_data_filtered  = [x[0] for x in stored_file_data if x[1] in extracted_showlist]
	else:
		stored_file_data_filtered = [x[0] for x in stored_file_data]

	log('process_stored_End')

	return stored_file_data_filtered


def convert_pl_to_showlist(pop):
	''' converts the playlist to a showlist
		'''

	# derive filtered_showids from smart playlist
	filename = os.path.split(pop)[1]
	clean_path = 'special://profile/playlists/video/' + filename

	#retrieve the shows in the supplied playlist, save their ids to a list
	plf  = {"jsonrpc": "2.0","id": 1, "method": "Files.GetDirectory", 		"params": {"directory": "special://profile/playlists/video/", "media": "video"}}
	plf['params']['directory'] = clean_path

	playlist_contents = json_query(plf, True)

	if 'files' not in playlist_contents:
		sys.exit()
	else:
		if not playlist_contents.get('files'):
			sys.exit()
		else:
			filtered_showids = [x['id'] for x in playlist_contents['files'] if x.get('type') == 'tvshow']
			log(str(filtered_showids), 'showids in playlist')
			if not filtered_showids:
				sys.exit()

	#returns the list of all and filtered shows and episodes
	return filtered_showids


def get_TVshows():
	''' gets all the TV shows that have unwatched episodes, and gets the union of that list with the list that is stored
		'''

	#get the most recent info on inProgress TV shows, cross-check it with what is currently stored
	query          = '{"jsonrpc": "2.0","method": "VideoLibrary.GetTVShows","params": {"filter": {"field": "playcount", "operator": "is", "value": "0" },"properties": ["lastplayed"], "sort": {"order": "descending", "method": "lastplayed"} },"id": "1" }'

	nepl_retrieved = json.loads(xbmc.executeJSONRPC(query))

	log('get_TVshows_querycomplete')

	if 'result' in nepl_retrieved and 'tvshows' in nepl_retrieved["result"] and nepl_retrieved['result']['tvshows']:
		nepl_retrieved = nepl_retrieved['result']['tvshows']
	else:
		nepl_retrieved = {}


	nepl_from_service = WINDOW.getProperty("LazyTV.nepl")

	if nepl_from_service:
		p = ast.literal_eval(nepl_from_service)
		nepl_stored = [int(x) for x in p]
	else:
		dialog.ok('LazyTV',lang(32115),lang(32116))
		sys.exit()

	nepl = [x['tvshowid'] for x in nepl_retrieved if x['tvshowid'] in nepl_stored]

	stored_file_data = [[WINDOW.getProperty(f"LazyTV.{x}.File"),x] for x in nepl]

	log('get_TVshows_End')

	return stored_file_data


def Main():

	# open location selection window
	location = dialog.browse(3,lang(32180),'files')
	if not location:
		return

	log("export location: " + str(location))

	# get file of selected shows
	file_list = get_files()
	if not file_list:
		dialog.ok('LazyTV', 'No files to export.')
		return


	dProgress = xbmcgui.DialogProgress()
	dProgress.create('LazyTV', lang(32183))

	sizes = []
	for f in file_list:
		try:
			sizes.append(xbmcvfs.Stat(f).st_size())
		except:
			sizes.append(0)
	total_size = float(sum(sizes))
	running_size = 0

	failures = []

	for i, video_file in enumerate(file_list):

		if (dProgress.iscanceled()): 
			log('user aborted')
			break

		prog = (running_size / total_size) * 100 if total_size > 0 else 0
		fn = os.path.basename(video_file)
		dProgress.update(int(prog), lang(32184), str(fn))

		try:
			dest_file = os.path.join(location, fn)
			if not xbmcvfs.exists(dest_file):
				xbmcvfs.copy(video_file, dest_file)
				log("file exported: " + str(fn))
			else:
				log('file already exists at location: ' + str(fn))
		except Exception as e:
			failures.append(fn)
			log(f"file failed to export: {fn}, Error: {e}")

		running_size += sizes[i]

	dProgress.close()

	if failures:
		ans = dialog.yesno('LazyTV', lang(32182), lang(32183))
		if ans:
			failures.sort()
			dialog.select('LazyTV', failures)
	else:
		xbmc.sleep(100)
		dialog.ok('LazyTV', lang(32185))
		log('file export successful')


if __name__ == "__main__":

	Main()