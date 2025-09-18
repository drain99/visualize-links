# Copyright (c) Indrajit Banerjee
# Licensed under the MIT License.

from typing import Optional, cast

import lldb
from lldb import SBValue, SBTypeMember, SBType

from . import lldb_utils as utils
from . import model as M


class GraphBuilder:
    def __init__(self, allowed_types: Optional[set[str]]):
        self.allowed_types = allowed_types

        self.nodes: dict[M.NodeId, M.NodeDesc] = dict()
        self.links: dict[M.LinkId, M.LinkDesc] = dict()
        self.addr_to_node: dict[int, M.NodeId] = dict()

    def extend_from_value(self, value: SBValue, names: set[str] = set()):
        root = self._dfs(value)

        if root is not None:
            for name in names:
                self.nodes[root].names[name] = M.NameDesc(diff_type=None)

    def graph(self) -> M.Graph:
        return M.Graph(nodes=self.nodes, links=self.links)

    def _get_addr_node_id(self, value: SBValue) -> M.NodeId:
        return f"ADDR{value.unsigned}"

    def _get_addr_node_desc(self, value: SBValue) -> M.NodeDesc:
        # TODO: for now, only supporting int.
        # support all primitive types & invalid-pointers which can be shown in hex.

        attrs: dict[str, M.AttrValue] = {}
        fields: list[SBTypeMember] = value.type.GetPointeeType().fields
        for field in fields:
            if field.type.GetBasicType() == lldb.eBasicTypeInt:
                attrs[field.name] = M.AttrValue(
                    scalar=cast(
                        SBValue, value.GetChildMemberWithName(field.name)
                    ).signed,
                    diff_type=None,
                    old_scalar=None,
                )

        type_desc = M.TypeDesc(
            name=cast(SBType, cast(SBType, value.type).GetPointeeType()).name
        )

        return M.NodeDesc(type=type_desc, attrs=attrs, names=dict())

    def _add_node(self, value: SBValue) -> M.NodeId:
        id = self._get_addr_node_id(value)
        desc = self._get_addr_node_desc(value)

        assert id not in self.nodes
        self.nodes[id] = desc
        return id

    def _add_link(self, source: M.NodeId, target: M.NodeId, accessor: str):
        link_id = (source, target)
        if link_id in self.links:
            self.links[link_id].accessors[accessor] = M.AccessorDesc(diff_type=None)
        else:
            self.links[link_id] = M.LinkDesc(
                accessors={accessor: M.AccessorDesc(diff_type=None)}
            )

    def _is_valid_type(self, type: SBType) -> bool:
        return utils.is_pointer_to_type(type, self.allowed_types)

    def _dfs(
        self, value: SBValue, parent: Optional[tuple[M.NodeId, str]] = None
    ) -> Optional[M.NodeId]:
        # terminate if we reach an invalid value, invalid type or the null pointer
        if not value.IsValid() or not self._is_valid_type(value.type):
            return None

        addr: int = value.unsigned
        type: SBType = value.type
        struct_type: SBType = type.GetPointeeType()
        fields: list[SBTypeMember] = struct_type.fields

        if addr == 0:
            return None

        # break if node is already visited but add incoming edge.
        if addr in self.addr_to_node:
            node = self.addr_to_node[addr]

            if parent is not None:
                parent_node, link_label = parent
                self._add_link(parent_node, node, link_label)

            return node

        node = self._add_node(value)
        self.addr_to_node[addr] = node

        if parent is not None:
            parent_node, link_label = parent
            self._add_link(parent_node, node, link_label)

        # recurse for children.
        for field in fields:
            if self._is_valid_type(field.type):
                child_value: SBValue = value.GetChildMemberWithName(field.name)
                self._dfs(child_value, (node, field.name))

        return node
