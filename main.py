import configparser
import time

import pylast
import os
import urllib.request
from pathlib import Path
import logging
from PIL import Image, ImageDraw

#LastFM4OBS

# to build as exe
# python -m PyInstaller -y -F --add-data ".\venv\Lib\site-packages\PIL\;PIL" --hidden-import numbers .\main.py

EXEC_PATH = Path(os.path.dirname(os.path.realpath(__file__)))
logging.basicConfig(filename=EXEC_PATH / "log.log", filemode='w')

# You have to have your own unique two values for API_KEY and API_SECRET
# Obtain yours from https://www.last.fm/api/account/create for Last.fm
API_KEY = "f6b159747f2b5d5ff48c3045cf05fa5c"
API_SECRET = "f64f158a571927b9197368617ca9ac54"
SESSION_KEY_FILE = os.path.join(os.path.expanduser("~"), ".session_key")

SAVING_DIR = None
network = None
user = None

error_count = 0
MAX_ERROR_COUNT = 10

# format options
FORMAT_TRACK = str("%TRACK")
FORMAT_ARTIST = str("%ARTIST")
FORMAT_ALBUM = str("%ALBUM")

DEFAULT_FORMAT = str("Track:" + FORMAT_TRACK + "\nArtist:" + FORMAT_ARTIST)
FORMAT = DEFAULT_FORMAT


def write_blank_image(album=None):
    img = Image.new('RGB', (600, 600), (69, 69, 69))
    if album is not None:
        d = ImageDraw.Draw(img)
        d.text((10, 10), album, fill=(0, 0, 0))
    return img


def format_info(source, target, content):
    assert (source.__contains__(target))
    source = source.replace(target, content)
    return source


def format_all_info(track=None, artist=None, album=None, year=None):
    string_format = str(FORMAT)
    string_format = string_format.replace("\\n", "\n")
    string_format = string_format.replace("\\t", "\t")

    try:
        string_format = format_info(string_format, FORMAT_TRACK, track)
    except AssertionError:
        logging.error("Track name was not supplied when required", exc_info=True)

    try:
        string_format = format_info(string_format, FORMAT_ARTIST, artist)
    except AssertionError:
        logging.error("Artist name was not supplied when required", exc_info=True)

    try:
        string_format = format_info(string_format, FORMAT_ALBUM, album)
    except AssertionError:
        logging.error("Album name was not supplied when required", exc_info=True)

    return string_format


if __name__ == "__main__":
    # parse config file
    config = configparser.ConfigParser()
    try:
        print("Reading config")
        config.read('config.ini')
        user = config['last.fm']['username']
        API_KEY = config['last.fm']['api-key']
        API_SECRET = config['last.fm']['api-secret']
        SAVING_DIR = Path(config['LOCAL']['directory'])
        FORMAT = config['LOCAL']['format']
        print("Using format: " + str(FORMAT))

        network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET)
    except Exception as e:
        logging.error("Error occurred and logged", exc_info=True)

    if not os.path.exists(SESSION_KEY_FILE):
        skg = pylast.SessionKeyGenerator(network)
        url = skg.get_web_auth_url()

        print(f"Please authorize the scrobbler to scrobble to your account: {url}\n")
        import webbrowser

        webbrowser.open(url)

        while True:
            try:
                session_key = skg.get_web_auth_session_key(url)
                fp = open(SESSION_KEY_FILE, "w")
                fp.write(session_key)
                fp.close()
                break
            except pylast.WSError:
                time.sleep(1)
    else:
        session_key = open(SESSION_KEY_FILE).read()

    network.session_key = session_key
    user = network.get_user(user)
    user_announce = "Tuned in to %s" % user

    playing_track = None
    text_file = SAVING_DIR / "track.txt"
    alive = True
    while alive:

        try:
            new_track = user.get_now_playing()

            if new_track is None:
                time.sleep(15)
                continue
                # Do nothing on none

            # A new, different track
            if new_track != playing_track:
                playing_track = new_track
                track = playing_track.title
                artist = playing_track.artist.name
                album = playing_track.get_album()
                album_name = album.title
                cover_image_url = playing_track.get_cover_image()

                if cover_image_url is not None:
                    urllib.request.urlretrieve(cover_image_url, SAVING_DIR / "image.png")
                else:
                    write_blank_image(album_name).save(SAVING_DIR / "image.png", "PNG")

                debug_out = "Track:{0}\nArtist:{1}".format(playing_track.title, playing_track.artist)
                track_out = format_all_info(track=track, artist=artist,
                                            album=album_name)
                print(track_out)
                track_file = open(text_file, 'w', encoding='utf-8')
                track_file.write(track_out)
                track_file.close()

        except Exception as e:
            print("Error occurred: %s" % repr(e))
            logging.error("Error occurred while writing out information", exc_info=True)
            error_count = error_count + 1
            if error_count > MAX_ERROR_COUNT:
                alive = False

        time.sleep(15)
    print("Exiting due to too many errors")
input()
