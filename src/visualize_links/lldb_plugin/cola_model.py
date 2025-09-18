# Copyright (c) Indrajit Banerjee
# Licensed under the MIT License.

from typing import TypeAlias, Literal

from pydantic import BaseModel

from . import model as M

NodeIndex: TypeAlias = int
Tag: TypeAlias = Literal["name", "value"]


class Node(BaseModel):
    id: M.NodeId
    label: list[str]
    tag: Tag


class LinkLabel(BaseModel):
    label: str
    diff_type: M.DiffType


class Link(BaseModel):
    source: NodeIndex
    target: NodeIndex
    forward_labels: list[LinkLabel]
    backward_labels: list[LinkLabel]
    tag: Tag
    diff_type: M.DiffType


class Graph(BaseModel):
    nodes: list[Node]
    links: list[Link]
