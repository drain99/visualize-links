import asyncio
from threading import Thread
from queue import Queue
import websockets.server as wss

import model as M
from cola_graph import convert_to_cola


class Server:
    def __init__(self):
        self.queue = Queue()
        self.client = None
        self.t = Thread(target=self._run_server_loop, daemon=True)
        self.t.start()

    def send_graph(self, g: M.Graph):
        cg = convert_to_cola(g)
        cg_str = cg.model_dump_json()
        self.queue.put(cg_str)

    def _run_server_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        server = wss.serve(self._ws_handler, "localhost", 8765)
        loop.run_until_complete(server)
        loop.create_task(self._send_loop())
        loop.run_forever()

    async def _ws_handler(self, conn: wss.WebSocketServerProtocol):
        if self.client is not None:
            await self.client.close()
        self.client = conn

        try:
            async for _ in conn:
                # ignore incoming messages
                pass
        finally:
            if self.client is conn:
                self.client = None

    async def _send_loop(self) -> None:
        loop = asyncio.get_event_loop()
        while True:
            msg = await loop.run_in_executor(None, self.queue.get)
            if self.client is not None:
                try:
                    await self.client.send(msg)
                except Exception:
                    self.client = None
            self.queue.task_done()
