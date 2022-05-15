import random

from typing import Optional, Union, List

from .tracks import Playable, Track, PartialTrack, LocalTrack, Playlist

class Queue:
    '''A queue class stores :class:`Track` objects and has various methods to manipulate them. This class should not be created manually but is an attribute to :class:`Player`.'''

    def __init__(self):
        self.tracks: List[Playable] = []

    @property
    def is_empty(self) -> bool:
        '''
        Shows whether the queue is currently empty.
        
        Returns:
            bool: Whether the queue is currently empty.
        '''
        return len(self.tracks) == 0

    @property
    def next_track(self) -> Optional[Playable]:
        '''
        Gets the upcoming track from the queue.

        Returns:
            :class:`PartialTrack`, :class:`Track` or :class:`LocalTrack`: The upcoming track, if the queue is empty, :class:`None` is returned.
        '''
        return self.tracks[0] if not self.is_empty else None

    @property
    def length(self) -> int:
        '''
        Gets the length of the queue.

        Returns:
            int: The amount of tracks in the queue.
        '''
        return len(self.tracks)

    def add(self, track: Union[Track, LocalTrack, Playlist], top: bool = False) -> None:
        '''
        Adds a track to the queue.

        Args:
            track: The track to add.
            top: Whether to add the track to the top of the queue. Defaults to False.
        '''
        if track:
            if top:
                if isinstance(track, Playlist):
                    for track in reversed(track.tracks):
                        self.tracks.insert(0, track)
                else:
                    self.tracks.insert(0, track)
            else:
                if isinstance(track, Playlist):
                    self.tracks.extend(track.tracks)
                else:
                    self.tracks.append(track)

    def get(self) -> Optional[Playable]:
        '''
        Pops the next track from the queue. This method should not be manually called but is automatically called when the player gets the next track. If you need the upcoming track use :property:`next_track` instead.
        
        Returns:
            :class:`PartialTrack`, :class:`Track` or :class:`LocalTrack`: The next track, if the queue is empty, :class:`None` is returned.
        '''
        return self.tracks.pop(0) if not self.is_empty else None

    def clear(self) -> None:
        '''Clears the queue.'''
        self.tracks.clear()

    def shuffle(self) -> None:
        '''Shuffles the queue.'''
        random.shuffle(self.tracks)

    def duration_until(self, track: Playable) -> int:
        '''
        Gets the duration until the given track is played.

        Args:
            track: The track to get the duration until.

        Returns:
            int: The duration until the given track is played in milliseconds.
        '''
        duration = 0
        for item in self.tracks:
            if item == track:
                break
            duration += item.duration
        return duration