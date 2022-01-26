from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from .pool import Node

__all__ = (
    'Penalty',
    'Stats',
)

class Penalty:

    def __init__(self, stats: Stats):
        self.player_penalty: int = stats.playing_players
        self.cpu_penalty: float = 1.05 ** (100 * stats.system_load) * 10 - 10
        self.null_frame_penalty: float = 0
        self.deficit_frame_penalty: float = 0
        if stats.frames_nulled != -1:
            self.null_frame_penalty = (
                1.03 ** (500 * (stats.frames_nulled / 3000))
            ) * 300 - 300
            self.null_frame_penalty *= 2
        if stats.frames_deficit != -1:
            self.deficit_frame_penalty = (
                1.03 ** (500 * (stats.frames_deficit / 3000))
            ) * 600 - 600
        self.total: float = (
            self.player_penalty
            + self.cpu_penalty
            + self.null_frame_penalty
            + self.deficit_frame_penalty
        )

class Stats:

    def __init__(self, node: Node, data: dict[str, Any]):
        self._node: Node = node
        self.uptime: int = data['uptime']
        self.players: int = data['players']
        self.playing_players: int = data['playingPlayers']
        memory: Dict[str, Any] = data['memory']
        self.memory_free: int = memory['free']
        self.memory_used: int = memory['used']
        self.memory_allocated: int = memory['allocated']
        self.memory_reservable: int = memory['reservable']
        cpu: Dict[str, Any] = data['cpu']
        self.cpu_cores: int = cpu['cores']
        self.system_load: float = cpu['systemLoad']
        self.lavalink_load: float = cpu['lavalinkLoad']
        frame_stats: Dict[str, Any] = data.get('frameStats', {})
        self.frames_sent: int = frame_stats.get('sent', -1)
        self.frames_nulled: int = frame_stats.get('nulled', -1)
        self.frames_deficit: int = frame_stats.get('deficit', -1)
        self.penalty = Penalty(self)