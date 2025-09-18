# Copyright (c) Indrajit Banerjee
# Licensed under the MIT License.

from pydantic import BaseModel

from . import cola_model as C
from .history import HistoryLabel

class ServedData(BaseModel):
    type: str

class ServedHistoryItem(BaseModel):
  index: int
  label: HistoryLabel

class ServedHistory(ServedData):
    type: str = "history"
    history: list[ServedHistoryItem]


class ServedGraph(ServedData):
    type: str = "graph"
    title: str
    graph: C.Graph
    history: list[ServedHistoryItem] | None = None
