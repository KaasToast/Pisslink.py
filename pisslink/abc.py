from __future__ import annotations

import abc

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, TypeVar, overload

if TYPE_CHECKING:
    from .pool import Node

__all__ = (
    'Playable',
    'Searchable',
    'Playlist'
)

ST = TypeVar('ST', bound='Searchable')

class Playable(metaclass=abc.ABCMeta):
    
    def __init__(self, id: str, info: Dict[str, Any]):
        self.id: str = id
        self.info: Dict[str, Any] = info
        self.length: float = info.get("length", 0) / 1000
        self.duration: float = self.length

class Searchable(metaclass=abc.ABCMeta):
    
    @overload
    @classmethod
    @abc.abstractmethod
    async def search(cls: Type[ST], query: str, *, node: Node = ...) -> Optional[ST]: ...

    @overload
    @classmethod
    @abc.abstractmethod
    async def get(cls: Type[ST], query: str, *, node: Node = ...) -> Optional[ST]: ...

    @overload
    @classmethod
    @abc.abstractmethod
    async def get_playlist(cls: Type[ST], query: str, *, node: Node = ...) -> List[ST]: ...

class Playlist(metaclass=abc.ABCMeta):

    def __init__(self, data: Dict[str, Any]):
        self.data: Dict[str, Any] = data