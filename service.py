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

'''
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#@@@@@@@@@@
#@@@@@@@@@@ - allow for next ep notification in LazyTV smartplaylist READY FOR TESTING
#@@@@@@@@@@ - suppress notification at start up READY FOR TESTING
#@@@@@@@@@@ - improve handling of specials
#@@@@@@@@@@ - improve refreshing of LazyTV Show Me window
#@@@@@@@@@@
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@'''


import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import time
import datetime
import ast
import json
import re
import random
import sys

# This is a throwaway variable to deal with a python bug
try:
	throwaway = datetime.datetime.strptime('20110101','%Y%m%d')
except:
	pass

__addon__              = xbmcaddon.Addon()
__addonid__            = __addon__.getAddonInfo('id')
__addonversion__       = tuple([int(x) for x in __addon__.getAddonInfo('version').split('.')])
__scriptPath__         = __addon__.getAddonInfo('path')
__profile__            = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))
__setting__            = __addon__.getSetting
videoplaylistlocation  = xbmcvfs.translatePath('special://profile/playlists/video/')
start_time             = time.time()
base_time              = time.time()
WINDOW                 = xbmcgui.Window(10000)
DIALOG                 = xbmcgui.Dialog()

WINDOW.setProperty("LazyTV.Version", str(__addonversion__))
WINDOW.setProperty("LazyTV.ServicePath", str(__scriptPath__))
WINDOW.setProperty('LazyTV_service_running', 'starting')

promptduration         = int(float(__setting__('promptduration')))
promptdefaultaction    = int(float(__setting__('promptdefaultaction')))

keep_logs              = True if __setting__('logging') 			== 'true' else False
playlist_notifications = True if __setting__("notify")  			== 'true' else False
resume_partials        = True if __setting__('resume_partials') 	== 'true' else False
nextprompt             = True if __setting__('nextprompt') 			== 'true' else False
nextprompt_or          = True if __setting__('nextprompt_or') 		== 'true' else False
prevcheck              = True if __setting__('prevcheck') 			== 'true' else False
moviemid               = True if __setting__('moviemid') 			== 'true' else False
first_run              = True if __setting__('first_run') 			== 'true' else False
startup                = True if __setting__('startup') 			== 'true' else False
maintainsmartplaylist  = True if __setting__('maintainsmartplaylist') 			== 'true' else False

if promptduration == 0:
	promptduration = 1 / 1000.0

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
		logmsg       = '%s : %s :: %s ::: %s - %s ' % (__addonid__ + 'service', total_gap, gap_time, label, message)
		xbmc.log(msg=logmsg, level=xbmc.LOGINFO)
		base_time    = start_time if reset else base_time


# get the current version of XBMC
versstr = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }')
vers = json.loads(versstr)
if 'result' in vers and 'version' in vers['result'] and (int(vers['result']['version']['major']) >= 13):
	__release__            = "Gotham"
else:
	__release__            = "Frodo"

whats_playing          = {"jsonrpc": "2.0","method": "Player.GetItem","params": {"properties": ["showtitle","tvshowid","episode", "season", "playcount", "resume"],"playerid": 1},"id": "1"}
now_playing_details    = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["playcount", "tvshowid"],"episodeid": "1"},"id": "1"}
ep_to_show_query       = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["lastplayed","tvshowid"],"episodeid": "1"},"id": "1"}
prompt_query           = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["season","episode","showtitle","tvshowid"],"episodeid": "1"},"id": "1"}
show_request           = {"jsonrpc": "2.0","method": "VideoLibrary.GetTVShows","params": {"filter": {"field": "playcount","operator": "is","value": "0"},"properties": ["genre","title","playcount","mpaa","watchedepisodes","episode","thumbnail"]},"id": "1"}
show_request_all       = {"jsonrpc": "2.0","method": "VideoLibrary.GetTVShows","params": {"properties": ["title"]},"id": "1"}
show_request_lw        = {"jsonrpc": "2.0","method": "VideoLibrary.GetTVShows","params": {"filter": {"field": "playcount", "operator": "is", "value": "0" },"properties": ["lastplayed"], "sort":{"order": "descending", "method":"lastplayed"} },"id": "1" }
eps_query              = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodes","params": {"properties": ["season","episode","runtime","resume","playcount","tvshowid","lastplayed","file"],"tvshowid": "1"},"id": "1"}
ep_details_query       = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["title","playcount","plot","season","episode","showtitle","file","lastplayed","rating","resume","art","streamdetails","firstaired","runtime","tvshowid"],"episodeid": 1},"id": "1"}
seek                   = {"jsonrpc": "2.0","id": 1, "method": "Player.Seek","params": {"playerid": 1, "value": 0 }}
plf                    = {"jsonrpc": "2.0","id": 1, "method": "Files.GetDirectory", "params": {"directory": "special://profile/playlists/video/", "media": "video"}}
add_this_ep            = {'jsonrpc': '2.0','id': 1, "method": 'Playlist.Add', 				"params": {'item' : {'episodeid' : 'placeholder' }, 'playlistid' : 1}}

log('Running: ' + str(__release__))


def json_query(query, ret):
	try:
		xbmc_request = json.dumps(query)
		result = xbmc.executeJSONRPC(xbmc_request)
		if ret:
			return json.loads(result)['result']
		else:
			return json.loads(result)
	except Exception as e:
		log(f"JSON query failed: {e}", label="ERROR")
		xbmc_request = json.dumps(query)
		result = xbmc.executeJSONRPC(xbmc_request)
		log(json.loads(result))
		return json.loads(result)


def stringlist_to_reallist(string):
	# this is needed because ast.literal_eval gives me EOF errors for no obvious reason
	real_string = string.replace("[","").replace("]","").replace(" ","").split(",")
	return real_string


def runtime_converter(time_string):
	if not time_string:
		return 0
	x = time_string.count(':')
	parts = time_string.split(':')
	try:
		if x == 0:
			return int(parts[0])
		elif x == 1:
			return int(parts[0]) * 60 + int(parts[1])
		elif x == 2:
			return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
	except (ValueError, IndexError):
		return 0
	return 0


def iStream_fix(show_npid,showtitle,episode_np,season_np):

	# streams from iStream dont provide the showid and epid for above
	# they come through as tvshowid = -1, but it has episode no and season no and show name
	# need to insert work around here to get showid from showname, and get epid from season and episode no's
	# then need to ignore prevcheck
	log('fixing istream, data follows...')
	log('show_npid = ' +str(show_npid))
	log('showtitle = ' +str(showtitle))
	log('episode_np = ' +str(episode_np))
	log('season_np = ' + str(season_np))
	redo = True
	count = 0
	ep_npid = None
	while redo and count < 2: 				# this ensures the section of code only runs twice at most
		redo = False
		count += 1
		if show_npid == -1 and showtitle and episode_np and season_np:
			prevcheck = False
			tmp_shows = json_query(show_request_all,True)
			log('tmp_shows = ' + str(tmp_shows))
			if 'tvshows'in tmp_shows:
				for x in tmp_shows['tvshows']:
					if x['label'] == showtitle:
						show_npid = x['tvshowid']
						eps_query['params']['tvshowid'] = show_npid
						tmp_eps = json_query(eps_query,True)
						log('tmp eps = '+ str(tmp_eps))
						if 'episodes' in tmp_eps:
							for y in tmp_eps['episodes']:
								if fix_SE(y['season']) == season_np and fix_SE(y['episode']) == episode_np:
									ep_npid = y['episodeid']
									log('playing epid stream = ' + str(ep_npid))

									# get odlist
									tmp_od_str = WINDOW.getProperty("%s.%s.odlist" % ('LazyTV', show_npid))
									tmp_od = ast.literal_eval(tmp_od_str) if tmp_od_str else []
									
									if show_npid in randos:
										tmpoff_str = WINDOW.getProperty("%s.%s.offlist" % ('LazyTV', show_npid))
										if tmpoff_str:
											tmp_od += ast.literal_eval(tmpoff_str)
									
									log('tmp od = ' + str(tmp_od))
									log('ep_npid = ' + str(ep_npid))
									if ep_npid not in tmp_od:
										log('iStream fix calls get eps')
										main_instance.get_eps([show_npid])
										log('iStream fix post get eps')
										redo = True

	return False, show_npid, ep_npid


def fix_SE(string):
	return f"{string:02d}"


def _breathe():
	# lets addon know the service is running
	if WINDOW.getProperty('LazyTV_service_running') == 'marco':
		WINDOW.setProperty('LazyTV_service_running', 'polo')


class LazyPlayer(xbmc.Player):
	def __init__(self, *args, **kwargs):
		xbmc.Player.__init__(self)
		self.np_next = False
		self.pl_running = 'null'
		self.playing_showid = False
		self.playing_epid = False
		self.nextprompt_trigger = False
		self.nextprompt_trigger_override = True

	def onPlayBackStarted(self):
		log('Playbackstarted',reset=True)
		global prevcheck

		main_instance.target = False
		self.nextprompt_trigger_override = True

		self.ep_details = json_query(whats_playing, True)
		log('this is playing = ' + str(self.ep_details))
		self.pl_running = WINDOW.getProperty("%s.playlist_running"	% ('LazyTV'))
		item = self.ep_details.get('item', {})

		if item and 'type' in item:
			pll = xbmc.getInfoLabel('VideoPlayer.PlaylistLength')
			if pll != '1' and not (self.pl_running == 'true' and nextprompt_or):
				log('nextprompt override')
				self.nextprompt_trigger_override = False

			if item['type'] in ['unknown', 'episode']:
				episode_np = fix_SE(item['episode'])
				season_np = fix_SE(item['season'])
				showtitle = item['showtitle']
				show_npid = int(item['tvshowid'])

				try:
					ep_npid = int(item['id'])
				except (KeyError, TypeError):
					if item.get('episode', -1) < 0:
						prevcheck, ep_npid, show_npid = False, None, None
					else:
						prevcheck, show_npid, ep_npid = iStream_fix(show_npid, showtitle, episode_np, season_np)

				log(f"prevcheck: {prevcheck}")

				if prevcheck and show_npid and show_npid not in randos and self.pl_running != 'true':
					log('Passed prevcheck')
					odlist_str = WINDOW.getProperty(f"LazyTV.{show_npid}.odlist")
					odlist = ast.literal_eval(odlist_str) if odlist_str else []
					stored_epid = int(WINDOW.getProperty(f"LazyTV.{show_npid}.EpisodeID"))
					stored_seas = fix_SE(int(WINDOW.getProperty(f"LazyTV.{show_npid}.Season")))
					stored_epis = fix_SE(int(WINDOW.getProperty(f"LazyTV.{show_npid}.Episode")))
					
					if ep_npid in odlist[1:] and stored_epid:
						xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":False},"id":1}')
						usr_note = DIALOG.yesno(lang(32160), lang(32161) % (showtitle, stored_seas, stored_epis), lang(32162))
						if usr_note:
							xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Player.Stop", "params": { "playerid": 1 }, "id": 1}')
							xbmc.sleep(100)
							xbmc.executeJSONRPC(f'{{ "jsonrpc": "2.0", "method": "Player.Open", "params": {{ "item": {{ "episodeid": {stored_epid} }}, "options":{{ "resume": true }}  }}, "id": 1 }}')
						else:
							xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":true},"id":1}')

				if self.pl_running == 'true' and playlist_notifications:
					xbmc.executebuiltin(f'Notification({lang(32163)},{showtitle} S{season_np}E{episode_np},5000)')

				if (self.pl_running == 'true' and resume_partials) or self.pl_running == 'listview':
					res_point = item.get('resume', {})
					if res_point.get('position', 0) > 0:
						seek_point = int((float(res_point['position']) / float(res_point['total'])) * 100)
						seek['params']['value'] = seek_point
						json_query(seek, True)

				self.playing_epid = ep_npid
				self.playing_showid = show_npid
				log(f'LazyPlayer supplied showid = {self.playing_showid}')
				log(f'LazyPlayer supplied epid = {self.playing_epid}')

			elif item['type'] == 'movie' and self.pl_running == 'true':
				if playlist_notifications:
					xbmc.executebuiltin(f'Notification({lang(32163)},{item["label"]},5000)')
				if resume_partials and item.get('resume', {}).get('position', 0) > 0:
					res_point = item['resume']
					seek_point = int((float(res_point['position']) / float(res_point['total'])) * 100)
					seek['params']['value'] = seek_point
					json_query(seek, True)
				elif moviemid and item.get('playcount', 0) != 0:
					duration = runtime_converter(xbmc.getInfoLabel('VideoPlayer.Duration'))
					if duration > 0:
						seek_point = int(100 * (duration * 0.75 * (random.random() ** 2)) / duration)
						seek['params']['value'] = seek_point
						json_query(seek, True)
		log('Playbackstarted_End')


	def onPlayBackStopped(self):
		pre_showid  = main_instance.nextprompt_info.get('tvshowid')
		if pre_showid:
			WINDOW.setProperty("%s.%s.Resume" % ('LazyTV', str(pre_showid)), 'true')
		self.onPlayBackEnded()


	def onPlayBackEnded(self):
		pre_seas  = main_instance.nextprompt_info.get('season', None)
		pre_ep    = main_instance.nextprompt_info.get('episode', None)
		pre_title = main_instance.nextprompt_info.get('showtitle', None)
		pre_epid  = main_instance.nextprompt_info.get('episodeid', None)
		paused    = False

		if any(v is None for v in [pre_seas, pre_ep, pre_title, pre_epid]):
			log('Main.nextprompt_info missing vital data')
			main_instance.nextprompt_info = {}
			return

		log('Playbackended', reset=True)
		self.playing_epid = False
		xbmc.sleep(500)
		self.now_name = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')

		if not self.now_name or (self.pl_running == 'true' and nextprompt_or):
			if not self.now_name and self.pl_running == 'true':
				WINDOW.setProperty("LazyTV.playlist_running", 'false')

			if self.nextprompt_trigger and self.nextprompt_trigger_override:
				if self.now_name:
					xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":False},"id":1}')
					paused = True

				self.nextprompt_trigger = False
				SE = f"{int(pre_seas)}x{int(pre_ep)}"
				ylabel = lang(32092) if promptdefaultaction == 0 else lang(32091)
				nlabel = lang(32091) if promptdefaultaction == 0 else lang(32092)

				prompt_kwargs = {
					"yeslabel": ylabel, "nolabel": nlabel,
					"autoclose": int(promptduration * 1000) if promptduration > 0.001 else 0
				}
				prompt = DIALOG.yesno(lang(32167) % promptduration, lang(32168) % (pre_title, SE), **prompt_kwargs)
				
				log(f'Dialog result: {prompt}')
				final_prompt = prompt
				if prompt == -1: # Autoclosed
					final_prompt = 0 if promptdefaultaction == 0 else 1

				log(f"nextep final prompt = {final_prompt}")

				if final_prompt:
					if paused: xbmc.Player().stop() # Stop paused playback before starting new
					xbmc.executeJSONRPC('{"jsonrpc": "2.0","id": 1, "method": "Playlist.Clear", "params": {"playlistid": 1}}')
					add_this_ep['params']['item']['episodeid'] = int(pre_epid)
					json_query(add_this_ep, False)
					xbmc.sleep(50)
					xbmc.Player().play(xbmc.PlayList(1))
				elif paused:
					xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":true},"id":1}')
			
			main_instance.nextprompt_info = {}
		log('Playbackended_End')


class LazyMonitor(xbmc.Monitor):
	def onSettingsChanged(self):
		grab_settings()

	def onNotification(self, sender, method, data):
		if method == 'VideoLibrary.OnUpdate':
			try:
				ndata = json.loads(data)
				item = ndata.get('item', {})
				if item.get('type') == 'episode' and ndata.get('playcount') == 1:
					log('manual change to watched status, data = ' + str(ndata))
					ep_to_show_query['params']['episodeid'] = item['id']
					details = json_query(ep_to_show_query, True)
					if details and 'episodedetails' in details:
						tmp_showid = details['episodedetails']['tvshowid']
						playing_epid = item['id']
						
						odlist_str = WINDOW.getProperty(f"LazyTV.{tmp_showid}.odlist")
						offlist_str = WINDOW.getProperty(f"LazyTV.{tmp_showid}.offlist")
						odlist = ast.literal_eval(odlist_str) if odlist_str else []
						offlist = ast.literal_eval(offlist_str) if offlist_str else []
						
						proceed = False
						if tmp_showid in randos and (playing_epid in odlist or playing_epid in offlist):
							proceed = True
						elif playing_epid in odlist:
							proceed = True

						if proceed:
							main_instance.monitor_override = True
							main_instance.player.playing_showid = tmp_showid
							main_instance.player.playing_epid = playing_epid
							log(f'monitor supplied showid - {main_instance.player.playing_showid}')
							log(f'monitor supplied epid - {main_instance.player.playing_epid}')
						else:
							main_instance.player.playing_epid = False
			except Exception as e:
				log(f"Error in onNotification: {e}")


class Main:
	def __init__(self, *args, **kwargs):
		log('monitor instantiated', reset=True)
		self.count = 0
		self.onLibUpdate = False
		self.monitor_override = False
		self.nepl = []
		self.eject = False
		self.randy_flag = False
		self.target = False
		self.nextprompt_info = {}
		self.player = LazyPlayer()
		self.monitor = LazyMonitor()
		self.sp_next = None
		self.initialisation()
		log('daemon started')
		self._daemon()

	def initialisation(self):
		log('variable_init_started')
		self.retrieve_all_show_ids()
		WINDOW.setProperty(f"{__addonid__}.playlist_running", 'null')
		self.get_eps(showids=self.all_shows_list)
		log('variable_init_End')

	def _daemon(self):
		WINDOW.setProperty('LazyTV_service_running', 'true')
		if startup:
			xbmc.executebuiltin(f'Notification({__addonid__},{lang(32173)},5000)')
		while not self.monitor.abortRequested():
			self._daemon_check()
			xbmc.sleep(100)

	def _daemon_check(self):
		_breathe()

		if self.onLibUpdate:
			self.onLibUpdate = False
			self.retrieve_all_show_ids()
			self.get_eps(showids=self.all_shows_list)

		if WINDOW.getProperty("LazyTV.rando_shuffle") == 'true':
			WINDOW.setProperty("LazyTV.rando_shuffle", 'false')
			log('shuffling randos')
			self.reshuffle_randos()

		if self.player.playing_showid and self.player.playing_showid in self.nepl:
			self.process_played_episode(self.player.playing_showid, self.player.playing_epid)
			self.player.playing_showid = False
			self.player.playing_epid = False

		if self.target:
			self.count = (self.count + 1) % 50
			if self.count == 0 and runtime_converter(xbmc.getInfoLabel('VideoPlayer.Time')) > self.target:
				log('Main.target exceeded')
				if self.eject:
					self.remove_from_nepl(self.sp_next)
					self.eject = False
				if self.sp_next:
					self.swap_over(self.sp_next)
				if nextprompt and self.nextprompt_info:
					self.player.nextprompt_trigger = True
				self.sp_next = None
				self.target = False

	def process_played_episode(self, showid, epid):
		log(f'Processing played episode: showid={showid}, epid={epid}')
		self.sp_next = showid
		retod = WINDOW.getProperty(f"LazyTV.{showid}.odlist")
		retoff = WINDOW.getProperty(f"LazyTV.{showid}.offlist")
		ond = ast.literal_eval(retod) if retod else []
		offd = ast.literal_eval(retoff) if retoff else []
		
		tmp_wep = int((WINDOW.getProperty(f"LazyTV.{showid}.CountWatchedEps") or '0').replace("''", '0')) + 1
		tmp_uwep = max(0, int((WINDOW.getProperty(f"LazyTV.{showid}.CountUnwatchedEps") or '0').replace("''", '0')) - 1)

		np_next = None

		if showid in randos:
			npodlist = ond + offd
			if epid in npodlist:
				if epid in ond: ond.remove(epid)
				else: offd.remove(epid)
				npodlist = ond + offd
				if npodlist:
					random.shuffle(npodlist)
					np_next = npodlist[0]
					self.randy_flag = True
					self.store_next_ep(np_next, 'temp', ond, offd, tmp_uwep, tmp_wep)
		elif epid in ond:
			cp = ond.index(epid)
			if cp < len(ond) - 1:
				np_next = ond[cp + 1]
				newod = ond[cp + 1:]
				self.store_next_ep(np_next, 'temp', newod, offd, tmp_uwep, tmp_wep)
			else:
				self.eject = True
		
		if self.monitor_override:
			self.swap_over(showid)
			self.monitor_override = False
			np_next = None

		if np_next:
			log(f'next ep to load = {np_next}')
			if nextprompt and not self.eject and not self.randy_flag:
				prompt_query['params']['episodeid'] = int(np_next)
				cp_details = json_query(prompt_query, True)
				if 'episodedetails' in cp_details:
					self.nextprompt_info = cp_details['episodedetails']
		
		tick, duration = 0, ""
		while not duration and tick < 20:
			duration = xbmc.getInfoLabel('VideoPlayer.Duration')
			if not duration:
				tick += 1
				xbmc.sleep(250)
		if duration:
			self.target = runtime_converter(duration) * 0.9
		log(f'target: {self.target}')

	def remove_from_nepl(self, showid):
		log(f'removing {showid} from nepl')
		if showid in self.nepl:
			self.nepl.remove(showid)
			WINDOW.setProperty("LazyTV.nepl", str(self.nepl))
		self.update_smartplaylist(showid, remove=True)

	def add_to_nepl(self, showid):
		log(f'adding {showid} to nepl')
		if showid not in self.nepl:
			self.nepl.append(showid)
			WINDOW.setProperty("LazyTV.nepl", str(self.nepl))

	def reshuffle_randos(self, sup_rand=None):
		log('shuffle started')
		shuf_rand = sup_rand if sup_rand is not None else randos
		log(f'shuffle list = {shuf_rand}')
		for rando in shuf_rand:
			tmp_od = ast.literal_eval(WINDOW.getProperty(f"LazyTV.{rando}.odlist") or '[]')
			tmp_off = ast.literal_eval(WINDOW.getProperty(f"LazyTV.{rando}.offlist") or '[]')
			
			if not WINDOW.getProperty(f"LazyTV.{rando}.EpisodeID"): continue
			
			tmp_wep = WINDOW.getProperty(f"LazyTV.{rando}.CountWatchedEps").replace("''", '0')
			tmp_uwep = WINDOW.getProperty(f"LazyTV.{rando}.CountUnwatchedEps").replace("''", '0')
			tmp_cmb = tmp_od + tmp_off
			if not tmp_cmb: continue

			random.shuffle(tmp_cmb)
			self.store_next_ep(tmp_cmb[0], rando, tmp_od, tmp_off, tmp_wep, tmp_uwep)
		log('shuffle ended')

	def retrieve_all_show_ids(self):
		log('retrieve_all_shows_started')
		self.result = json_query(show_request, True)
		self.all_shows_list = [id['tvshowid'] for id in self.result.get('tvshows', [])]
		log('retrieve_all_shows_End')

	def get_eps(self, showids=None):
		log('get_eps_started', reset=True)
		self.showids = showids if showids is not None else []
		self.lshowsR = json_query(show_request_lw, True)
		self.show_lw = [x['tvshowid'] for x in self.lshowsR.get('tvshows', []) if x['tvshowid'] in self.showids]

		for my_showid in self.show_lw:
			_breathe()
			eps_query['params']['tvshowid'] = my_showid
			self.ep = json_query(eps_query, True)
			if 'episodes' not in self.ep: continue
			
			self.eps = self.ep['episodes']
			all_unplayed = []
			Season, Episode, watched_showcount = 1, 0, 0

			for ep in self.eps:
				if ep['playcount'] != 0:
					watched_showcount += 1
					if (ep['season'] > Season) or (ep['season'] == Season and ep['episode'] > Episode):
						Season, Episode = ep['season'], ep['episode']
				else:
					all_unplayed.append(ep)
			
			files = set()
			unique_unplayed = [ep for ep in all_unplayed if ep['file'] not in files and not files.add(ep['file'])]
			
			unordered_ondeck_eps = [x for x in unique_unplayed if x['season'] > Season or (x['season'] == Season and x['episode'] > Episode)]
			offdeck_eps = [x for x in unique_unplayed if x not in unordered_ondeck_eps]
			
			ondeck_eps = sorted(unordered_ondeck_eps, key=lambda k: (k['season'], k['episode']))
			
			if not ondeck_eps and not offdeck_eps:
				if my_showid in self.nepl: self.remove_from_nepl(my_showid)
				continue

			comb_deck = ondeck_eps + offdeck_eps
			if not comb_deck: continue
			
			on_deck_epid = ondeck_eps[0]['episodeid'] if (ondeck_eps and my_showid not in randos) else random.choice(comb_deck)['episodeid']

			self.store_next_ep(on_deck_epid, my_showid, [e['episodeid'] for e in ondeck_eps], [e['episodeid'] for e in offdeck_eps], len(unique_unplayed), watched_showcount)

			if not ondeck_eps and my_showid not in randos: continue
			if my_showid not in self.nepl: self.nepl.append(my_showid)

		WINDOW.setProperty("LazyTV.nepl", str(self.nepl))
		log('get_eps_Ended')

	def store_next_ep(self, episodeid, tvshowid, ondecklist, offdecklist, uwep=0, wep=0):
		if self.monitor.abortRequested(): return
		_breathe()
		ep_details_query['params']['episodeid'] = episodeid
		ep_details = json_query(ep_details_query, True)

		if 'episodedetails' in ep_details:
			details = ep_details['episodedetails']
			resume_pos = details.get('resume', {}).get('position', 0)
			resume_total = details.get('resume', {}).get('total', 0)
			
			props = {
				'Title': details['title'], 'Episode': f"{details['episode']:02d}",
				'EpisodeNo': f"s{details['season']:02d}e{details['episode']:02d}",
				'Season': f"{details['season']:02d}", 'TVshowTitle': details['showtitle'],
				'Art(thumb)': details.get('art', {}).get('thumb', ''),
				'Art(tvshow.poster)': details.get('art', {}).get('tvshow.poster', ''),
				'Resume': "true" if resume_pos > 0 else "false",
				'PercentPlayed': f"{int(resume_pos / resume_total * 100)}%" if resume_total > 0 else "0%",
				'CountWatchedEps': str(wep), 'CountUnwatchedEps': str(uwep),
				'CountonDeckEps': str(len(ondecklist)), 'EpisodeID': str(episodeid),
				'odlist': str(ondecklist), 'offlist': str(offdecklist),
				'File': details['file'], 'Art(tvshow.fanart)': details.get('art', {}).get('tvshow.fanart', ''),
				'Premiered': details['firstaired'], 'Plot': details['plot']
			}
			for key, value in props.items():
				WINDOW.setProperty(f"LazyTV.{tvshowid}.{key}", str(value))
			if tvshowid != 'temp':
				self.update_smartplaylist(tvshowid)

	def swap_over(self, TVShowID_):
		log(f'swapover_started for {TVShowID_}')
		props_to_swap = [
			'Title', 'Episode', 'EpisodeNo', 'Season', 'TVshowTitle', 'Art(thumb)',
			'Art(tvshow.poster)', 'Resume', 'PercentPlayed', 'CountWatchedEps',
			'CountUnwatchedEps', 'CountonDeckEps', 'EpisodeID', 'odlist', 'offlist',
			'File', 'Art(tvshow.fanart)', 'Premiered', 'Plot'
		]
		for prop in props_to_swap:
			temp_val = WINDOW.getProperty(f"LazyTV.temp.{prop}")
			WINDOW.setProperty(f"LazyTV.{TVShowID_}.{prop}", temp_val)
		
		self.update_smartplaylist(TVShowID_)
		log('swapover_End')

	def update_smartplaylist(self, tvshowid, remove=False):
		if maintainsmartplaylist and tvshowid != 'temp':
			playlist_file = os.path.join(videoplaylistlocation, 'LazyTV.xsp')
			showname = WINDOW.getProperty(f"LazyTV.{tvshowid}.TVshowTitle")
			filename = os.path.basename(WINDOW.getProperty(f"LazyTV.{tvshowid}.File"))

			if showname and filename:
				content = []
				try:
					with open(playlist_file, 'r', encoding='utf-8') as f:
						content = f.readlines()
				except FileNotFoundError:
					pass

				line1 = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n<smartplaylist type="episodes">\n<name>LazyTV</name>\n<match>one</match>\n'
				linex = '</smartplaylist>\n'
				rawshowline = f'<!--{showname}--><rule field="filename" operator="is"><value>{filename}</value></rule><!--END-->\n'

				# Filter out existing rule for this show
				new_content = [line for line in content if f'<!--{showname}-->' not in line]
				
				# Remove playlist tags if they exist
				new_content = [line for line in new_content if not line.strip().startswith('<?xml') and not line.strip().startswith('<smartplaylist') and not line.strip().startswith('</smartplaylist>')]


				if not remove:
					new_content.append(rawshowline)

				with open(playlist_file, 'w', encoding='utf-8') as g:
					g.write(line1)
					g.writelines(new_content)
					g.write(linex)

def grab_settings(firstrun=False):
	global playlist_notifications, resume_partials, keep_logs, nextprompt, promptduration, randos, prevcheck, maintainsmartplaylist, promptdefaultaction, startup, nextprompt_or
	
	old_randos = randos
	
	playlist_notifications = __setting__("notify") == 'true'
	resume_partials = __setting__('resume_partials') == 'true'
	keep_logs = __setting__('logging') == 'true'
	nextprompt = __setting__('nextprompt') == 'true'
	nextprompt_or = __setting__('nextprompt_or') == 'true'
	startup = __setting__('startup') == 'true'
	promptduration = int(float(__setting__('promptduration')))
	prevcheck = __setting__('prevcheck') == 'true'
	promptdefaultaction = int(float(__setting__('promptdefaultaction')))
	if promptduration == 0: promptduration = 0.001

	new_maintain_setting = __setting__('maintainsmartplaylist') == 'true'
	if new_maintain_setting and not maintainsmartplaylist and not firstrun:
		for neep in main_instance.nepl: main_instance.update_smartplaylist(neep)
	maintainsmartplaylist = new_maintain_setting
	
	try:
		randos = ast.literal_eval(__setting__('randos') or '[]')
	except: randos = []

	if old_randos != randos and not firstrun:
		added = [r for r in randos if r not in old_randos]
		removed = [r for r in old_randos if r not in randos]
		for r in added: main_instance.add_to_nepl(r); main_instance.reshuffle_randos(sup_rand=[r])
		for oar in removed:
			has_ond_str = WINDOW.getProperty(f"LazyTV.{oar}.odlist")
			if has_ond_str and ast.literal_eval(has_ond_str):
				ond = ast.literal_eval(has_ond_str)
				offd_str = WINDOW.getProperty(f"LazyTV.{oar}.offlist")
				offd = ast.literal_eval(offd_str or '[]')
				wep = int(WINDOW.getProperty(f"LazyTV.{oar}.CountWatchedEps").replace("''",'0') or 0)
				uwep = int(WINDOW.getProperty(f"LazyTV.{oar}.CountUnwatchedEps").replace("''",'0') or 0)
				main_instance.store_next_ep(ond[0], oar, ond, offd, uwep, wep)
			else: main_instance.remove_from_nepl(oar)

	WINDOW.setProperty("LazyTV.randos", str(randos))
	log(f'randos = {randos}')
	log('settings grabbed')

randos = []
main_instance = None
if (__name__ == "__main__"):
	xbmc.sleep(1000)
	log(f' {__addonversion__} started')
	grab_settings(firstrun=True)
	main_instance = Main()
	del main_instance
	log(f' {__addonversion__} stopped')