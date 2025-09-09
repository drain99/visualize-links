from __future__ import annotations

from typing import TypeAlias, Literal
from collections import defaultdict

from pydantic import BaseModel

NodeId: TypeAlias = str
LinkId: TypeAlias = tuple[NodeId, NodeId]
NameDiffType: TypeAlias = Literal["old", "new", "both"]
ValueDiffType: TypeAlias = Literal["old", "new", "both_same", "both_diff"]
AccessorDiffType: TypeAlias = NameDiffType
AttrScalar: TypeAlias = int | float | str


class TypeDesc(BaseModel):
    name: str


class AttrValue(BaseModel):
    scalar: AttrScalar
    diff_type: ValueDiffType | None
    old_scalar: AttrScalar | None

    def attr_value_to_label(self) -> str:
        match self.diff_type:
            case None | "both_same":
                return f"{self.scalar}"
            case "old" | "new" as d:
                return f"{d}: {self.scalar}"
            case "both_diff":
                assert self.old_scalar is not None
                return f"change: {self.old_scalar} -> {self.scalar}"

    def old(self) -> AttrValue:
        assert self.diff_type is None
        assert self.old_scalar is None

        return AttrValue(scalar=self.scalar, diff_type="old", old_scalar=None)

    def new(self) -> AttrValue:
        assert self.diff_type is None
        assert self.old_scalar is None

        return AttrValue(scalar=self.scalar, diff_type="new", old_scalar=None)

    def difference(self, new: AttrValue) -> AttrValue:
        assert self.diff_type is None
        assert self.old_scalar is None

        assert new.diff_type is None
        assert new.old_scalar is None

        if self.scalar == new.scalar:
            return AttrValue(scalar=self.scalar, diff_type="both_same", old_scalar=None)
        else:
            return AttrValue(
                scalar=new.scalar, diff_type="both_diff", old_scalar=self.scalar
            )


class NameDesc(BaseModel):
    diff_type: NameDiffType | None

    def old(self) -> NameDesc:
        assert self.diff_type is None
        return NameDesc(diff_type="old")

    def new(self) -> NameDesc:
        assert self.diff_type is None
        return NameDesc(diff_type="new")

    def difference(self, new: NameDesc):
        assert self.diff_type is None
        assert new.diff_type is None

        return NameDesc(diff_type="both")


class NodeDesc(BaseModel):
    type: TypeDesc
    attrs: dict[str, AttrValue]
    names: dict[str, NameDesc]

    def attrs_to_label(self) -> list[str]:
        l: list[str] = []
        for attr, value in self.attrs.items():
            l.append(f"{attr}: {value.attr_value_to_label()}")

        return l

    def old(self) -> NodeDesc:
        return NodeDesc(
            type=self.type,
            attrs={attr: value.old() for attr, value in self.attrs.items()},
            names={name: desc.old() for name, desc in self.names.items()},
        )

    def new(self) -> NodeDesc:
        return NodeDesc(
            type=self.type,
            attrs={attr: value.new() for attr, value in self.attrs.items()},
            names={name: desc.new() for name, desc in self.names.items()},
        )

    def difference(self, new: NodeDesc) -> NodeDesc:
        assert self.type == new.type

        old_attrs = set(self.attrs.keys())
        new_attrs = set(new.attrs.keys())

        attrs: dict[str, AttrValue] = {}
        for attr in old_attrs - new_attrs:
            attrs[attr] = self.attrs[attr].old()
        for attr in new_attrs - old_attrs:
            attrs[attr] = new.attrs[attr].new()
        for attr in old_attrs & new_attrs:
            attrs[attr] = self.attrs[attr].difference(new.attrs[attr])

        old_names = set(self.names.keys())
        new_names = set(new.names.keys())

        names: dict[str, NameDesc] = {}
        for name in old_names - new_names:
            names[name] = self.names[name].old()
        for name in new_names - old_names:
            names[name] = new.names[name].new()
        for name in old_names & new_names:
            names[name] = self.names[name].difference(new.names[name])

        return NodeDesc(type=self.type, attrs=attrs, names=names)


class AccessorDesc(BaseModel):
    diff_type: AccessorDiffType | None

    def old(self) -> AccessorDesc:
        assert self.diff_type is None
        return AccessorDesc(diff_type="old")

    def new(self) -> AccessorDesc:
        assert self.diff_type is None
        return AccessorDesc(diff_type="new")

    def difference(self, new: AccessorDesc) -> AccessorDesc:
        assert self.diff_type is None
        assert new.diff_type is None

        return AccessorDesc(diff_type="both")


class LinkDesc(BaseModel):
    accessors: dict[str, AccessorDesc]

    def accessors_to_label(self) -> list[str]:
        accessors_condensed: defaultdict[AccessorDiffType | None, list[str]] = (
            defaultdict(list)
        )
        for accessor, desc in self.accessors.items():
            accessors_condensed[desc.diff_type].append(accessor)

        l: list[str] = []
        for diff_type, accessors in accessors_condensed.items():
            match diff_type:
                case None | "both":
                    l.append(",".join(accessors))
                case "old" | "new" as d:
                    l.append(f"{d}: {','.join(accessors)}")

        return l

    def old(self) -> LinkDesc:
        return LinkDesc(
            accessors={
                accessor: desc.old() for accessor, desc in self.accessors.items()
            },
        )

    def new(self) -> LinkDesc:
        return LinkDesc(
            accessors={
                accessor: desc.new() for accessor, desc in self.accessors.items()
            },
        )

    def difference(self, new: LinkDesc) -> LinkDesc:
        old_accessors = set(self.accessors.keys())
        new_accessors = set(new.accessors.keys())

        accessors: dict[str, AccessorDesc] = {}
        for accessor in old_accessors - new_accessors:
            accessors[accessor] = self.accessors[accessor].old()
        for accessor in new_accessors - old_accessors:
            accessors[accessor] = new.accessors[accessor].new()
        for accessor in old_accessors & new_accessors:
            accessors[accessor] = self.accessors[accessor].difference(
                new.accessors[accessor]
            )

        return LinkDesc(accessors=accessors)


class Graph(BaseModel):
    nodes: dict[NodeId, NodeDesc]
    links: dict[LinkId, LinkDesc]

    def difference(self, new: Graph) -> Graph:
        old_nodes = set(self.nodes.keys())
        new_nodes = set(new.nodes.keys())

        nodes: dict[NodeId, NodeDesc] = {}
        for node in old_nodes - new_nodes:
            nodes[node] = self.nodes[node].old()
        for node in new_nodes - old_nodes:
            nodes[node] = new.nodes[node].new()
        for node in old_nodes & new_nodes:
            nodes[node] = self.nodes[node].difference(new.nodes[node])

        old_links = set(self.links.keys())
        new_links = set(new.links.keys())

        links: dict[LinkId, LinkDesc] = {}
        for link in old_links - new_links:
            links[link] = self.links[link].old()
        for link in new_links - old_links:
            links[link] = new.links[link].new()
        for link in old_links & new_links:
            links[link] = self.links[link].difference(new.links[link])

        return Graph(nodes=nodes, links=links)
