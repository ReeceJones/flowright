from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, FileResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket
from starlette.endpoints import WebSocketEndpoint

from flowright import config
from flowright.messages import ComponentFlushMessage, IterationStartMessage, ConnectionInitiationMessage
from flowright.customization import build_preload

import os
import asyncio
import aiofiles
import sys
import logging
import tempfile
import json
import shutil
import watchfiles
import re

from typing import Optional, Any


sys.path.append(os.path.join(os.getcwd()))


CLIENT_HTML_PATH = os.path.join(os.path.dirname(__file__), 'res/client.html')
CLIENT_HTML = None

with open(CLIENT_HTML_PATH, "r") as f:
    CLIENT_HTML = f.read()


async def serve_client(request: Request) -> HTMLResponse | FileResponse:
    url = request.path_params['url']
    if not re.match(r'^static', url):
        return HTMLResponse(CLIENT_HTML)
    cwd = os.path.join(os.path.abspath(os.path.curdir), 'app')
    static_file = os.path.join(cwd, url)
    if not os.path.exists(static_file) or os.path.commonpath([static_file, cwd]) != cwd:
        print('file does not exist:', static_file)
        return HTMLResponse(status_code=404)
    return FileResponse(static_file)


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

    client_queue_task: Optional[asyncio.Task] = None
    server_queue_task: Optional[asyncio.Task] = None
    python_client_task: Optional[asyncio.Task] = None

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

        if config.AUTO_REFRESH:
            asyncio.create_task(self._refresh_on_timer(websocket, config.AUTO_REFRESH_DELAY))

        self.client_queue_task = asyncio.create_task(self.handle_client_queue())
        self.server_queue_task = asyncio.create_task(self.handle_server_queue(websocket))

    async def on_receive(self, websocket: WebSocket, data: Any) -> None:
        while self.client_msg_queue is None:
            await asyncio.sleep(config.FIFO_POLL_DELAY)
        if data.get('kind') == 'ConnectionInitiationMessage':
            # print(data)
            init_message = ConnectionInitiationMessage.parse_obj(data)
            # cwd = os.path.join(os.path.abspath(os.path.curdir))
            fwd = os.environ['FLOWRIGHT_APP_DIR']
            resource = websocket.path_params.get('url', '/')
            # python_file = os.path.join(fwd, f'{resource}.py' if resource[-1] != '/' else 'index.py')
            python_file = os.path.join(fwd, f'{resource}.py')
            if not os.path.exists(python_file) or os.path.commonpath([python_file, fwd]) != fwd:
                print('file does not exist:', python_file)
                python_file = os.path.join(fwd, f'{resource}', 'index.py')
            
            if not os.path.exists(python_file) or os.path.commonpath([python_file, fwd]) != fwd:
                print('file does not exist:', python_file)
                await websocket.close()
                return
            
            self.python_client_task = asyncio.create_task(self.handle_python_client(python_file, init_message.params))
        elif data.get('kind') == 'ComponentFlushMessage':
            flush_obj = ComponentFlushMessage.parse_obj(data)
            await self.client_msg_queue.put(flush_obj.json())
            if not config.BUFFER_INPUT or flush_obj.force_refresh:
                self.refresh = True
                await self._refresh(websocket)

    async def on_disconnect(self, websocket: WebSocket, close_code: int) -> None:
        if self.python_client_task is not None:
            await self.terminate_client(websocket)
            try:
                await asyncio.wait_for(self.python_client_task, 5.0)
            except TimeoutError:
                self.python_client_task.cancel()
        if self.client_queue_task is not None:
            self.client_queue_task.cancel()
        if self.server_queue_task is not None:
            self.server_queue_task.cancel()
        if self.temp_dir is not None:
            shutil.rmtree(self.temp_dir)
            
    async def terminate_client(self, websocket: WebSocket) -> None:
        self.terminated = True
        self.refresh = True
        await self._refresh(websocket)

    async def detect_changes(self, script_name: str) -> None:
        while self.client_msg_queue is None:
            await asyncio.sleep(config.FIFO_POLL_DELAY)
        
        async for change_set in watchfiles.awatch(script_name, yield_on_timeout=True):
            if len(change_set) > 0:
                break

        if not self.terminated:
            reload_msg = IterationStartMessage(terminated=True, reload=True)
            await self.client_msg_queue.put(reload_msg.json())

    async def handle_python_client(self, script_name: str, params: dict[str, Any]) -> None:
        while self.client_fifo is None or self.server_fifo is None or self.client_msg_queue is None:
            await asyncio.sleep(config.FIFO_POLL_DELAY)

        env = os.environ.copy()
        env.update({
            'CLIENT_FIFO': self.client_fifo,
            'SERVER_FIFO': self.server_fifo,
            'PARAMS': json.dumps(params)
        })
        reload = os.getenv('FLOWRIGHT_RELOAD', 'False') == 'True'
        async with asyncio.TaskGroup() as tg:
            if reload:
                tg.create_task(self.detect_changes(script_name))
            
            python_task = tg.create_task(asyncio.create_subprocess_shell(f"python3 {script_name}", shell=True, env=env, cwd=os.path.dirname(script_name)))
            p = await python_task
            logging.info("Client terminated with return code:", p.returncode)
    
    async def handle_client_queue(self) -> None:
        while self.client_fifo is None or self.client_msg_queue is None or self.python_client_task is None:
            await asyncio.sleep(config.FIFO_POLL_DELAY)
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
        while self.server_fifo is None or self.client_msg_queue is None or self.python_client_task is None:
            await asyncio.sleep(config.FIFO_POLL_DELAY)
        async with aiofiles.open(self.server_fifo, 'r') as server:
            while True:
                msg = (await server.readline()).strip()
                if len(msg) == 0:
                    await asyncio.sleep(config.FIFO_POLL_DELAY)
                    continue
                obj = json.loads(msg)
                await websocket.send_text(msg)
                if obj.get('kind') == 'IterationCompleteMessage':
                    if obj.get('force_refresh', False):
                        self.refresh = True
                        await self._refresh(websocket)

    async def _refresh(self, websocket: WebSocket, preload_data: str = '') -> None:
        if self.client_msg_queue is None:
            raise RuntimeError("Unable to handle message")
        while not self.refresh:
            await asyncio.sleep(config.FIFO_POLL_DELAY)
        self.refresh = False
        await asyncio.sleep(config.RERENDER_DELAY)
        start_msg = IterationStartMessage(terminated=self.terminated, preload_data=preload_data)
        await self.client_msg_queue.put(start_msg.json())
        if not self.terminated:
            await websocket.send_text(start_msg.json())
        
    async def _refresh_on_timer(self, websocket: WebSocket, delay: float) -> None:
        while not self.terminated:
            await asyncio.sleep(delay)
            self.refresh = True
            await self._refresh(websocket)

app = Starlette(debug=True, routes=[
    Route("/{url:path}", serve_client),
    WebSocketRoute("/{url:path}", ServerHandler)
])
