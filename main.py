import configparser
import time

import pylast
import os
import sys
import urllib.request
from pathlib import Path
import logging
from PIL import Image, ImageDraw, ImageFont

# LastFM4OBS

# to build as exe C:\Users\lollb\AppData\Local\Programs\Python\Python37\python.exe -m PyInstaller -y -F --add-data
# "C:\Users\lollb\PycharmProjects\LBLastFmToOBS\venv\Lib\site-packages\PIL\;PIL" --add-data
# "assets\unknownalbumplaceholder.png;assets" --add-data "assets\api.ini;assets" --hidden-import numbers .\main.py

EXEC_PATH = Path(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(filename=EXEC_PATH / "log.log", filemode='w')

# You have to have your own unique two values for API_KEY and API_SECRET
# Obtain yours from https://www.last.fm/api/account/create for Last.fm
API_KEY = "SOME API KEY"
API_SECRET = "SOME API SECRET"
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
MISSING_ALBUM_TEXT = "?"
ALBUM_PLACEHOLDER_PATH = EXEC_PATH / "assets" / "unknownalbumplaceholder.png"
ALBUM_ART_NAME = "image.png"


def write_blank_image(dims, album=None):
    img = Image.new('RGB', dims, (0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(10, 10), (dims[0] - 10, dims[1] - 10)], fill="white", width=img.width)
    if album is not None:
        font, fontsize = scale_font(img, MISSING_ALBUM_TEXT, "arial.ttf", img_width=dims[0] - 20, scale=0.6)
        x = (fontsize[0] / 2) - 10
        y = 0
        draw.text((x, y), MISSING_ALBUM_TEXT, font=font, align="center", fill=(0, 0, 0))  # put the text on the image
        # Print out the album name (make configurable)
    # font = scale_font(img, album, "arial.ttf", img_width=dims[0] - 20)
    # draw.text((10, 70), album, font=font, align="center")  # put the text on the image

    return img


def scale_font(image, text, font_name, scale=0.8, img_width=None):
    # Following code adapted from https://stackoverflow.com/questions/4902198/pil-how-to-scale-text-size-in
    # -relation-to-the-size-of-the-image
    fontsize = 1
    # portion of image width you want text width to be
    img_fraction = scale
    if img_width is None:
        img_width = image.size[0]

    font = ImageFont.truetype(font_name, fontsize)
    while font.getsize(text)[0] < img_fraction * img_width:
        # iterate until the text size is just larger than the criteria
        fontsize += 1
        font = ImageFont.truetype(font_name, fontsize)
    return font, font.getsize(text)


def format_info(source, target, content):
    assert (source.__contains__(target))
    source = source.replace(target, content)
    return source


def format_all_info(track=None, artist=None, album=None):
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


def get_album_name(track):
    # Get album information
    album = track.get_album()
    # If the album doesn't exist, use the track name for the album (e.g. a single)
    if album is None:
        return track.title, False
    else:
        return album.get_name(), True


def check_same_album(a, b):
    if a is None or b is None:
        return False
    return get_album_name(a) is get_album_name(b) and a.artist.title is b.artist.title


if __name__ == "__main__":
    # parse config file
    config = configparser.ConfigParser()
    try:
        config.read(EXEC_PATH / 'assets' / 'api.ini', encoding='utf-8')
        API_KEY = config['last.fm']['api-key']
        API_SECRET = config['last.fm']['api-secret']
        print("Reading config")
        config.read('config.ini', encoding='utf-8')
        user = config['last.fm']['username']
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
    img_dims = (300, 300)
    previous_track = None
    ALBUM_PLACEHOLDER = Image.open(ALBUM_PLACEHOLDER_PATH)
    while alive:
        try:
            new_track = user.get_now_playing()

            if new_track is None:
                time.sleep(15)
                print("No track playing")
                continue
                # Do nothing on none

            # A new, different track
            if new_track != playing_track:
                # Remember previous track
                previous_track = playing_track
                # Assign the new track
                playing_track = new_track
                # Get the track name
                track_name = playing_track.title
                # Get the artist name
                artist_name = playing_track.artist.name

                # get the album name
                album_name = get_album_name(playing_track)

                cover_image_url = None

                try:
                    # Get the cover image (if it has one)
                    cover_image_url = playing_track.get_cover_image()
                    urllib.request.urlretrieve(cover_image_url, SAVING_DIR / ALBUM_ART_NAME)
                    img = Image.open(SAVING_DIR / ALBUM_ART_NAME)
                    img_dims = img.size
                except Exception as ie:
                    # see if its the same album as last time
                    if not check_same_album(playing_track, previous_track):
                        ALBUM_PLACEHOLDER.save(SAVING_DIR / ALBUM_ART_NAME)
                       # write_blank_image(img_dims, album_name).save(SAVING_DIR / "image.png", "PNG")

                # Write out the textual information to the formatter
                track_out = format_all_info(track=track_name, artist=artist_name,
                                            album=album_name)
                # Print to console
                to_console = "Found track \"" + str(track_name) + "\" by \"" + str(artist_name) + "\" from the album \"" \
                             + str(album_name[0]) + "\""
                if album_name[1] is False:
                    to_console = to_console + " (Album is unknown)"
                print(to_console)

                # Write information to file
                track_file = open(text_file, 'w', encoding='utf-8')
                track_file.write(track_out)
                track_file.close()

        except Exception as e:
            print("Error occurred while writing out information: %s" % repr(e))
            logging.error("Error occurred while writing out information", exc_info=True)

        time.sleep(15)
input()
