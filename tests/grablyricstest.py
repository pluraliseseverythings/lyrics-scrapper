import os
import unittest
from grablyrics import *

PATH_DIRNAME = os.path.dirname(os.path.realpath(__file__))


class TestMyHTMLParser(unittest.TestCase):

  def test_parse(self):
    parser = AZLyricsHTMLParser()
    with open(PATH_DIRNAME + '/resources/az_html_1.txt', 'r') as html_file:
      html = html_file.read()
    with open(PATH_DIRNAME + '/resources/az_lyrics_1.txt', 'r') as lyrics_file:
      lyrics = lyrics_file.read()
    parser.feed(html)
    self.assertEqual(lyrics, parser.lyrics)


class UkChartHTMLParser(unittest.TestCase):

  def test_parse(self):
    parser = UKChartHTMLParser()
    with open(PATH_DIRNAME + '/resources/ukchart_html.txt', 'r') as html_file:
      html = html_file.read()
    with open(PATH_DIRNAME + '/resources/ukchart_song.txt', 'r') as songs_file:
      songs = songs_file.read()
    parser.feed(html)
    self.assertEqual(eval(songs), parser.songs)


if __name__ == '__main__':
    unittest.main()