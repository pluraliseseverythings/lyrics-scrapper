"""It uses a pager to find the X best selling songs for a certain year and then it tries to
find the lyrics for these songs cleaning up the text a bit"""
import argparse
import logging
import os
import sys
import urllib2
import re
import time
import spotipy
from HTMLParser import HTMLParser

logger = logging.getLogger(__name__)

logging.basicConfig(stream=sys.stdout,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    level=logging.DEBUG,
                    datefmt='%I:%M:%S')


class UKChartHTMLParser(HTMLParser):
  def __init__(self):
    HTMLParser.__init__(self)
    self.grab_songs = False
    self.artist = False
    self.song = False
    self.current_song = ""
    self.current_artist = ""
    self.songs = []

  def handle_starttag(self, tag, _):
    if tag == "tbody":
      self.grab_songs = True

  def handle_endtag(self, tag):
    if tag == "tbody":
      self.grab_songs = False
    elif tag == "td" and self.grab_songs and not self.artist and not self.song:
      self.artist = True
    elif tag == "td" and self.artist:
      self.artist = False
      self.song = True
    elif tag == "td" and self.song:
      self.song = False
      if self.current_artist and self.current_song:
        self.songs.append((self.current_artist, self.current_song))

  def handle_data(self, data):
    if self.artist:
      self.current_artist = data
    if self.song:
      self.current_song = data


class AZLyricsHTMLParser(HTMLParser):
  def __init__(self):
    HTMLParser.__init__(self)
    self.started_lyrics = False
    self.grab_lyrics = False
    self.depth = -1
    self.lyrics_depth = 0
    self.lyrics = ""

  def handle_starttag(self, tag, attrs):
    if tag != "br":
      self.depth += 1
    for (k_value, attr_value) in attrs:
      if attr_value == "lyricsh":
        self.started_lyrics = True
    if self.started_lyrics and tag == "div" and len(attrs) == 0:
      self.lyrics_depth = self.depth
      self.grab_lyrics = True

  def handle_endtag(self, tag):
    if tag != "br":
      self.depth -= 1
    if self.grab_lyrics and self.depth < self.lyrics_depth:
      self.grab_lyrics = False
      self.lyrics = self.lyrics.strip()

  def handle_data(self, data):
    if self.grab_lyrics:
      self.lyrics += data


class SongListGrabSpotify():
  def get_songs_from_year(self, year, lyrics_grabber, num_songs=400):
    start = 0
    limit = 50
    song_read = 0
    client = spotipy.Spotify()
    while song_read < num_songs:
      res = client.search("year:{}".format(year), limit=limit, offset=start)
      tracks = res["tracks"]["items"]
      logger.info("Found %d songs for year %s", len(tracks), year)
      tracks_and_artist = [(a["name"], a["artists"][0]["name"]) for a in tracks]
      all_lyrics = ""
      for (song, artist) in tracks_and_artist:
        lyrics = lyrics_grabber.grab_lyrics_from_az(artist, song)
        if lyrics:
          all_lyrics += lyrics
          all_lyrics += "\n\n"
          song_read += 1
        time.sleep(3)
      start += limit
    return all_lyrics


class SongListGrabUkChart():
  UKCHARTURL = "http://www.uk-charts.top-source.info/top-100-{}.shtml"

  def get_songs_from_year(self, year, lyrics_grabber):
    ukcharturl_format = SongListGrabUkChart.UKCHARTURL.format(year)
    logger.info("Fetching songs from %s", ukcharturl_format)
    request = urllib2.Request(ukcharturl_format)
    opener = urllib2.build_opener()
    request.add_header('User-Agent', 'Googlebot/2.1 (http://www.googlebot.com/bot.html)')
    raw_response = opener.open(request).read().decode('utf-8')
    uk_chart_parser = UKChartHTMLParser()
    uk_chart_parser.feed(raw_response)
    songs = uk_chart_parser.songs
    all_lyrics = ""
    logger.info("Found %d songs", len(songs))
    for (artist, song) in songs:
      lyrics = lyrics_grabber.grab_lyrics_from_az(artist, song)
      if lyrics:
        all_lyrics += lyrics
        all_lyrics += "\n\n"
      time.sleep(5)
    return all_lyrics


class AZLyricsGrab():
  AZURL = "http://www.azlyrics.com/lyrics/{}/{}.html"

  def grab_lyrics_from_az(self, az_artist, az_song):
    azurl = AZLyricsGrab.AZURL.format(self.azfy(az_artist), self.azfy(az_song))
    try:
      logger.debug("Fetching {}".format(azurl))
      raw_response = urllib2.urlopen(azurl).read().decode('utf-8')
      logger.info("Read {}, {} from az successfully".format(az_artist, az_song))
      az_parser = AZLyricsHTMLParser()
      az_parser.feed(raw_response)
      return az_parser.lyrics
    except urllib2.HTTPError, e:
      logger.debug("Could not read url {}. Code: {}".format(azurl, e.getcode()))
    except Exception as e:
      logger.debug("Could not read url {}. Error: {}".format(azurl, e))

  def azfy(self, text):
    return re.sub(r'\W+', '', text.split(" ft ")[0].replace("the", "")).strip().lower()


def main():
  parser = argparse.ArgumentParser()
  # Data and vocabulary file
  parser.add_argument('--path', type=str,
                      default='/tmp/lyrics/',
                      help='Directory where the lyrics are saved')
  parser.add_argument('--year', type=int,
                      default=2011,
                      help='Year of lyrics to grab')
  args = parser.parse_args()

  file = ".{}".format(args.year)
  temp_file_path = os.path.join(args.path, file)
  temp_file_dir = os.path.dirname(temp_file_path)
  if not os.path.exists(temp_file_dir):
    os.makedirs(temp_file_dir)
    logger.info("Created: %s", temp_file_dir)
  else:
    files_in_dir = os.listdir(temp_file_dir)
    if files_in_dir:
      logger.info("Files in dir: %s", files_in_dir)
      if file in files_in_dir:
        logger.error("The file exists already: %s", temp_file_path)
        return

  song_list_grab = SongListGrabSpotify()
  all_lyrics = song_list_grab.get_songs_from_year(args.year, AZLyricsGrab())
  if all_lyrics:
    logger.info("Writing file: %s", temp_file_path)
    with open(temp_file_path, 'w') as file:
      return file.write(all_lyrics.encode('utf8') + '\n')
  else:
    logger.error("No songs found, returning")


if __name__ == "__main__":
  main()
