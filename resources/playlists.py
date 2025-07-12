import xbmc
import json
import xbmcaddon
import xbmcgui

__addon__              = xbmcaddon.Addon('script.lazytv')
__addonid__          = __addon__.getAddonInfo('id')

def lang(id):
    return __addon__.getLocalizedString(id)

plf            = {"jsonrpc": "2.0","id": 1, "method": "Files.GetDirectory",         "params": {"directory": "special://profile/playlists/video/", "media": "video"}}


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

def playlist_selection_window():
    ''' Purpose: launch Select Window populated with smart playlists '''

    playlist_files = json_query(plf, True).get('files', [])

    if playlist_files:

        plist_files   = dict((x['label'],x['file']) for x in playlist_files)

        playlist_list = list(plist_files.keys())
        playlist_list.sort()

        inputchoice = xbmcgui.Dialog().select(lang(32104), playlist_list)
        
        if inputchoice > -1:
            return plist_files[playlist_list[inputchoice]]
        else:
            return 'empty'
    else:
        return 'empty'



pl = playlist_selection_window()

__addon__.setSetting(id="users_spl",value=str(pl))

__addon__.openSettings()