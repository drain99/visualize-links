from typing import Optional

from pydantic import BaseModel
import json
import asyncio
from threading import Thread
from queue import Queue
import websockets.server as wss

import model as M
import cola_model as C
from cola_graph import convert_to_cola
from history import History, HistoryLabel


class ServerGraph(BaseModel):
    type: str = "graph"
    graph: C.Graph


class ServerHistoryLabel(BaseModel):
    i: int
    label: HistoryLabel


class ServerHistory(BaseModel):
    type: str = "history"
    history: list[ServerHistoryLabel]


class Server:
    def __init__(self):
        self.history = History()
        self.queue = Queue()
        self.client = None
        self.t = Thread(target=self._run_server_loop, daemon=True)
        self.t.start()

    def publish_graph(
        self, g: M.Graph, label: Optional[HistoryLabel] = None
    ) -> Optional[int]:
        history_index: Optional[int] = None
        if label is not None:
            history_index = self.history.add(label, g)
            self.queue.put(self._get_history_json())

        cg = convert_to_cola(g)
        self.queue.put(self._get_graph_json(cg))

        return history_index

    def _get_graph_json(self, cg: C.Graph) -> str:
        sg = ServerGraph(graph=cg)
        return sg.model_dump_json()

    def _get_history_json(self) -> str:
        sh = ServerHistory(
            history=[
                ServerHistoryLabel(i=i, label=label) for i, label, _g in self.history
            ]
        )
        return sh.model_dump_json()

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
            async for message in conn:
                try:
                    data = json.loads(message)
                    if data["type"] == "history":
                        await self.client.send(self._get_history_json())
                except Exception:
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
