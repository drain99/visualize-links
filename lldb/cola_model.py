from typing import TypeAlias, Literal

from pydantic import BaseModel

import model as M

NodeIndex: TypeAlias = int
Tag: TypeAlias = Literal["name", "value"]


class Node(BaseModel):
    id: M.NodeId
    label: list[str]
    tag: Tag


class Link(BaseModel):
    source: NodeIndex
    target: NodeIndex
    forward_label: list[str]
    backward_label: list[str]
    tag: Tag


class Graph(BaseModel):
    nodes: list[Node]
    links: list[Link]
