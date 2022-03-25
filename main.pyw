from ctypes.wintypes import VARIANT_BOOL
from multiprocessing.spawn import old_main_modules
import os
from unicodedata import decimal
current_path = os.path.dirname(os.path.abspath(__file__))
import time
import requests
import os.path
import random
import sys
try:
    from dotenv import load_dotenv
    import phue
    from phue import Bridge
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    import urllib.request
    import colorgram
    import numpy as np
    from pystray import MenuItem as item
    import pystray
    from PIL import Image
except:
    os.system('pip install -r '+current_path+r'/requirements.txt')
    from dotenv import load_dotenv
    import phue
    from phue import Bridge
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    import urllib.request
    import colorgram
    import numpy as np
    from pystray import MenuItem as item
    import pystray
    from PIL import Image

def get_hue_bridge_ip():
    IP_URL = 'https://discovery.meethue.com/'
    res = requests.get(IP_URL)
    ip_data = res.json()[0]
    ID = ip_data['id']
    INTERNALIP = ip_data['internalipaddress']
    return INTERNALIP

def hue_get_group_from_room(hue_room, HUE_GROUPS):
    for group_num in HUE_GROUPS:
            if HUE_GROUPS[group_num]['name'].lower() == hue_room.lower():
                return group_num

def convertColor(hexCode):
    R = int(hexCode[:2],16)
    G = int(hexCode[2:4],16)
    B = int(hexCode[4:6],16)
    total = R + G + B
    if R == 0:
        firstPos = 0
    else:
        firstPos = R / total
    if G == 0:
        secondPos = 0
    else:
        secondPos = G / total
    return [firstPos, secondPos]

def getRandomHex():
    return "%06x" % random.randint(0, 0xFFFFFF)

def extract_colors(url, n=4):
    urllib.request.urlretrieve(url, current_path+r"/cover.jpg")
    img = current_path+r"/cover.jpg"
    return colorgram.extract(img, n)
    
def rgb_to_xy(R, G, B):
    total = R + G + B
    if R == 0:
        firstPos = 0
    else:
        firstPos = R / total
    if G == 0:
        secondPos = 0
    else:
        secondPos = G / total
    return [firstPos, secondPos]

def exit_everything():
    os._exit(1)

if __name__ == '__main__':
    # Check if env file exsists
    if os.path.isfile(current_path+r'/.env') == False:
        # If not create it and add content
        with open(current_path+r'/.env', 'w') as f:
            var_lines = ["SPOTIPY_CLIENT_ID = ", "SPOTIPY_CLIENT_SECRET = ", "SPOTIPY_USER_NAME = ", "SPOTIPY_REDIRECT_URI = ", "HUE_ROOM = "]
            for var_line in var_lines:
                f.write(var_line+'\n')
        print('Please fill out the variables in the .env file ( '+current_path+r'/.env )')
        exit()
    else:
        # Load vars
        load_dotenv()
        hue_room = str(os.getenv('HUE_ROOM'))

        # Connect to Bridge
        try:
            bridge = Bridge(get_hue_bridge_ip())
        except phue.PhueRegistrationException:
            print('Could not link with the Philips Hue Bridge. Maybe the Bridge is offline or the pairbutton hasnt been pressed. Do this and restart the script within 30 seconds.')
            exit()
        bridge.connect()
        HUE_GROUPS = bridge.get_group()

        if hue_room is None:
            HUE_GROUPS = 1
        else:
            hue_group = int(hue_get_group_from_room(hue_room, HUE_GROUPS))
        
        hue_lights = [int(x) for x in bridge.get_group(hue_group)['lights']]

        # Spotify Auth
        sp_scopes = 'user-read-currently-playing user-read-playback-state streaming user-read-email user-read-private user-read-currently-playing user-read-playback-position user-read-playback-state'
        global sp
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=sp_scopes))
        one_device_is_active = False
        for x in sp.devices()['devices']:
            if x['is_active'] == True:
                try:
                    sp.start_playback(x['id'])
                except:
                    pass
                one_device_is_active = True
                break
        if one_device_is_active == False:
            sp.start_playback(sp.devices()['devices'][0]['id'])
            sp.next_track(sp.devices()['devices'][0]['id'])

        current_track_uri = (sp.current_playback().get("item")).get("uri")
        current_track_progress = (sp.current_playback().get("progress_ms"))/1000
        current_track_playing_status = sp.current_playback().get("is_playing")
        current_track_duration = (sp.current_playback().get("item")).get("duration_ms")/100            
        raw_current_audio_features = sp.audio_analysis(current_track_uri)
        current_audio_features_segments = raw_current_audio_features.get("segments")
        current_audio_features_segments_array = np.array(current_audio_features_segments)
        numb_segments = len(current_audio_features_segments_array)
        current_segment = 0
        current_segment_time = 0
        prev_track_progress = 0
        min_loudness_segment = 0
        min_loudness = 0
        max_loudness = 0
        count = 0

        old_colors = extract_colors(sp.current_playback()['item']['album']['images'][0]['url'])
        old_cover_url = sp.current_playback()['item']['album']['images'][0]['url']
        bridge.set_light(hue_lights, 'on', True)
        global synced
        synced = True

        def start_sync():
            bridge.set_light(hue_lights, 'on', True)
            global synced
            synced=True

        def pause_sync():
            global synced
            synced=False

        def compare_old_with_new_track():
            if sp.current_playback()['item']['uri'] != current_track_uri:
                return True
            else:
                return False

        tray_icon = Image.open(current_path+r'/icon.ico')
        tray_menu = (item('Start synchronisation', start_sync), item('Pause synchronisation', pause_sync), item('Exit', exit_everything))
        icon = pystray.Icon('Huefy Sync', tray_icon, 'Huefy Sync', tray_menu)
        icon.run_detached()

        while True:
            if synced == True:
                if sp.current_playback()['is_playing'] is True:
                    if count < numb_segments:
                        if((current_audio_features_segments_array[count]["loudness_max"]) < min_loudness):
                            min_loudness_segment = count
                            min_loudness = current_audio_features_segments_array[count]["loudness_max"]
                        count = count + 1
                    max_loudness_positive = max_loudness - min_loudness
                    if (current_segment < numb_segments):
                        current_loudness = current_audio_features_segments_array[current_segment]["loudness_max"]
                        current_loudness_time = current_audio_features_segments_array[current_segment]["loudness_max_time"]
                        current_confidence = current_audio_features_segments_array[current_segment]["confidence"]
                        current_loudness_positive = current_loudness - min_loudness
                        bar_percentage = ((current_loudness_positive/max_loudness_positive) * 100)* current_confidence
                        current_segment = current_segment + 1
                        if (current_segment < numb_segments):
                            current_segment_time = current_audio_features_segments_array[current_segment]["start"]
                    current_id = sp.current_playback()['item']['id']
                    if compare_old_with_new_track() == True:
                        colors = extract_colors(sp.current_playback()['item']['album']['images'][0]['url'])
                    else:
                        colors = old_colors
                    for light_id, color in zip(hue_lights, colors):
                        bridge.set_light(light_id, 'xy', rgb_to_xy(color.rgb.r, color.rgb.g, color.rgb.b))

                    bar_percentage = round(bar_percentage, 0)
                    bridge.set_light(hue_lights, 'bri', int(bar_percentage) + 30, 0)
                    old_cover_url = sp.current_playback()['item']['album']['images'][0]['url']
                    old_colors = colors
                else:
                    bridge.set_light(hue_lights, 'bri', 254)
                    for x in hue_lights:
                        bridge.set_light(x,'xy',convertColor(getRandomHex()))