import model as M


class HistoryLabel:
    pass


class History:
    def __init__(self):
        self.h: list[tuple[HistoryLabel, M.Graph]] = []

    def add(self, label: HistoryLabel, g: M.Graph):
        self.h.append((label, g))

    def at(self, i: int) -> tuple[HistoryLabel, M.Graph]:
        return self.h[i]
