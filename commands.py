from typing import Optional, Tuple

import graphviz

import lldb
from lldb import (
    SBDebugger,
    SBCommandReturnObject,
    SBTarget,
    SBProcess,
    SBThread,
    SBFrame,
    SBValue,
    SBType,
    SBTypeMember,
)


def __lldb_init_module(debugger: SBDebugger, internal_dict):
    debugger.HandleCommand(
        "command script add --overwrite -f commands.visualize visualize"
    )
    print("Installed visualize-links commands.")


def visualize(
    debugger: SBDebugger, command: str, result: SBCommandReturnObject, internal_dict
):
    expr = command.strip()
    if len(expr) == 0:
        return

    target: SBTarget = debugger.GetSelectedTarget()
    process: SBProcess = target.GetProcess()
    thread: SBThread = process.GetSelectedThread()
    frame: SBFrame = thread.GetSelectedFrame()

    graph = graphviz.Digraph("links")
    visited: set[int] = set()
    nullCounter: int = 0

    def dfs(value: SBValue, parent: Optional[Tuple[SBValue, SBTypeMember]] = None):
        # invariant: value & parent (if not None) has to be an address ie a pointer type
        # this is true at start by definition and we only recurse for pointer children
        # all non-pointer children are handled inplace
        type: SBType = value.GetType()
        structType: SBType = type.GetPointeeType()
        assert (
            value.IsValid()
            and type.IsPointerType()
            and structType.GetTypeClass() == lldb.eTypeClassStruct
        ), "Unexpectedly reached a value that is not a pointer to a struct!"

        addr: int = value.GetValueAsUnsigned()

        # special handling for null
        # use unique nodes to represent each null node
        # unifying the null node leads to undesired merging of all structures that use the null-terminator
        if addr == 0:
            nonlocal nullCounter
            graph.node(f"NULL{nullCounter}", label="nullptr")
            if parent is not None:
                graph.edge(
                    f"ADDR{parent[0].GetValueAsUnsigned()}",
                    f"NULL{nullCounter}",
                    label=parent[1].GetName(),
                )
            nullCounter += 1
            return

        # if already visited, skip recursion but add the incoming edge
        if addr in visited:
            if parent is not None:
                graph.edge(
                    f"ADDR{parent[0].GetValueAsUnsigned()}",
                    f"ADDR{addr}",
                    label=parent[1].GetName(),
                )
            return

        visited.add(addr)

        graph.node(f"ADDR{addr}", label=value.Dereference().__str__())
        if parent is not None:
            graph.edge(
                f"ADDR{parent[0].GetValueAsUnsigned()}",
                f"ADDR{addr}",
                label=parent[1].GetName(),
            )

        # go over children
        fields: list[SBTypeMember] = structType.fields
        for field in fields:
            field_type: SBType = field.GetType()
            if (
                field_type.IsPointerType()
                and field_type.GetPointeeType().GetTypeClass() == lldb.eTypeClassStruct
            ):
                child_value: SBValue = value.GetChildMemberWithName(field.GetName())
                dfs(
                    child_value,
                    (
                        value,
                        field,
                    ),
                )

    root: SBValue = frame.EvaluateExpression(expr)
    dfs(root)

    file = graph.save()
    print(f"Visualized graph to: {file}")
