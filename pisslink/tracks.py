from typing import Optional, List

class Playable:
    '''An abstract base class for all playable objects.'''
    pass

class PartialTrack(Playable):
    '''
    A track that only has a title, duration and optionally a url. This track is used to later fetch the full track.

    Args:
        data: The raw data of the track.
    '''

    def __init__(self, data: dict) -> None:
        self.title: str = data['title']
        self.duration: int = data.get('duration', 0) * 1000
        self.url: Optional[str] = data.get('url', None)

class Track(Playable):
    '''
    A track that contains all the data of a track. This track is used to play the track.

    Attributes:
        title: The title of the track.
        identifier: The identifier of the track.
        duration: The duration of the track in milliseconds.
        is_stream: Whether the track is a stream.
        url: The url of the track.
        thumbnail: The thumbnail of the track.
        endpoint: The endpoint of the track.
    '''

    def __init__(self, data: dict) -> None:
        self.title: str = data['title']
        self.identifier: str = data['id']
        self.duration: int = data.get('duration', 0) * 1000
        self.is_stream: bool = data.get('is_live', None) if data.get('is_live', None) else False
        self.url: Optional[str] = f'https://www.youtube.com/watch?v={self.identifier}' if self.identifier and self.identifier != '_playlisttrack' else None
        self.thumbnail: Optional[str] = data.get('thumbnail', None)
        self.endpoint: Optional[str] = data.get('url', None)

class LocalTrack(Playable):
    '''
    A track that is a local file. This track can be played directly and only has a title and a path.

    Attributes:
        title: The title of the track.
        duration: The duration of the track in milliseconds.
        path: The path to the file.
    '''

    def __init__(self, data: dict) -> None:
        self.title: str = data['title']
        self.duration: int = data.get('duration', 0) * 1000
        self.path: str = data['path']

class Playlist:
    '''
    A playlist that contains a list of :class:`PartialTrack` objects and the name of a playlist.

    Attributes:
        title: The name of the playlist.
        tracks: The list of :class:`PartialTrack` objects.
    '''

    def __init__(self, data: dict) -> None:
        self.title: str = data['title']
        self.tracks: List[PartialTrack] = data['tracks']