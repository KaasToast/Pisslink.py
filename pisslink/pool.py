import discord

from typing import Optional, List

from .player import Player
from .errors import *

class Pool:
    '''
    The pool manages all players in the bot. It is responsible for creating and destroying players as needed.

    If you wish to play Spotify music, you must specify :attr:`spotify_client_id` and :attr:`spotify_client_secret`.

    If you wish to play age restricted music, you must specify :attr:`cookies_path`. This is the path that points to your cookies.txt file. This file needs to contain cookies from an account that can view age restricted content. (https://chrome.google.com/webstore/detail/get-cookiestxt/bgaddhkoddajcdgocldbbfleckgcbcid)

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
            spotify_client_id: Optional[str] = None,
            spotify_client_secret: Optional[str] = None,
            track_conversion_interval: int = 30,
            cookies_path: Optional[str] = None,
            proxies: Optional[List[str]] = None,
            proxy_rotation_interval: int = 600
        ) -> None:
        self.client = client
        self.spotify_client_id = spotify_client_id
        self.spotify_client_secret = spotify_client_secret
        self.track_conversion_interval = track_conversion_interval
        self.cookies_path = cookies_path
        self.proxies = proxies
        self.proxy_rotation_interval = proxy_rotation_interval
        self._sessions = {}
        client.add_listener(self._destroy_player, 'on_player_destroy')

    def get_player(self, guild: discord.Guild) -> Player:
        '''
        Gets the player associated with specified guild. If no player exists, a new one is created.

        Args:
            guild: The :class:`Guild` to get the player for.

        Returns:
            The :class:`Player` associated with the guild.

        Raises:
            InvalidGuild: If the :class:`Guild` is not valid.
        '''
        if guild.id not in self._sessions.keys():
            self._sessions[guild.id] = Player(self.client, self.spotify_client_id, self.spotify_client_secret, self.track_conversion_interval, self.cookies_path, self.proxies, self.proxy_rotation_interval)
        return self._sessions[guild.id]

    async def _destroy_player(self, guild: discord.Guild) -> None:
        '''
        Destroys the player associated with specified guild. This method is automatically called when the player gets disconnected.

        Args:
            guild: The :class:`Guild` to destroy the player for.
        '''
        if guild.id in self._sessions.keys():
            del self._sessions[guild.id]