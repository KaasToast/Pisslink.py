from __future__ import annotations

import asyncio
import aiohttp
import pisslink

from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple
from .utils import MISSING

if TYPE_CHECKING:
    from .pool import Node

__all__ = (
    'Websocket'
)

class Websocket:

    def __init__(self, *, node: Node, session: aiohttp.ClientSession = MISSING) -> None:
        self.node: Node = node
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        if session is MISSING:
            session = aiohttp.ClientSession()
        self.session: aiohttp.ClientSession = session
        self.listener: Optional[asyncio.Task] = None
        self.host: str = f'{"https://" if self.node._https else "http://"}{self.node.host}:{self.node.port}'
        self.ws_host: str = f'ws://{self.node.host}:{self.node.port}'

    @property
    def headers(self) -> Dict[str, Any]:
        return {'Authorization': self.node._password, 'User-Id': str(self.node.client.user.id), 'Client-Name': 'Pisslink'}

    def is_connected(self) -> bool:
        return self.websocket is not None and not self.websocket.closed

    async def connect(self) -> None:
        if self.is_connected():
            assert isinstance(self.websocket, aiohttp.ClientWebSocketResponse)
            await self.websocket.close(code=1006, message=b'Pisslink: Attempting reconnection.')
        self.websocket = await self.session.ws_connect(self.ws_host, headers=self.headers, heartbeat=self.node._heartbeat)
        if self.listener is None:
            self.listener = asyncio.create_task(self.listen())
        if self.is_connected():
            self.dispatch('node_ready', self.node)

    async def listen(self) -> None:
        backoff = pisslink.Backoff(base=1, maximum_time=60, maximum_tries=None)
        while True:
            assert isinstance(self.websocket, aiohttp.ClientWebSocketResponse)
            msg = await self.websocket.receive()
            if msg.type is aiohttp.WSMsgType.CLOSED:
                retry = backoff.calculate()
                await asyncio.sleep(retry)
                if not self.is_connected():
                    await self.connect()
            else:
                if msg.data == 1011:
                    self.listener.cancel()
                    return
                asyncio.create_task(self.process_data(msg.json()))

    async def process_data(self, data: Dict[str, Any]) -> None:
        op = data.get('op', None)
        if not op:
            return
        if op == 'stats':
            self.node.stats = pisslink.Stats(self.node, data)
            return
        try:
            player = self.node.get_player(self.node.client.get_guild(int(data['guildId'])))
        except KeyError:
            return
        if player is None:
            return
        if op == 'event':
            event, payload = await self._get_event_payload(data['type'], data)
            if event == 'track_end':
                player._source = None
            self.dispatch(event, player, **payload)
        elif op == 'playerUpdate':
            try:
                await player.update_state(data)
            except KeyError:
                pass

    async def _get_event_payload(self, name: str, data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        event = 'event'
        payload = {}
        if name == 'WebSocketClosedEvent':
            event = 'websocket_closed'
            payload['reason'] = data.get('reason')
            payload['code'] = data.get('code')
        if name.startswith('Track'):
            base64_ = data.get('track')
            track = await self.node.build_track(cls=pisslink.Track, identifier=base64_)
            payload['track'] = track
            if name == 'TrackEndEvent':
                event = 'track_end'
                payload['reason'] = data.get('reason')
            elif name == 'TrackStartEvent':
                event = 'track_start'
            elif name == 'TrackExceptionEvent':
                event = 'track_exception'
                payload['error'] = data.get('error')
            elif name == 'TrackStuckEvent':
                event = 'track_stuck'
                threshold = data.get('thresholdMs')
                if isinstance(threshold, str):
                    payload['threshold'] = int(threshold)
        return event, payload

    def dispatch(self, event, *args: Any, **kwargs: Any) -> None:
        self.node.client.dispatch(f'pisslink_{event}', *args, **kwargs)

    async def send(self, **data: Any) -> None:
        if self.is_connected():
            assert isinstance(self.websocket, aiohttp.ClientWebSocketResponse)
            data_str = self.node._dumps(data)
            if isinstance(data_str, bytes):
                data_str = data_str.decode('utf-8')
            await self.websocket.send_str(data_str)