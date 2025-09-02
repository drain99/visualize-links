from typing import Optional, Iterable, Literal, TypeAlias, cast
from collections import defaultdict
from dataclasses import dataclass
from pydantic import BaseModel

import lldb
from lldb import (
    SBValue,
    SBTypeMember,
    SBType,
    SBDebugger,
    SBCommandReturnObject,
    SBTarget,
    SBProcess,
    SBThread,
    SBFrame,
    SBValueList,
    SBLineEntry,
    SBDeclaration,
)

from server import start_background, enqueue_message

NodeId: TypeAlias = str


class NodeDesc(BaseModel):
    type: str
    attrs: dict[str, int | float | str]
    tag: Literal["addr", "null"]


class Node(BaseModel):
    id: NodeId
    names: set[str]
    desc: NodeDesc


class LinkDesc(BaseModel):
    accessor: str


class Link(BaseModel):
    source: NodeId
    target: NodeId
    desc: LinkDesc


class Graph(BaseModel):
    nodes: list[Node]
    links: list[Link]


NodeIndex: TypeAlias = int

class ColaNode(BaseModel):
    id: NodeId
    label: str
    tag: Literal["name", "value"]


class ColaLink(BaseModel):
    source: NodeIndex
    target: NodeIndex
    label: str
    tag: Literal["name", "value"]


class ColaGroup(BaseModel):
    leaves: list[NodeIndex]
    links: dict[str, list[NodeIndex]]


class ColaGraph(BaseModel):
    nodes: list[ColaNode]
    links: list[ColaLink]
    groups: list[ColaGroup]


def convert_to_cola(g: Graph) -> ColaGraph:
    cg = ColaGraph(nodes=[], links=[], groups=[])

    node_id2index: dict[NodeId, NodeIndex] = {}

    for node in g.nodes:
        value_node_index = len(node_id2index)
        node_id2index[node.id] = value_node_index
        if node.desc.tag == "addr":
            label = "\n".join(
                f"{attr}: {value}" for attr, value in node.desc.attrs.items()
            )
        else:
            label = "null"

        # add value node
        cg.nodes.append(ColaNode(id=node.id, label=label, tag="value"))

        name_node_indices = []

        for name in node.names:
            name_node_id = f"NAME{name}"
            name_node_index = len(node_id2index)
            node_id2index[name_node_id] = name_node_index

            name_node_indices.append(name_node_index)

            # add name node
            cg.nodes.append(ColaNode(id=name_node_id, label=name, tag="name"))

            # add name link
            cg.links.append(
                ColaLink(
                    source=name_node_index,
                    target=value_node_index,
                    label="",
                    tag="name",
                )
            )

        if len(name_node_indices) >= 1:
            # add name group
            cg.groups.append(
                ColaGroup(leaves=name_node_indices, links={"": [value_node_index]})
            )

    for link in g.links:
        # add value link
        cg.links.append(
            ColaLink(
                source=node_id2index[link.source],
                target=node_id2index[link.target],
                label=link.desc.accessor,
                tag="value",
            )
        )

    return cg


def convert_diff_to_cola(g1: Graph, g2: Graph) -> ColaGraph:
    cg = ColaGraph(nodes=[], links=[], groups=[])

    node_id2index: dict[NodeId, NodeIndex] = {}

    g1_nodes = {node.id: node for node in g1.nodes}
    g2_nodes = {node.id: node for node in g2.nodes}
    all_node_ids = g1_nodes.keys() | g2_nodes.keys()
    for node_id in all_node_ids:
        in_g1 = node_id in g1_nodes
        in_g2 = node_id in g2_nodes
        if in_g1 and not in_g2:
            # only in old
            desc1 = g1_nodes[node_id].desc
            label = "\n".join(
                ["<old>"] + [f"{attr}: {value}" for attr, value in desc1.attrs.items()]
            )
            node_id2index[node_id] = len(cg.nodes)
            cg.nodes.append(ColaNode(id=node_id, label=label, tag="value"))
        elif not in_g1 and in_g2:
            # only in new
            desc2 = g2_nodes[node_id].desc
            label = "\n".join(
                ["<new>"] + [f"{attr}: {value}" for attr, value in desc2.attrs.items()]
            )
            node_id2index[node_id] = len(cg.nodes)
            cg.nodes.append(ColaNode(id=node_id, label=label, tag="value"))
        else:
            # in both old and new, diff between desc
            desc1 = g1_nodes[node_id].desc
            desc2 = g2_nodes[node_id].desc
            # assert desc1.type == desc2.type
            desc = NodeDesc(type=desc1.type, attrs={}, tag="addr")
            all_attrs = desc1.attrs.keys() | desc2.attrs.keys()
            for attr in all_attrs:
                in_desc1 = attr in desc1.attrs
                in_desc2 = attr in desc2.attrs
                if in_desc1 and not in_desc2:
                    # only in old
                    desc.attrs[f"<old> {attr}"] = desc1.attrs[attr]
                elif not in_desc1 and in_desc2:
                    # only in new
                    desc.attrs[f"<new> {attr}"] = desc2.attrs[attr]
                else:
                    # add even if value is same (to help users identify value nodes)
                    if desc1.attrs[attr] != desc2.attrs[attr]:
                        desc.attrs[attr] = f"{desc1.attrs[attr]} -> {desc2.attrs[attr]}"
                    else:
                        desc.attrs[attr] = f"{desc1.attrs[attr]}"
            label = "\n".join(f"{attr}: {value}" for attr, value in desc.attrs.items())
            node_id2index[node_id] = len(cg.nodes)
            cg.nodes.append(ColaNode(id=node_id, label=label, tag="value"))

    g1_links = {(link.source, link.target): link for link in g1.links}
    g2_links = {(link.source, link.target): link for link in g2.links}
    all_link_ids = g1_links.keys() | g2_links.keys()
    for link_id in all_link_ids:
        source, target = link_id
        in_g1 = link_id in g1_links
        in_g2 = link_id in g2_links
        if in_g1 and not in_g2:
            # only in g1
            desc1 = g1_links[link_id].desc
            cg.links.append(
                ColaLink(
                    source=node_id2index[source],
                    target=node_id2index[target],
                    label=f"<old> {desc1.accessor}",
                    tag="value",
                )
            )
        elif not in_g1 and in_g2:
            # only in g2
            desc2 = g2_links[link_id].desc
            cg.links.append(
                ColaLink(
                    source=node_id2index[source],
                    target=node_id2index[target],
                    label=f"<new> {desc2.accessor}",
                    tag="value",
                )
            )
        else:
            desc1 = g1_links[link_id].desc
            desc2 = g2_links[link_id].desc
            # in both g1 and g2, only add if accessor changed
            if desc1.accessor != desc2.accessor:
                cg.links.append(
                    ColaLink(
                        source=node_id2index[source],
                        target=node_id2index[target],
                        label=f"{desc1.accessor} -> {desc2.accessor}",
                        tag="value",
                    )
                )

    g1_names: dict[str, str] = {}
    for node in g1.nodes:
        for name in node.names:
            assert name not in g1_names
            g1_names[name] = node.id
    g2_names: dict[str, str] = {}
    for node in g2.nodes:
        for name in node.names:
            assert name not in g2_names
            g2_names[name] = node.id
    all_names = g1_names.keys() | g2_names.keys()
    for name in all_names:
        in_g1 = name in g1_names
        in_g2 = name in g2_names
        if in_g1 and not in_g2:
            # only in g1
            name_node_index = len(cg.nodes)
            name_node_id = f"NAME{name}"
            node_id2index[name_node_id] = name_node_index
            cg.nodes.append(ColaNode(id=name_node_id, label=name, tag="name"))

            cg.links.append(
                ColaLink(
                    source=name_node_index,
                    target=node_id2index[g1_names[name]],
                    label="<old>",
                    tag="name",
                )
            )
        elif not in_g1 and in_g2:
            # only in g2
            name_node_index = len(cg.nodes)
            name_node_id = f"NAME{name}"
            node_id2index[name_node_id] = name_node_index
            cg.nodes.append(ColaNode(id=name_node_id, label=name, tag="name"))

            cg.links.append(
                ColaLink(
                    source=name_node_index,
                    target=node_id2index[g2_names[name]],
                    label="<new>",
                    tag="name",
                )
            )
        else:
            # in both g1 and g2
            if g1_names[name] != g2_names[name]:
                name_node_index = len(cg.nodes)
                name_node_id = f"NAME{name}"
                node_id2index[name_node_id] = name_node_index
                cg.nodes.append(ColaNode(id=name_node_id, label=name, tag="name"))

                cg.links.append(
                    ColaLink(
                        source=name_node_index,
                        target=node_id2index[g1_names[name]],
                        label="<old>",
                        tag="name",
                    )
                )

                cg.links.append(
                    ColaLink(
                        source=name_node_index,
                        target=node_id2index[g2_names[name]],
                        label="<new>",
                        tag="name",
                    )
                )

    name_adj_list: dict[NodeIndex, dict[str, list[NodeIndex]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for link in cg.links:
        if link.tag == "name":
            name_adj_list[link.source][link.label].append(link.target)

    inv_name_adj_list: dict[
        frozenset[tuple[str, tuple[NodeIndex, ...]]], list[NodeIndex]
    ] = defaultdict(list)
    for source, links in name_adj_list.items():
        frozen_links: frozenset[tuple[str, tuple[NodeIndex, ...]]] = frozenset(
            (label, tuple(targets)) for label, targets in links.items()
        )

        inv_name_adj_list[frozen_links].append(source)

    for links, leaves in inv_name_adj_list.items():
        cg.groups.append(
            ColaGroup(
                leaves=leaves,
                links={label: list(targets) for label, targets in links},
            )
        )

    return cg


class LLDBUtils:
    @staticmethod
    def get_current_frame(debugger: SBDebugger) -> SBFrame:
        target: SBTarget = debugger.GetSelectedTarget()
        process: SBProcess = target.GetProcess()
        thread: SBThread = process.GetSelectedThread()
        frame: SBFrame = thread.GetSelectedFrame()
        return frame

    @staticmethod
    def is_initialized_in_current_frame(value: SBValue, frame: SBFrame):
        decl_pc: SBDeclaration = value.GetDeclaration()
        frame_pc: SBLineEntry = frame.line_entry

        return decl_pc.file == frame_pc.file and frame_pc.line > decl_pc.line

    @staticmethod
    def is_pointer_to_type(type: SBType, allowed_types: Optional[set[str]]):
        pointee_type: SBType = type.GetPointeeType()

        return (
            type.is_pointer
            and pointee_type.GetTypeClass() == lldb.eTypeClassStruct
            and (allowed_types is None or pointee_type.name in allowed_types)
        )


class GraphBuilder:
    def __init__(self, allowed_types: Optional[set[str]]):
        self.allowed_types = allowed_types

        self.graph = Graph(nodes=[], links=[])
        self.addr_to_id: dict[int, str] = dict()
        self.null_counter: int = 0

    def extend_from_value(self, value: SBValue, names: set[str] = set()):
        id = self._dfs(value)

        if id is not None:
            for node in self.graph.nodes:
                if node.id == id:
                    node.names = node.names | names

    def _get_next_null_node_id(self) -> str:
        self.null_counter += 1
        return f"NULLPTR{self.null_counter - 1}"

    def _get_addr_node_id(self, value: SBValue) -> str:
        return f"ADDR{value.unsigned}"

    def _get_addr_node_desc(self, value: SBValue) -> NodeDesc:
        # TODO: for now, only supporting int.
        # support all primitive types & invalid-pointers which can be shown in hex.

        attrs = {}
        fields: list[SBTypeMember] = value.type.GetPointeeType().fields
        for field in fields:
            if field.type.GetBasicType() == lldb.eBasicTypeInt:
                attrs[field.name] = cast(
                    SBValue, value.GetChildMemberWithName(field.name)
                ).signed

        return NodeDesc(
            type=cast(SBType, cast(SBType, value.type).GetPointeeType()).name,
            attrs=attrs,
            tag="addr",
        )

    def _add_node(self, id: str, desc: NodeDesc) -> str:
        node = Node(id=id, names=set(), desc=desc)
        self.graph.nodes.append(node)
        return id

    def _add_null_node(self, value: SBValue) -> str:
        id = self._get_next_null_node_id()
        desc = NodeDesc(
            type=cast(SBType, cast(SBType, value.type).GetPointeeType()).name,
            attrs={},
            tag="null",
        )
        return self._add_node(id, desc)

    def _add_addr_node(self, value: SBValue) -> str:
        id = self._get_addr_node_id(value)
        desc = self._get_addr_node_desc(value)
        return self._add_node(id, desc)

    def _add_link(self, source: str, target: str, accessor: str):
        desc = LinkDesc(accessor=accessor)
        link = Link(source=source, target=target, desc=desc)
        self.graph.links.append(link)

    def _is_valid_type(self, type: SBType) -> bool:
        return LLDBUtils.is_pointer_to_type(type, self.allowed_types)

    def _dfs(
        self, value: SBValue, parent: Optional[tuple[str, str]] = None
    ) -> Optional[str]:
        # invariant: value & parent (if not None) is of type T* where T is one of the whitelisted
        # types being tracked.
        assert value.IsValid() and self._is_valid_type(
            value.type
        ), "Unexpectedly reached an invalid value!"

        addr: int = value.unsigned
        type: SBType = value.type
        struct_type: SBType = type.GetPointeeType()
        fields: list[SBTypeMember] = struct_type.fields

        # special handling for null.
        # use unique nodes to represent each null node to avoid undesired merging.
        if addr == 0:
            # id = self._add_null_node(value)

            # if parent is not None:
            #     parent_id, link_label = parent
            #     self._add_link(parent_id, id, link_label)

            # return id
            return None

        # break if node is already visited but add incoming edge.
        if addr in self.addr_to_id:
            id = self.addr_to_id[addr]

            if parent is not None:
                parent_id, link_label = parent
                self._add_link(parent_id, id, link_label)

            return id

        id = self._add_addr_node(value)
        self.addr_to_id[addr] = id

        if parent is not None:
            parent_id, link_label = parent
            self._add_link(parent_id, id, link_label)

        # recurse for children.
        for field in fields:
            if self._is_valid_type(field.type):
                child_value: SBValue = value.GetChildMemberWithName(field.name)
                self._dfs(child_value, (id, field.name))

        return id


def visualize_expr(
    debugger: SBDebugger, command: str, result: SBCommandReturnObject, internal_dict
):
    expr_str = command.strip()

    target: SBTarget = debugger.GetSelectedTarget()
    process: SBProcess = target.GetProcess()
    thread: SBThread = process.GetSelectedThread()
    frame: SBFrame = thread.GetSelectedFrame()

    value: SBValue = frame.EvaluateExpression(expr_str)
    assert value.IsValid(), "Failed to evaluate given <expr>"

    builder = GraphBuilder(allowed_types=None)
    builder.extend_from_value(value)
    g = builder.graph
    cg = convert_to_cola(g)

    enqueue_message(cg.model_dump_json())


_VISUALIZE_GRAPHS: list[Graph] = []


def visualize(
    debugger: SBDebugger, command: str, result: SBCommandReturnObject, internal_dict
):
    allowed_types = {command.strip()}

    target: SBTarget = debugger.GetSelectedTarget()
    process: SBProcess = target.GetProcess()
    thread: SBThread = process.GetSelectedThread()
    frame: SBFrame = thread.GetSelectedFrame()

    def filter_fn(value: SBValue):
        return (
            value.IsValid()
            and LLDBUtils.is_pointer_to_type(value.type, allowed_types)
            and LLDBUtils.is_initialized_in_current_frame(value, frame)
        )

    variables: Iterable[SBValue] = filter(filter_fn, frame.variables)

    builder = GraphBuilder(allowed_types=allowed_types)
    for variable in variables:
        builder.extend_from_value(variable, {variable.name})
    g = builder.graph
    cg = convert_to_cola(g)

    _VISUALIZE_GRAPHS.append(g)
    enqueue_message(cg.model_dump_json())


def visualize_diff(
    debugger: SBDebugger, command: str, result: SBCommandReturnObject, internal_dict
):
    g1 = _VISUALIZE_GRAPHS[-2]
    g2 = _VISUALIZE_GRAPHS[-1]
    cg = convert_diff_to_cola(g1, g2)

    enqueue_message(cg.model_dump_json())


def __lldb_init_module(debugger: SBDebugger, internal_dict):
    debugger.HandleCommand(
        "command script add --overwrite -f commands.visualize_expr visualize-expr"
    )
    debugger.HandleCommand(
        "command script add --overwrite -f commands.visualize visualize"
    )
    debugger.HandleCommand(
        "command script add --overwrite -f commands.visualize_diff visualize-diff"
    )

    start_background()
