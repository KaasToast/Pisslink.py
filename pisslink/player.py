import asyncio
import os
import discord
import re
import ffmpeg

from typing import Optional, Union, Any, List
from youtube_dl import YoutubeDL
from spotipy import Spotify, SpotifyClientCredentials
from discord.ext import tasks

from .tracks import PartialTrack, Track, LocalTrack, Playlist
from .errors import *
from .queue import Queue

YOUTUBE_REGEX = re.compile(r'^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$')
SPOTIFY_REGEX = re.compile(r'https?://open.spotify.com/(?P<type>album|playlist|track)/(?P<id>[a-zA-Z0-9]+)')
PLAYLIST_REGEX = re.compile(r'^https?:\/\/(www.youtube.com|youtube.com)\/playlist(.*)$')
URL_REGEX = re.compile(r'https?://(?:www\.)?.+')

class Logger(object):
    '''A base logger that outputs nothing.'''

    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass

class Player:
    '''
    The base player that provides the basic functionality for playing music and managing the inbuilt queue. 
    This class should not be created but rather retrieved through the :class:`Pool`.

    Args:
        client: The bot.
        spotify_client_id: The client ID for the Spotify application.
        spotify_client_secret: The client secret for the Spotify application.
        track_conversion_interval: The interval in seconds at which the bot will convert :class:`PartialTrack` objects to :class:`Track` objects. This makes initial track loading faster. Set to 0 to disable.
        cookies_path: The path to the cookies.txt file.
        proxies: A list of available proxies to use. Leave empty to disable proxying.
        proxy_rotation_interval: The interval in seconds at which proxies are rotated.
    '''

    def __init__(
            self,
            client: discord.Bot,
            spotify_client_id: Optional[str],
            spotify_client_secret: Optional[str],
            track_conversion_interval: int,
            cookies_path: Optional[str],
            proxies: Optional[List[str]] = None,
            proxy_rotation_interval: int = 600
        ) -> None:
        ydl_opts = {'format': 'bestaudio/best', 'logger': Logger()}
        if cookies_path:
            ydl_opts['cookiefile'] = cookies_path
        self.ydl: YoutubeDL = YoutubeDL(ydl_opts)
        self.client = client
        self.queue = Queue()
        self.spotify: Optional[Spotify] = self.spotify_check(spotify_client_id, spotify_client_secret)
        self.channel: Optional[discord.VoiceChannel] = None
        self.current: Optional[Track] = None
        self.track_conversion_interval: int = track_conversion_interval
        self.cookies_path: Optional[str] = cookies_path
        self.proxies: Optional[List[str]] = proxies
        self.proxy_rotation_interval: int = proxy_rotation_interval
        self.proxy_position: int = 0
        self.stopevent: str = 'FINISHED'
        self.connected: bool = False
        self.playing: bool = False
        self.paused: bool = False
        self.loop: bool = False
        client.add_listener(self.on_voice_state_update, 'on_voice_state_update')
        if not self._track_converter.is_running() and track_conversion_interval > 0:
            self._track_converter.start()
        if not self._rotate_proxy.is_running() and proxies and len(proxies) > 0:
            self._rotate_proxy.start()

    @property
    def guild(self) -> Optional[discord.Guild]:
        return getattr(self.channel, 'guild', None)

    def spotify_check(self, spotify_client_id: str, spotify_client_secret: str) -> Optional[Spotify]:
        '''
        Checks if the spotify client credentials are valid and returns a spotify client if they are.
        This method should not be called directly.

        Args:
            spotify_client_id: The client id of the spotify application.
            spotify_client_secret: The client secret of the spotify application.

        Returns:
            :class:`Spotify` or :class:`None` if no credentials are provided or if the credentials are invalid.
        '''
        try:
            spotify = Spotify(client_credentials_manager=SpotifyClientCredentials(spotify_client_id, spotify_client_secret))
            spotify.categories()
            return spotify
        except:
            return

    async def dispatch(self, event: str, *args: Any) -> None:
        '''
        Dispatches an event to the :class:`Bot`. This method should not be called directly.

        Args:
            event: The event to dispatch.
            *args: The arguments to pass to the event.
        '''
        self.client.dispatch(event, *args)
        if event == 'track_end':
            self.stopevent = 'FINISHED'
            self.playing = False
            if self.connected:
                await self.advance()

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        '''Handles voice state updates.'''
        if member == member.guild.me and before.channel != after.channel:
            self.channel = after.channel
            if not after.channel:
                await self.teardown()

    async def teardown(self) -> None:
        self.connected = False
        self.client.loop.create_task(self.dispatch('player_destroy', self))
        if self._track_converter.is_running():
            self._track_converter.stop()
        if self._rotate_proxy.is_running():
            self._rotate_proxy.stop()

    async def connect(self, channel: discord.VoiceChannel) -> None:
        '''
        Connects to specified :class:`VoiceChannel`. This method should be called rather than the :method:`connect` method on :class:`VoiceChannel`.

        Args:
            channel: The :class:`VoiceChannel` to connect to.

        Raises:
            :exc:`NoAccess`: If the bot does not have access to the :class:`VoiceChannel`.
        '''
        if not channel.permissions_for(channel.guild.me).connect:
            raise NoAccess
        self.connected = True
        self.channel = channel
        await channel.connect()

    async def disconnect(self) -> None:
        '''
        Disconnects the bot from the :class:`VoiceChannel` it's connected to. This method should be called rather than the :method:`disconnect` method on :class:`VoiceClient`.

        Raises:
            :exc:`NotConnected`: If the bot is not connected to a :class:`VoiceChannel`.
        '''
        if not self.connected:
            raise NotConnected
        await self.guild.voice_client.disconnect()
        await self.teardown()

    async def move_to(self, channel: discord.VoiceChannel) -> None:
        '''
        Moves the bot to the specified :class:`VoiceChannel`. This method should be called rather than the :method:`move_to` method on :class:`VoiceClient` or :class:`Member`.

        Args:
            channel: The :class:`VoiceChannel` to move the bot to.

        Raises:
            :exc:`NotConnected`: If the bot is not connected to a :class:`VoiceChannel`.
        '''
        if not self.connected:
            raise NotConnected
        await self.guild.me.move_to(channel)

    async def play(self, track: Track) -> None:
        '''
        Plays the specified :class:`Track`. 
        This method should not be used if you plan on using the queue system. This method should be called rather than the :method:`play` method on :class:`VoiceClient`.
        :class:`Track` objects should be retrieved through :method:`get_tracks`.

        Args:
            track: The :class:`Track` to play.

        Raises:
            :exc:`NotConnected`: If the bot is not connected to a :class:`VoiceChannel`.
        '''
        if not self.connected:
            raise NotConnected
        if isinstance(track, PartialTrack):
            try:
                track = await self.get_tracks(track.url) if track.url else await self.get_tracks(track.title)
            except:
                if self.connected:
                    await self.advance()
                return
        self.current = track
        self.playing = True
        if isinstance(track, LocalTrack):
            self.guild.voice_client.play(discord.FFmpegPCMAudio(track.path), after=lambda error: self.client.loop.create_task(self.dispatch('track_end', self, track, self.stopevent)))
        else:
            self.guild.voice_client.play(discord.FFmpegOpusAudio(track.endpoint, codec='copy'), after=lambda error: self.client.loop.create_task(self.dispatch('track_end', self, track, self.stopevent)))

    async def stop(self) -> None:
        '''
        Clears the queue and stops playing entirely. This method should be called rather than the :method:`stop` method on :class:`VoiceClient`. For skipping songs use :method:`skip` instead.

        Raises:
            :exc:`NotConnected`: If the bot is not connected to a :class:`VoiceChannel`.
        '''
        if not self.connected:
            raise NotConnected
        self.stopevent = 'STOPPED'
        self.queue.clear()
        self.loop = False
        self.guild.voice_client.stop()

    async def skip(self) -> None:
        '''
        Skips the currently playing song and starts playing the next one, if available.

        Raises:
            :exc:`NotConnected`: If the bot is not connected to a :class:`VoiceChannel`.
        '''
        if not self.connected:
            raise NotConnected
        self.stopevent = 'STOPPED'
        self.guild.voice_client.stop()

    async def pause(self) -> None:
        '''
        Pauses the currently playing song if not already paused. This method should be called rather than the :method:`pause` method on :class:`VoiceClient`. To resume playback use :method:`resume`.
        
        Raises:
            :exc:`NotConnected`: If the bot is not connected to a :class:`VoiceChannel`.
        '''
        if not self.connected:
            raise NotConnected
        if not self.guild.voice_client.is_paused():
            self.guild.voice_client.pause()
            self.paused = True

    async def resume(self) -> None:
        '''
        Resumes the currently playing song if it is paused. This method should be called rather than the :method:`resume` method on :class:`VoiceClient`.

        Raises:
            :exc:`NotConnected`: If the bot is not connected to a :class:`VoiceChannel`.
        '''
        if not self.connected:
            raise NotConnected
        if self.guild.voice_client.is_paused():
            self.guild.voice_client.resume()
            self.paused = False

    async def advance(self) -> None:
        '''
        Advances the queue to the next song or replays current song if :attr:`loop` is enabled. This method should be called rather than the :method:`play` method if you want to make use of the queue system. You first need to add songs to the :class:`Queue` using :method:`add`.
        
        This method is automatically called when the current song ends.
        '''
        if self.loop:
            await self.play(self.current)
        elif track := self.queue.get():
            await self.play(track)
        else:
            self.current = None

    async def get_tracks(self, query: str) -> Optional[Union[Track, Playlist]]:
        '''
        Retrieves a :class:`Track` or :class:`Playlist` from the specified :param:`query`.

        This :class:`Track` can then be played or added to the :class:`Queue`.

        Args:
            query: The YouTube video or playlist URL, Spotify track, playlist or album URL or YouTube search query.

        Returns:
            :class:`Track` or :class:`Playlist`: The :class:`Track` or :class:`Playlist` retrieved from the specified :param:`query`. If no tracks are found, :class:`None` is returned.
        '''
        query = query.strip('<>')
        if spotify_match := SPOTIFY_REGEX.match(query):
            if not self.spotify:
                return
            search = spotify_match.group('type')
            if search == 'track':
                result = self.spotify.track(track_id=query)
                if not result:
                    return
                try:
                    return await self.get_tracks(f'{" & ".join([artist["name"] for artist in result["artists"]])} - {result["name"]}')
                except:
                    return
            elif search == 'playlist' or search == 'album':
                if search == 'playlist':
                    result = self.spotify.playlist_tracks(playlist_id=query)
                elif search == 'album':
                    result = self.spotify.album_tracks(album_id=query)
                if not result:
                    return
                try:
                    tracklist = result['items']
                    while result['next']:
                        result = self.spotify.next(result)
                        tracklist.extend(result['items'])
                    tracks = []
                    if search == 'playlist':
                        for track in tracklist:
                            try:
                                tracks.append(PartialTrack({'title': f'{" & ".join([artist["name"] for artist in track["track"]["artists"]])} - {track["track"]["name"]}', 'duration': int(track.get('track', {}).get('duration_ms', 0) // 1000)}))
                            except:
                                continue
                    elif search == 'album':
                        for track in tracklist:
                            try:
                                tracks.append(PartialTrack({'title': f'{" & ".join([artist["name"] for artist in track["artists"]])} - {track["name"]}', 'duration': int(track.get('duration_ms', 0) // 1000)}))
                            except:
                                continue
                    if len(tracks) == 0:
                        return
                    if search == 'playlist':
                        return Playlist({'title': self.spotify.playlist(query, fields='name')['name'], 'tracks': tracks})
                    elif search == 'album':
                        return Playlist({'title': self.spotify.album(query)['name'], 'tracks': tracks})
                except:
                    return
        elif PLAYLIST_REGEX.match(query):
            result = self.ydl.extract_info(query, download=False, process=False)
            if not result:
                return
            tracks = []
            for track in result['entries']:
                try:
                    tracks.append(PartialTrack({'title': track['title'], 'duration': int(track.get('duration', 0)), 'url': f'https://www.youtube.com/watch?v={track["id"]}'}))
                except:
                    continue
            if len(tracks) == 0:
                return
            return Playlist({'title': result['title'], 'tracks': tracks})
        elif YOUTUBE_REGEX.match(query):
            try:
                return Track(self.ydl.extract_info(query, download=False))
            except:
                return
        elif URL_REGEX.match(query):
            return
        else:
            try:
                result = self.ydl.extract_info(f'ytsearch:{query}', download=False)
            except:
                return
            if len(result['entries']) == 0:
                return
            return Track(result['entries'][0])

    async def get_local_track(self, path: str) -> Optional[LocalTrack]:
        '''
        Retrieves a :class:`LocalTrack` located at :param:`path`.

        This :class:`LocalTrack` can then be played or added to the :class:`Queue`.

        Args:
            path: The path to the file.

        Returns:
            :class:`LocalTrack`: The :class:`LocalTrack` retrieved from the specified :param:`path`. If the file does not exist or is not in a valid format, :class:`None` is returned.
        '''
        formats = ('webm', 'mkv', 'ogg', 'avi', 'mov', 'mp4', 'mpeg', 'mpg', 'm4v', 'aac', 'flac', 'mp3', 'wav')
        if not os.path.isfile(path) or not path.lower().endswith(formats):
            return
        return LocalTrack({'title': os.path.basename(path).rsplit('.', 1)[0].replace('_', ' ').rsplit(' - ', 1)[0], 'duration': round(float(ffmpeg.probe(path)['format']['duration'])), 'path': path})

    @tasks.loop()
    async def _track_converter(self) -> None:
        '''
        A background task that replaces :class:`PartialTrack` objects with :class:`Track` objects in the :class:`Queue`. You can specify the interval at which this task runs using the :attr:`track_conversion_interval` attribute. If set to 0 this task will not run.
        '''
        for track in self.queue.tracks:
            if isinstance(track, PartialTrack):
                index = self.queue.tracks.index(track)
                try:
                    converted_track = await self.get_tracks(track.url) if track.url else await self.get_tracks(track.title)
                except:
                    converted_track = None
                if track in self.queue.tracks:
                    self.queue.tracks.remove(track)
                    if converted_track:
                        self.queue.tracks.insert(index, converted_track)
                break
        await asyncio.sleep(self.track_conversion_interval)

    @tasks.loop()
    async def _rotate_proxy(self) -> None:
        '''
        A background task that rotates the :attr:`proxy_list` and :attr:`proxy_index` attributes. You can specify the interval at which this task runs using the :attr:`proxy_rotation_interval` attribute.
        '''
        if self.proxy_position > len(self.proxy_list):
            self.proxy_position = 0
        ydl_opts = {'format': 'bestaudio/best', 'logger': Logger(), 'proxy': self.proxies[self.proxy_position]}
        if self.cookies_path:
            ydl_opts['cookiefile'] = self.cookies_path
        self.ydl = YoutubeDL(ydl_opts)
        self.proxy_position += 1
        await asyncio.sleep(self.proxy_rotation_interval)