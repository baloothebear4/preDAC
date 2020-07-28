#!/usr/bin/env python
"""
 preDAC preamplifier project

 StreamerInterface class
    - provides an interface to a remote MPD server
    - reads socket and provides metadata for display
    - Potentially works for Airplay too - future enhancement

 baloothebear4
 v1 June 2020
 """

from mpd          import MPDClient
from events       import Events
from threading    import Thread
import time


SONG_KEYS       = ('file', 'artist', 'album', 'title', 'comment', 'pos', 'id')
STATUS_KEYS     = ('repeat', 'random', 'single', 'consume', 'playlist', 'playlistlength', \
                    'mixrampdb', 'state', 'song', 'songid', 'time', 'elapsed', 'bitrate', \
                    'duration', 'audio', 'nextsong', 'nextsongid')

class MPDMetaData:
    """
        Data model class to manage the metadata captured from MPD
    """

    SONG            = ('artist', 'album', 'title')
    STATUS          = ('state', 'elapsed', 'duration')
    ALL             = SONG + STATUS

    def __init__(self):
        self.clear_track()
        print("MPDMetaData.__init__> OK")

    def clear_track(self):
        self._metadata = { k : "" for k in MPDMetaData.ALL }

    @property
    def artist(self):
        return self._metadata['artist']

    @property
    def album(self):
        return self._metadata['album']

    @property
    def track(self):
        return self._metadata['title']

    @property
    def playing(self):
        return self._metadata['state']=='play'

    @property
    def elapsedpc(self):
        try:
            return float(self._metadata['elapsed'])/float(self._metadata['duration'])
        except:
            return 0.0

    @property
    def metadata(self):
        return self._metadata

    def update(self, song, status):
        """ updates with new meta data and returns a list of the keys that have changed"""

        changed = { 'new_track' : False, 'play_state' : False}
        for key in song:
            if key in self._metadata and self._metadata[key] != song[key]:
                changed['new_track'] = True
                self._metadata[key] = song[key]

        for key in status:
            if key in self._metadata and self._metadata[key] != status[key]:
                if key == 'state' : changed['play_state'] = True
                self._metadata[key] = status[key]

        # print("MPDMetadata.update> changed %s, %s " % (changed, self ))
        return changed

    def __str__(self):
        text = ""
        for i, k in enumerate(self._metadata):
            text  += "%s : %s,  " % (k, self._metadata[k])
        return text


class StreamerInterface(MPDMetaData, Thread):
    """
        Use the socket based MPD interface to detect changes in status
        then to raise events to drive updates of new metadata

        Runs in a separate thread so that the idle method is blocking until a
        change in status is received and an Streamer Event is raised
    """
    STREAMER_IP  = { 'dac': '192.168.1.131', 'streamer': '192.168.1.218' }

    def __init__(self, events):
        self.events = events

        """ setup the interface and data model """
        MPDMetaData.__init__(self)

        # print("StreamerInterface._init__ > ready. MPD v", self.client.mpd_version)
        # self.start()

    def run(self):
        self.checkStreamerEvents()
        print("StreamerInterface.run > exit")

    def streamersource(self,source):
        """
            run if these source has metadata else stop

        """

        try:
            print("StreamerInterface.streamersource > stop")
            self.streamerstop()
            self.clear_track()
        except:
            pass
            # NB: may fail if nothing started

        if source in StreamerInterface.STREAMER_IP:
            print("StreamerInterface.run > start metadata for ", source)
            try:
                self.source = source
                self.client = MPDClient()                 # create client object
                self.client.timeout = 0.1                  # network timeout in seconds (floats allowed), default: None
                self.client.idletimeout = None            # timeout for fetching the result of the idle command is handled seperately, default: None
                self.client.connect(StreamerInterface.STREAMER_IP[source], 6600) # connect to MPD
                self.update( self.client.currentsong(), self.client.status())
                self.client.close()                     # send the close command
                self.client.disconnect()                # disconnect from the server

                """ as mpd.idle blocks, run as a separate thread """
                self.running = True
                self.checker = Thread(target=self.checkStreamerEvents)
                self.checker.start()
            except:
                print("StreamerInterface.run > failed start metadata for ", source)


    def streamerstop(self):
        self.running = False
        self.client.close()                     # send the close command
        self.client.disconnect()                # disconnect from the server
        self.clear_track()
        print("StreamerInterface.run > stop")

    def streamerpause(self):
        try:
            tempclient = MPDClient()                 # create client object
            tempclient.connect(StreamerInterface.STREAMER_IP[self.source], 6600) # connect to MPD
            tempclient.pause()
            tempclient.close()
            tempclient.disconnect()
        except Exception as e:
            print("StreamerInterface.streamerpause > failed ", e)


    def streamerplay(self):
        try:
            self.client.play()
        except Exception as e:
            print("StreamerInterface.streamerplay > failed ", e)

    def checkStreamerEvents(self):
        '''
            Loop indefinately waiting for MPD events
        '''
        while self.running:
            try:
                print ("\nStreamerInterface.checkStreamerEvents> wait for MPD events... ")
                self.client = MPDClient()                 # create client object
                self.client.idletimeout = None            # timeout for fetching the result of the idle command is handled seperately, default: None
                self.client.connect(StreamerInterface.STREAMER_IP[self.source], 6600) # connect to MPD

                self.client.idle('player')

                changed   = self.update( self.client.currentsong(), self.client.status())
                self.client.close()                     # send the close command
                self.client.disconnect()

                """ multiple events can be triggered from one event update """
                if changed['new_track']:
                    self.events.Streamer('new_track')

                if changed['play_state']:
                    if self.playing:
                        self.events.Streamer('start')
                    else:
                        self.events.Streamer('stop')

                print("StreamerInterface.checkStreamerEvents> processed changes ", changed)
                time.sleep(0.1)

            except Exception as e:
                print("StreamerInterface.checkStreamerEvents> exception", e)
                time.sleep(1)
                # break

    def StreamerAction(self, e):
        print('StreamerInterface> event %s' % e)
        print('Meta data: ', self.artist, self.track, self.album, self.playing, self.elapsedpc )

if __name__ == "__main__":
    try:
        # client = MPDClient()                 # create client object
        # client.timeout = 10                  # network timeout in seconds (floats allowed), default: None
        # client.idletimeout = None            # timeout for fetching the result of the idle command is handled seperately, default: None
        # client.connect(ALLODIGISIG_IP, 6600) # connect to localhost:6600
        #
        # print("current song> ", client.currentsong())
        # print("current status> ", client.status())
        # print("keys>", client.currentsong().keys(),client.status().keys() )
        # print("Wait until something significant happens [blocking]> ", client.idle())
        # client.close()                     # send the close command
        # client.disconnect()                # disconnect from the server
        events = Events('Streamer')

        s = StreamerInterface(events)
        events.Streamer += s.StreamerAction

        s.run()

    except KeyboardInterrupt:
        s.stop()
