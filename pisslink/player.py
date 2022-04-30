import datetime
import discord

from typing import Any, Dict, Optional, Union
from discord.channel import VoiceChannel
from . import abc
from .pool import Node, NodePool
from .utils import MISSING

__all__ = (
    'Player'
)

VoiceChannel = Union[
    discord.VoiceChannel, discord.StageChannel
]

class Player(discord.VoiceProtocol):

    def __call__(self, client: discord.Client, channel: VoiceChannel) -> None:
        self.client: discord.Client = client
        self.channel: VoiceChannel = channel
        return self

    def __init__(self, client: discord.Client = MISSING, channel: VoiceChannel = MISSING, *, node: Node = MISSING) -> None:
        self.client: discord.Client = client
        self.channel: VoiceChannel = channel
        if node is MISSING:
            node = NodePool.get_node()
        self.node: Node = node
        self.node._players.append(self)
        self._voice_state: Dict[str, Any] = {}
        self.last_update: datetime.datetime = MISSING
        self.last_position: float = MISSING
        self.volume: float = 100
        self._paused: bool = False
        self._source: Optional[abc.Playable] = None
        self._connected: bool = False

    @property
    def guild(self) -> discord.Guild:
        return self.channel.guild

    @property
    def source(self) -> Optional[abc.Playable]:
        return self._source

    async def update_state(self, state: Dict[str, Any]) -> None:
        state = state['state']
        self.last_update = datetime.datetime.fromtimestamp(state.get('time', 0) / 1000, datetime.timezone.utc)
        self.last_position = round(state.get('position', 0) / 1000, 1)

    async def on_voice_server_update(self, data: Dict[str, Any]) -> None:
        self._voice_state.update({'event': data})
        await self._dispatch_voice_update()

    async def on_voice_state_update(self, data: Dict[str, Any]) -> None:
        self._voice_state.update({'sessionId': data['session_id']})
        channel_id = data['channel_id']
        if not channel_id:
            self._voice_state.clear()
            await self.disconnect()
            return
        self.channel = self.guild.get_channel(int(channel_id))

    async def _dispatch_voice_update(self) -> None:
        if {'sessionId', 'event'} == self._voice_state.keys():
            await self.node._websocket.send(op='voiceUpdate', guildId=str(self.guild.id), **self._voice_state)

    async def connect(self, *, timeout: float, reconnect: bool) -> None:
        await self.guild.change_voice_state(channel=self.channel)
        self._connected = True

    async def disconnect(self, *, force: bool) -> None:
        await self.guild.change_voice_state(channel=None)
        self._connected = False
        self.node.players.remove(self)
        self.cleanup()

    async def move_to(self, channel: discord.VoiceChannel) -> None:
        await self.guild.change_voice_state(channel=channel)

    async def play(self, source: abc.Playable, replace: bool = True, start: int = 0, end: int = 0):
        '''Play a track.'''
        if replace or not self.is_playing():
            await self.update_state({'state': {}})
            self._paused = False
        else:
            return
        self._source = source
        payload = {
            'op': 'play',
            'guildId': str(self.guild.id),
            'track': source.id,
            'noReplace': not replace,
            'startTime': str(start),
        }
        if end > 0:
            payload['endTime'] = str(end)
        await self.node._websocket.send(**payload)
        return source

    def is_connected(self) -> bool:
        '''Indicates whether the player is connected to voice.'''
        return self._connected

    def is_playing(self) -> bool:
        '''Indicates wether a track is currently being played.'''
        return self.is_connected() and self._source is not None

    def is_paused(self) -> bool:
        '''Indicates wether the currently playing track is paused.'''
        return self._paused

    async def stop(self) -> None:
        '''Stop the Player's currently playing song.'''
        await self.node._websocket.send(op='stop', guildId=str(self.guild.id))
        self._source = None

    async def pause(self) -> None:
        '''Pauses the player if it was playing.'''
        await self.node._websocket.send(
            op='pause', guildId=str(self.guild.id), pause=True
        )
        self._paused = True

    async def resume(self) -> None:
        '''Resumes the player if it was paused.'''
        await self.node._websocket.send(
            op='pause', guildId=str(self.guild.id), pause=False
        )
        self._paused = False