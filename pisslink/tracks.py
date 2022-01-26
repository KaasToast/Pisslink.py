from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, List, Literal, Optional, Type, TypeVar, Union, overload

from .abc import *
from .pool import Node, NodePool
from .utils import MISSING

__all__ = (
    'Track',
    'PisslinkTrack',
    'PisslinkPlaylist'
)

ST = TypeVar('ST', bound='PisslinkTrack')

class Track(Playable):

    def __init__(self, id: str, info: dict):
        super().__init__(id, info)
        self.title: str = info['title']
        self.identifier: Optional[str] = info.get('identifier')
        self.uri: Optional[str] = info.get('uri')
        self.author: Optional[str] = info.get('author')
        self.duration: Optional[str] = info.get('length')
        self._stream: bool = info.get('isStream')
        self._dead: bool = False

    def __str__(self) -> str:
        return self.title

    def is_stream(self) -> bool:
        return self._stream

    @property
    def thumbnail(self) -> str:
        return f'https://img.youtube.com/vi/{self.identifier}/maxresdefault.jpg'

class PisslinkTrack(Track, Searchable):

    @classmethod
    async def search(cls: Type[ST], query: str, *, node: Node = MISSING, return_first: bool = False) -> Union[Optional[ST], List[ST]]:
        '''Search for tracks with the given query.'''
        if node is MISSING:
            node = NodePool.get_node()
        tracks = await node.get_tracks(cls, f'ytsearch:{query}')
        if return_first:
            return tracks[0]
        return tracks

    @classmethod
    async def get(cls: Type[ST], query: str, *, node: Node = MISSING, return_first: bool = False) -> Union[Optional[ST], List[ST]]:
        '''Gets tracks with the given url.'''
        if node is MISSING:
            node = NodePool.get_node()
        tracks = await node.get_tracks(cls, query)
        if return_first:
            return tracks[0]
        return tracks

    @classmethod
    async def get_playlist(cls: Type[ST], query: str, *, node: Node = MISSING) -> Union[Optional[ST], List[ST]]:
        '''Gets playlist with the given url.'''
        if node is MISSING:
            node = NodePool.get_node()
        tracks = await node.get_playlist(PisslinkPlaylist, query)
        return tracks

class PisslinkPlaylist(Playlist):

    def __init__(self, data: dict):
        self.tracks: List[PisslinkTrack] = []
        self.name: str = data['playlistInfo']['name']
        self.selected_track: Optional[int] = data['playlistInfo'].get('selectedTrack')
        if self.selected_track is not None:
            self.selected_track = int(self.selected_track)
        for track_data in data['tracks']:
            track = PisslinkTrack(track_data['track'], track_data['info'])
            self.tracks.append(track)