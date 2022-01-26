import math
import asyncio
import discord
import pisslink
import re
import spotipy
import random

from discord.commands import slash_command
from discord.ext import commands
from discord import Option

YOUTUBE_REGEX = re.compile(r'^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$')
SPOTIFY_REGEX = re.compile(r'https?://open.spotify.com/(?P<type>album|playlist|track)/(?P<id>[a-zA-Z0-9]+)')
YOUTUBE_REGEX = re.compile(r'^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$')
PLAYLIST_REGEX = re.compile(r'^https?:\/\/(www.youtube.com|youtube.com)\/playlist(.*)$')
URL_REGEX = re.compile(r'https?://(?:www\.)?.+')
SPOTIFY_CLIENT_ID = 'SPOTIFY_CLIENT_ID'
SPOTIFY_CLIENT_SECRET = 'SPOTIFY_CLIENT_SECRET'

class Client(discord.Bot):

    def __init__(self):
        super().__init__()

class UserNotConnected(discord.ApplicationCommandError):
    pass

class NoAccess(discord.ApplicationCommandError):
    pass

class NotSameChannel(discord.ApplicationCommandError):
    pass

class NoTracksFound(discord.ApplicationCommandError):
    pass

class AlreadyConnected(discord.ApplicationCommandError):
    pass

class NotConnected(discord.ApplicationCommandError):
    pass

class NotPrivileged(discord.ApplicationCommandError):
    pass

class NotPlaying(discord.ApplicationCommandError):
    pass

class DisableLooping(discord.ApplicationCommandError):
    pass

class NoTracksLeft(discord.ApplicationCommandError):
    pass

class InvalidURL(discord.ApplicationCommandError):
    pass

class Queue:

    def __init__(self):
        self._queue = []

    @property
    def next_track(self) -> pisslink.Track:
        if not self.is_empty():
            return self._queue[0]

    @property
    def length(self) -> int:
        return len(self._queue)

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def get_track(self) -> pisslink.Track:
        if not self.is_empty():
            return self._queue.pop(0)

    def add(self, track : pisslink.Track) -> pisslink.Track:
        self._queue.append(track)
        return track

    def add_top(self, track : pisslink.Track) -> pisslink.Track:
        self._queue.insert(0, track)
        return track

    def clear(self) -> None:
        self._queue.clear()

    def shuffle(self) -> None:
        random.shuffle(self._queue)

class Player(pisslink.Player):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = Queue()
        self.skip_votes = set()
        self.loop = False
        self.current_track = None
        self.dj = None

    async def teardown(self):
        self.queue.clear()
        await self.stop()
        await self.disconnect(force=False)

    async def add_track(self, track):
        self.queue.add(track)
        if not self.is_playing() and not self.queue.is_empty():
            await self.advance()

    async def advance(self):
        if self.loop:
            await self.play(self.current_track)
        elif (track := self.queue.get_track()):
            self.skip_votes.clear()
            if track.id == 'spotify':
                track = await pisslink.PisslinkTrack.search(track.title, return_first=True)
                if not track:
                    return await self.advance()
            await self.play(track)
            self.current_track = track
        else:
            self.current_track = None
            await asyncio.sleep(300)
            if self.is_connected() and not self.is_playing():
                await self.teardown()

class Music(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.spotify = spotipy.Spotify(client_credentials_manager=spotipy.SpotifyClientCredentials(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET))
        self.client.loop.create_task(self.node())

    def cog_unload(self):
        self.client.loop.create_task(self.disconnect_all())

    async def disconnect_all(self):
        for guild in self.client.guilds:
            player = guild.voice_client
            if player and player.is_connected():
                await player.teardown()

    async def node(self):
        await self.client.wait_until_ready()
        await pisslink.NodePool.create_node(
            client = self.client,
            host = '127.0.0.1',
            port = 2333,
            password = 'youshallnotpass'
        )

    async def cog_command_error(self, ctx, error):
        if isinstance(error, UserNotConnected):
            await ctx.respond('You are not connected to a voice channel.', ephemeral=True)
        if isinstance(error, NoAccess):
            await ctx.respond('I do not have access to this channel.', ephemeral=True)
        if isinstance(error, NotSameChannel):
            await ctx.respond('You must be connected to the same channel as the bot.', ephemeral=True)
        if isinstance(error, NoTracksFound):
            await ctx.respond('No songs found.', ephemeral=True)
        if isinstance(error, AlreadyConnected):
            await ctx.respond('I am already connected to a voice channel.', ephemeral=True)
        if isinstance(error, NotConnected):
            await ctx.respond('I am not connected to a voice channel.', ephemeral=True)
        if isinstance(error, NotPrivileged):
            await ctx.respond('This command can only be used by the dj and admins. Being alone in the channel also works.', ephemeral=True)
        if isinstance(error, NotPlaying):
            await ctx.respond('No music playing.', ephemeral=True)
        if isinstance(error, DisableLooping):
            await ctx.respond('Disable looping first.', ephemeral=True)
        if isinstance(error, NoTracksLeft):
            await ctx.respond('There are no songs left in the queue.', ephemeral=True)
        if isinstance(error, InvalidURL):
            await ctx.respond('Only spotify and youtube URLs are supported.', ephemeral=True)

    def required(self, ctx):
        player = ctx.voice_client
        count = 0
        for member in player.channel.members:
            if not member.bot:
                count += 1
        return math.ceil(count / 2.5)

    def length(self, ctx):
        player = ctx.voice_client
        count = 0
        for member in player.channel.members:
            if not member.bot:
                count += 1
        return count

    def is_privileged(self, ctx):
        player = ctx.voice_client
        return player.dj == ctx.author or ctx.author.guild_permissions.manage_channels

    @commands.Cog.listener()
    async def on_pisslink_track_end(self, player, track, reason):
        await player.advance()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        player = self.get_player(member.guild)
        if member.id == self.client.user.id:
            if before.channel and not after.channel:
                if player and player.is_connected():
                    await player.teardown()
            elif before.channel and after.channel and before.channel != after.channel:
                if not player.dj or not player.dj in after.channel.members:
                    count = 0
                    for m in after.channel.members:
                        if m.bot:
                            continue
                        player.dj = m
                        count += 1
                        break
                    if count == 0:
                        player.dj = None
        elif player and player.is_connected():
            count = 0
            for m in player.channel.members:
                if not m.bot:
                    count += 1
            if count == 0:
                player.dj = None
                await asyncio.sleep(300)
                count = 0
                for m in player.channel.members:
                    if not m.bot:
                        count += 1
                if player.is_connected() and count == 0:
                    await player.teardown()
            elif member == player.dj and after.channel != before.channel:
                count = 0
                for m in player.channel.members:
                    if m.bot:
                        continue
                    player.dj = m
                    count += 1
                    break
                if count == 0:
                    player.dj = None
            elif after.channel == player.channel and not player.dj in player.channel.members:
                player.dj = member

    @slash_command()
    async def join(self, ctx):
        '''Make the bot join your voice channel.'''
        player = ctx.voice_client
        if player and player.is_connected():
            raise AlreadyConnected
        elif not ctx.author.voice:
            raise UserNotConnected
        else:
            try:
                channel = ctx.author.voice.channel
                await channel.connect(cls=Player())
                player = ctx.voice_client
                player.dj = ctx.author
                await ctx.respond(f'Joined {channel.name}.')
            except discord.Forbidden:
                raise NoAccess

    @slash_command()
    async def leave(self, ctx):
        '''Make the bot leave your voice channel.'''
        player = ctx.voice_client
        if not player:
            raise NotConnected
        elif ctx.author.voice is None or player.channel != ctx.author.voice.channel:
            raise NotSameChannel
        elif self.length(ctx) >= 3 and not self.is_privileged(ctx):
            raise NotPrivileged
        else:
            channel = player.channel
            await player.teardown()
            await ctx.respond(f'Left {channel.name}.')

    @slash_command()
    async def play(self, ctx, query: Option(str, 'Search query or Spotify/Youtube URL.')):
        '''Add a song to the queue from Spotify or Youtube (URL or search query).'''
        player = ctx.voice_client
        await ctx.defer()
        if not player:
            if not ctx.author.voice:
                raise UserNotConnected
            else:
                try:
                    channel = ctx.author.voice.channel
                    await channel.connect(cls=Player())
                    player = ctx.voice_client
                    player.dj = ctx.author
                except discord.Forbidden:
                    raise NoAccess
        if not ctx.author.voice or player.channel != ctx.author.voice.channel:
            raise NotSameChannel
        else:
            if SPOTIFY_REGEX.match(query):
                url_check = SPOTIFY_REGEX.match(query)
                search_type = url_check.group('type')
                if search_type == 'track':
                    result = self.spotify.track(track_id=query)
                    if not result:
                        raise NoTracksFound
                    else:
                        try:
                            artists = []
                            for artist in result['artists']:
                                artists.append(artist['name'])
                            artists = ' & '.join(artists)
                            name = f'{artists} - {result["name"]}'
                            track = await pisslink.PisslinkTrack.search(name, return_first=True)
                            if player.queue.is_empty() and not player.is_playing() and not player.is_paused():
                                await player.add_track(track)
                                await ctx.respond(f'Playing "{track.title}" now.')
                            else:
                                await player.add_track(track)
                                await ctx.respond(f'Added "{track.title}" to the queue.')
                        except:
                            raise NoTracksFound
                elif search_type == 'playlist':
                    result = self.spotify.playlist_tracks(playlist_id=query)
                    if not result:
                        raise NoTracksFound
                    else:
                        try:
                            tracklist = result['items']
                            while result['next']:
                                result = self.spotify.next(result)
                                tracklist.extend(result['items'])
                            tracks = []
                            for track in tracklist:
                                try:
                                    artists = []
                                    for artist in track['track']['artists']:
                                        artists.append(artist['name'])
                                    artists = ' & '.join(artists)
                                    trackobject = pisslink.Track(
                                        id='spotify',
                                        info={
                                            'title': f'{artists} - {track["track"]["name"]}',
                                            'Author': None,
                                            'length': track['track']['duration_ms'],
                                            'identifier': None,
                                            'uri': None,
                                            'isStream': False,
                                        }
                                    )
                                    tracks.append(trackobject)
                                except:
                                    continue
                            if len(tracks) == 0:
                                raise NoTracksFound
                            else:
                                for track in tracks:
                                    await player.add_track(track)
                                await ctx.respond(f'Added {len(tracks)} songs to the queue.')
                        except:
                            raise NoTracksFound
                elif search_type == 'album':
                    result = self.spotify.album_tracks(album_id=query)
                    if not result:
                        raise NoTracksFound
                    else:
                        try:
                            tracklist = result['items']
                            while result['next']:
                                result = self.spotify.next(result)
                                tracklist.extend(result['items'])
                            tracks = []
                            for track in tracklist:
                                try:
                                    artists = []
                                    for artist in track['artists']:
                                        artists.append(artist['name'])
                                    artists = ' & '.join(artists)
                                    trackobject = pisslink.Track(
                                        id='spotify',
                                        info={
                                            'title': f'{artists} - {track["name"]}',
                                            'Author': None,
                                            'length': track['duration_ms'],
                                            'identifier': None,
                                            'uri': None,
                                            'isStream': False,
                                        }
                                    )
                                    tracks.append(trackobject)
                                except:
                                    continue
                            if len(tracks) == 0:
                                raise NoTracksFound
                            else:
                                for track in tracks:
                                    await player.add_track(track)
                                await ctx.respond(f'Added {len(tracks)} songs to the queue.')
                        except:
                            raise NoTracksFound
                else:
                    raise NoTracksFound
            elif PLAYLIST_REGEX.match(query):
                track = await pisslink.PisslinkTrack.get_playlist(query)
                if not track:
                    raise NoTracksFound
                else:
                    for track in track.tracks:
                        await player.add_track(track)
                    await ctx.respond(f'Added {len(track.tracks)} songs to the queue.')
            elif YOUTUBE_REGEX.match(query):
                track = await pisslink.PisslinkTrack.get(query, return_first=True)
                if not track:
                    raise NoTracksFound
                if player.queue.is_empty() and not player.is_playing() and not player.is_paused():
                    await player.add_track(track)
                    await ctx.respond(f'Playing "{track.title}" now.')
                else:
                    await player.add_track(track)
                    await ctx.respond(f'Added "{track.title}" to the queue.')
            elif URL_REGEX.match(query):
                raise InvalidURL
            else:
                track = await pisslink.PisslinkTrack.search(query, return_first=True)
                if not track:
                    raise NoTracksFound
                if player.queue.is_empty() and not player.is_playing() and not player.is_paused():
                    await player.add_track(track)
                    await ctx.respond(f'Playing "{track.title}" now.')
                else:
                    await player.add_track(track)
                    await ctx.respond(f'Added "{track.title}" to the queue.')

    @slash_command()
    async def voteskip(self, ctx):
        '''Vote to skip the currently playing song.'''
        player = ctx.voice_client
        if not player:
            raise NotConnected
        elif not ctx.author.voice or player.channel != ctx.author.voice.channel:
            raise NotSameChannel
        elif not player.is_playing():
            raise NotPlaying
        elif player.loop:
            raise DisableLooping
        elif self.length(ctx) >= 3:
            required = self.required(ctx)
            if ctx.author in player.skip_votes:
                player.skip_votes.remove(ctx.author)
                await ctx.respond(f'{ctx.author.display_name} is no longer voting to skip. {len(player.skip_votes)}/{required} required votes.')
            else:
                player.skip_votes.add(ctx.author)
                if len(player.skip_votes) >= required:
                    player.skip_votes.clear()
                    if player.queue.is_empty():
                        await player.stop()
                        await ctx.respond('Skipped song.')
                    else:
                        next_track = player.queue.next_track
                        await player.stop()
                        await ctx.respond(f'Skipped song. Now playing: {next_track.title}.')
                else:
                    await ctx.respond(f'{ctx.author.display_name} voted to skip. {len(player.skip_votes)}/{required} required votes.')
        else:
            if player.queue.is_empty():
                await player.stop()
                await ctx.respond('Skipped song.')
            else:
                next_track = player.queue.next_track
                await player.stop()
                await ctx.respond(f'Skipped song. Now playing: {next_track.title}.')

    @slash_command()
    async def shuffle(self, ctx):
        '''Shuffle the queue.'''
        player = ctx.voice_client
        if not player:
            raise NotConnected
        elif not ctx.author.voice or player.channel != ctx.author.voice.channel:
            raise NotSameChannel
        elif player.queue.is_empty():
            raise NoTracksLeft
        elif self.length(ctx) >= 3 and not self.is_privileged(ctx):
            raise NotPrivileged
        else:
            player.queue.shuffle()
            await ctx.respond('Shuffled the queue.')

    @slash_command()
    async def loop(self, ctx):
        '''Loop the currently playing song.'''
        player = ctx.voice_client
        if not player:
            raise NotConnected
        elif not ctx.author.voice or player.channel != ctx.author.voice.channel:
            raise NotSameChannel
        elif not player.is_playing():
            raise NotPlaying
        elif self.length(ctx) >= 3 and not self.is_privileged(ctx):
            raise NotPrivileged
        elif player.loop:
            player.loop = False
            await ctx.respond('Looping disabled.')
        else:
            player.loop = True
            await ctx.respond('Looping current song.')

client = Client()
client.add_cog(Music(client))
client.run('TOKEN')