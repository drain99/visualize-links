from typing import Iterator

from pydantic import BaseModel

import model as M


class HistoryLabel(BaseModel):
    filename: str
    line: int
    column: int
    function_name: str


class History:
    def __init__(self):
        self.h: dict[int, tuple[HistoryLabel, M.Graph]] = {}

    def add(self, label: HistoryLabel, g: M.Graph) -> int:
        index = len(self.h)
        self.h[index] = (label, g)
        return index

    def at(self, i: int) -> tuple[HistoryLabel, M.Graph]:
        return self.h[i]

    def __iter__(self) -> Iterator[tuple[int, HistoryLabel, M.Graph]]:
        return iter([(i, label, g) for i, (label, g) in reversed(self.h.items())])
