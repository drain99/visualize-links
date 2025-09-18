# Copyright (c) Indrajit Banerjee
# Licensed under the MIT License.

from typing import Iterator

from pydantic import BaseModel

from . import model as M
from . import cola_model as C


class HistoryLabel(BaseModel):
    filename: str
    line: int
    column: int
    function_name: str
    desc: str


class HistoryItem(BaseModel):
    label: HistoryLabel
    graph: M.Graph
    cola_graph: C.Graph


class History:
    def __init__(self):
        self.h: dict[int, HistoryItem] = {}

    def add(self, label: HistoryLabel, g: M.Graph, cg: C.Graph) -> int:
        index = len(self.h)
        self.h[index] = HistoryItem(label=label, graph=g, cola_graph=cg)
        return index

    def at(self, i: int) -> HistoryItem:
        return self.h[i]

    def __iter__(self) -> Iterator[tuple[int, HistoryLabel]]:
        return iter([(i, item.label) for i, item in reversed(self.h.items())])
