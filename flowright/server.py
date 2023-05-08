from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket
from starlette.endpoints import WebSocketEndpoint

from flowright.config import FIFO_POLL_DELAY, RERENDER_DELAY
from flowright.messages import ComponentFlushMessage, IterationStartMessage
from flowright.customization import build_preload

import os
import asyncio
import aiofiles
import sys
import logging
import tempfile
import json
import shutil

from typing import Optional, Any


sys.path.append(os.path.join(os.getcwd()))


CLIENT_HTML_PATH = os.path.join(os.path.dirname(__file__), 'res/client.html')
CLIENT_HTML = None

with open(CLIENT_HTML_PATH, "r") as f:
    CLIENT_HTML = f.read()


async def serve_client(request: Request) -> HTMLResponse:
    return HTMLResponse(CLIENT_HTML)


class ServerHandler(WebSocketEndpoint):
    # Starlette config
    encoding = 'json'

    # useful stuff
    temp_dir: Optional[str] = None
    client_fifo: Optional[str] = None
    server_fifo: Optional[str] = None
    refresh: bool = False
    terminated: bool = False
    client_msg_queue: Optional[asyncio.Queue] = None

    async def on_connect(self, websocket: WebSocket) -> None:
        await websocket.accept()

        # create temp scratch space
        self.temp_dir = tempfile.mkdtemp()
        # create pipes for i/o between server and client
        self.client_fifo = os.path.join(self.temp_dir, 'client')
        self.server_fifo = os.path.join(self.temp_dir, 'server')
        self.client_msg_queue = asyncio.Queue()
        os.mkfifo(self.client_fifo)
        os.mkfifo(self.server_fifo)
        print(f'{self.client_fifo=}')
        print(f'{self.server_fifo=}')

        self.refresh = True
        await self._refresh(websocket, preload_data=build_preload())

        self.python_client_task = asyncio.create_task(self.handle_python_client('test.py'))
        self.client_queue_task = asyncio.create_task(self.handle_client_queue())
        self.server_queue_task = asyncio.create_task(self.handle_server_queue(websocket))

    async def on_receive(self, websocket: WebSocket, data: Any) -> None:
        while self.client_msg_queue is None:
            await asyncio.sleep(FIFO_POLL_DELAY)
        if data.get('kind') == 'ComponentFlushMessage':
            flush_obj = ComponentFlushMessage.parse_obj(data)
            await self.client_msg_queue.put(flush_obj.json())
            self.refresh = True
            await self._refresh(websocket)

    async def on_disconnect(self, websocket: WebSocket, close_code: int) -> None:
        if self.python_client_task is not None:
            await self.terminate_client(websocket)
            await asyncio.shield(asyncio.wait_for(self.python_client_task, 10.0))
            self.client_queue_task.cancel()
            self.server_queue_task.cancel()
        if self.temp_dir is not None:
            shutil.rmtree(self.temp_dir)
            
    async def terminate_client(self, websocket: WebSocket) -> None:
        self.terminated = True
        self.refresh = True
        await self._refresh(websocket)

    async def handle_python_client(self, script_name: str) -> None:
        while self.client_fifo is None or self.server_fifo is None:
            await asyncio.sleep(FIFO_POLL_DELAY)
        env = os.environ.copy()
        env.update({
            'CLIENT_FIFO': self.client_fifo,
            'SERVER_FIFO': self.server_fifo
        })
        p = await asyncio.create_subprocess_shell(f"python3 {script_name}", shell=True, env=env)
        logging.info("Client terminated with return code:", p.returncode)
    
    async def handle_client_queue(self) -> None:
        while self.client_fifo is None or self.client_msg_queue is None:
            await asyncio.sleep(FIFO_POLL_DELAY)
        try:
            async with aiofiles.open(self.client_fifo, 'w') as client:
                while True:
                    msg = await self.client_msg_queue.get()
                    await client.write(f'{msg}\n')
                    await client.flush()
        except BrokenPipeError:
            # client script has finished running, stop task silently
            pass

    async def handle_server_queue(self, websocket: WebSocket) -> None:
        while self.server_fifo is None or self.client_msg_queue is None:
            await asyncio.sleep(FIFO_POLL_DELAY)
        async with aiofiles.open(self.server_fifo, 'r') as server:
            while True:
                msg = (await server.readline()).strip()
                if len(msg) == 0:
                    await asyncio.sleep(FIFO_POLL_DELAY)
                    continue
                obj = json.loads(msg)
                await websocket.send_text(msg)
                if obj.get('kind' == 'IterationCompleteMessage'):
                    await self._refresh(websocket)

    async def _refresh(self, websocket: WebSocket, preload_data: str = '') -> None:
        if self.client_msg_queue is None:
            raise RuntimeError("Unable to handle message")
        while not self.refresh:
            await asyncio.sleep(FIFO_POLL_DELAY)
        self.refresh = False
        await asyncio.sleep(RERENDER_DELAY)
        start_msg = IterationStartMessage(terminated=self.terminated, preload_data=preload_data)
        await self.client_msg_queue.put(start_msg.json())
        if not self.terminated:
            await websocket.send_text(start_msg.json())
        

app = Starlette(debug=True, routes=[
    Route("/", serve_client),
    WebSocketRoute("/ws", ServerHandler)
])