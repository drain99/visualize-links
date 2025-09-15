from typing import Optional

from pydantic import BaseModel
import json
import asyncio
from threading import Thread
from queue import Queue
import websockets.server as wss

import model as M
from cola_graph import convert_to_cola
from history import History, HistoryLabel
import served_model as S


class Server:
    def __init__(self):
        self.history = History()
        self.queue: Queue[str] = Queue()
        self.client = None
        self.t = Thread(target=self._run_server_loop, daemon=True)
        self.t.start()

    def publish_new_graph(self, label: HistoryLabel, g: M.Graph) -> int:
        cg = convert_to_cola(g)
        index = self.history.add(label, g, cg)

        history = list(
            S.ServedHistoryItem(index=index, label=label)
            for index, label in self.history
        )
        data = S.ServedGraph(title=f"#{index}", graph=cg, history=history)

        self.queue.put(data.model_dump_json())
        return index

    def publish_diff_graph(self, index1: int, index2: int) -> None:
        g1 = self.history.at(index1).graph
        g2 = self.history.at(index2).graph

        data = S.ServedGraph(
            title=f"diff #{index1}-#{index2}", graph=convert_to_cola(g1.difference(g2))
        )

        self.queue.put(data.model_dump_json())

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
                        history = list(
                            S.ServedHistoryItem(index=index, label=label)
                            for index, label in self.history
                        )
                        data = S.ServedHistory(history=history)
                        await self.client.send(data.model_dump_json())
                    elif data["type"] == "graph":
                        index: int = data["index"]
                        data = S.ServedGraph(
                            title=f"#{index}", graph=self.history.at(index).cola_graph
                        )
                        await self.client.send(data.model_dump_json())
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
