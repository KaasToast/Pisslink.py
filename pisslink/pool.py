from __future__ import annotations

import json
import logging
import os
import aiohttp
import discord

from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, List, Optional, Tuple, Type, TypeVar
from discord.enums import try_enum
from . import abc
from .enums import *
from .errors import *
from .stats import Stats
from .utils import MISSING
from .websocket import Websocket

if TYPE_CHECKING:
    from .player import Player

__all__ = (
    'Node',
    'NodePool'
)

PT = TypeVar('PT', bound=abc.Playable)
PLT = TypeVar('PLT', bound=abc.Playlist)

class Node:

    def __init__(self, client: discord.Bot, host: str, port: int, password: str, https: bool, heartbeat: float, region: Optional[discord.VoiceRegion], identifier: str, dumps: Callable[[Any], str]):
        self.client: discord.Bot = client
        self._host: str = host
        self._port: int = port
        self._password: str = password
        self._https: bool = https
        self._heartbeat: float = heartbeat
        self._region: Optional[discord.VoiceRegion] = region
        self._identifier: str = identifier
        self._players: List[Player] = []
        self._dumps: Callable[[Any], str] = dumps
        self._websocket: Websocket = MISSING
        self.stats: Optional[Stats] = None

    def __repr__(self) -> str:
        return f'<Pisslink Node: <{self.identifier}>, Region: <{self.region}>, Players: <{len(self._players)}>>'

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def region(self) -> Optional[discord.VoiceRegion]:
        return self._region

    @property
    def identifier(self) -> str:
        return self._identifier

    @property
    def players(self) -> List[Player]:
        return self._players

    @property
    def penalty(self) -> float:
        if self.stats is None:
            return 9e30
        return self.stats.penalty.total

    def is_connected(self) -> bool:
        if self._websocket is MISSING:
            return False
        return self._websocket.is_connected()

    async def _connect(self) -> None:
        self._websocket = Websocket(node=self)
        await self._websocket.connect()

    async def _get_data(self, endpoint: str, params: dict) -> Tuple[Dict[str, Any], aiohttp.ClientResponse]:
        headers = {'Authorization': self._password}
        async with self._websocket.session.get(f'{self._websocket.host}/{endpoint}', headers=headers, params=params) as resp:
            data = await resp.json()
        return data, resp

    async def get_tracks(self, cls: Type[PT], query: str) -> List[PT]:
        data, resp = await self._get_data('loadtracks', {'identifier': query})
        if resp.status != 200:
            raise LavalinkException('Invalid response from Lavalink server.')
        load_type = try_enum(LoadType, data.get('loadType'))
        if load_type is LoadType.load_failed:
            raise LoadTrackError(data)
        if load_type is LoadType.no_matches:
            return []
        if load_type is LoadType.track_loaded:
            track_data = data['tracks'][0]
            return [cls(track_data['track'], track_data['info'])]
        if load_type is not LoadType.search_result:
            raise LavalinkException('Track failed to load.')
        return [cls(track_data['track'], track_data["info"]) for track_data in data['tracks']]

    async def get_playlist(self, cls: Type[PLT], identifier: str) -> Optional[PLT]:
        data, resp = await self._get_data('loadtracks', {'identifier': identifier})
        if resp.status != 200:
            raise LavalinkException('Invalid response from Lavalink server.')
        load_type = try_enum(LoadType, data.get('loadType'))
        if load_type is LoadType.load_failed:
            raise LoadTrackError(data)
        if load_type is LoadType.no_matches:
            return None
        if load_type is not LoadType.playlist_loaded:
            raise LavalinkException('Track failed to load.')
        return cls(data)

    async def build_track(self, cls: Type[PT], identifier: str) -> PT:
        data, resp = await self._get_data('decodetrack', {'track': identifier})
        if resp.status != 200:
            raise BuildTrackError(data)
        return cls(identifier, data)

    def get_player(self, guild: discord.Guild) -> Optional[Player]:
        for player in self.players:
            if player.guild == guild:
                return player
        return None

    async def disconnect(self, *, force: bool = False) -> None:
        for player in self.players:
            await player.disconnect(force=force)
        await self.cleanup()

    async def cleanup(self) -> None:
        try:
            self._websocket.listener.cancel()
        except Exception:
            pass
        try:
            await self._websocket.session.close()
        except Exception:
            pass
        del NodePool._nodes[self._identifier]


class NodePool:

    _nodes: ClassVar[Dict[str, Node]] = {}

    @property
    def nodes(self) -> Dict[str, Node]:
        return self._nodes

    @classmethod
    async def create_node(cls, *, client: discord.Bot, host: str, port: int, password: str, https: bool = False, heartbeat: float = 30, region: Optional[discord.VoiceRegion] = None, identifier: str = MISSING, dumps: Callable[[Any], str] = json.dumps) -> Node:
        if identifier is MISSING:
            identifier = os.urandom(8).hex()
        if identifier in cls._nodes:
            raise NodeOccupied(f'A node with identifier <{identifier}> already exists in this pool.')
        node = Node(
            client=client,
            host=host,
            port=port,
            password=password,
            https=https,
            heartbeat=heartbeat,
            region=region,
            identifier=identifier,
            dumps=dumps,
        )
        cls._nodes[identifier] = node
        await node._connect()
        return node

    @classmethod
    def get_node(cls, *, identifier: str = MISSING, region: discord.VoiceRegion = MISSING) -> Node:
        if not cls._nodes:
            raise ZeroConnectedNodes('There are no connected Nodes on this pool.')
        if identifier is not MISSING:
            try:
                node = cls._nodes[identifier]
            except KeyError:
                raise NoMatchingNode(f'No Node with identifier <{identifier}> exists.')
            else:
                return node
        elif region is not MISSING:
            nodes = [n for n in cls._nodes.values() if n._region is region]
            if not nodes:
                raise ZeroConnectedNodes(f'No Nodes for region <{region}> exist on this pool.')
        else:
            nodes = cls._nodes.values()
        return sorted(nodes, key=lambda n: len(n.players))[0]