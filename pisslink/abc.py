from __future__ import annotations

import abc
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    TYPE_CHECKING,
    Type,
    TypeVar,
    Union,
    overload,
)

from .utils import MISSING

if TYPE_CHECKING:
    from .pool import Node

__all__ = (
    "Playable",
    "Searchable",
    "Playlist",
)

ST = TypeVar("ST", bound="Searchable")

class Playable(metaclass=abc.ABCMeta):
    """An ABC that defines the basic structure of a lavalink track resource.

    Attributes
    ----------
    id: str
        The base64 identifier for this object.
    info: Dict[str, Any]
        The raw data supplied by Lavalink.
    length:
        The duration of the track.
    duration:
        Alias to ``length``.
    """

    def __init__(self, id: str, info: Dict[str, Any]):
        self.id: str = id
        self.info: Dict[str, Any] = info
        self.length: float = info.get("length", 0) / 1000
        self.duration: float = self.length

class Searchable(metaclass=abc.ABCMeta):
    @overload
    @classmethod
    @abc.abstractmethod
    async def search(
        cls: Type[ST],
        query: str,
        *,
        node: Node = ...,
        return_first: Literal[True] = ...
    ) -> Optional[ST]:
        ...

    @overload
    @classmethod
    @abc.abstractmethod
    async def search(
        cls: Type[ST],
        query: str,
        *,
        node: Node = ...,
        return_first: Literal[False] = ...
    ) -> List[ST]:
        ...

    @classmethod
    @abc.abstractmethod
    async def search(
        cls: Type[ST], query: str, *, node: Node = MISSING, return_first: bool = False
    ) -> Union[Optional[ST], List[ST]]:
        raise NotImplementedError


class Playlist(metaclass=abc.ABCMeta):
    """An ABC that defines the basic structure of a lavalink playlist resource.

    Attributes
    ----------
    data: Dict[str, Any]
        The raw data supplied by Lavalink.
    """

    def __init__(self, data: Dict[str, Any]):
        self.data: Dict[str, Any] = data