from typing import Optional, Tuple
from dataclasses import dataclass

import argparse
from graphviz import Digraph

import lldb
from lldb import (
    SBDebugger,
    SBCommandReturnObject,
    SBTarget,
    SBProcess,
    SBThread,
    SBFrame,
    SBValue,
    SBValueList,
    SBType,
    SBTypeMember,
)


@dataclass
class GraphState:
    graph: Digraph
    addresses: set[int]
    nullCounter: int

    def __init__(self, name: str = "links"):
        self.graph = Digraph(name)
        self.addresses = set()
        self.nullCounter = 0


def extendGraphFromRoot(root: SBValue, graphState: GraphState) -> str:
    def dfs(
        value: SBValue, parent: Optional[Tuple[SBValue, SBTypeMember]] = None
    ) -> str:
        nonlocal graphState

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
            nodeStr = f"NULL{graphState.nullCounter}"
            graphState.graph.node(nodeStr, label="nullptr")
            if parent is not None:
                graphState.graph.edge(
                    f"ADDR{parent[0].GetValueAsUnsigned()}",
                    nodeStr,
                    label=parent[1].GetName(),
                )
            graphState.nullCounter += 1
            return nodeStr

        # if already visited, skip recursion but add the incoming edge
        if addr in graphState.addresses:
            if parent is not None:
                graphState.graph.edge(
                    f"ADDR{parent[0].GetValueAsUnsigned()}",
                    f"ADDR{addr}",
                    label=parent[1].GetName(),
                )
            return f"ADDR{addr}"

        graphState.addresses.add(addr)

        graphState.graph.node(f"ADDR{addr}", label=value.Dereference().__str__())
        if parent is not None:
            graphState.graph.edge(
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

        return f"ADDR{addr}"

    return dfs(root)


def visualize_expr(
    debugger: SBDebugger, command: str, result: SBCommandReturnObject, internal_dict
):
    exprStr = command.strip()
    if len(exprStr) == 0:
        return

    target: SBTarget = debugger.GetSelectedTarget()
    process: SBProcess = target.GetProcess()
    thread: SBThread = process.GetSelectedThread()
    frame: SBFrame = thread.GetSelectedFrame()

    root: SBValue = frame.EvaluateExpression(exprStr)
    graphState = GraphState()
    rootStr = extendGraphFromRoot(root, graphState)

    file = graphState.graph.save()
    print(f"Visualized graph to: {file}")


def visualize(
    debugger: SBDebugger, command: str, result: SBCommandReturnObject, internal_dict
):
    typeStr = command.strip()
    if len(typeStr) == 0:
        return

    target: SBTarget = debugger.GetSelectedTarget()
    process: SBProcess = target.GetProcess()
    thread: SBThread = process.GetSelectedThread()
    frame: SBFrame = thread.GetSelectedFrame()

    variables: SBValueList = frame.variables

    def filterFn(value: SBValue):
        type: SBType = value.GetType()
        structType: SBType = type.GetPointeeType()
        return (
            value.IsValid()
            and type.IsPointerType()
            and structType.GetTypeClass() == lldb.eTypeClassStruct
            and structType.GetName() == typeStr
        )

    variables = list(filter(filterFn, variables))

    graphState = GraphState()
    for rootIndex, variable in enumerate(variables):
        rootStr = extendGraphFromRoot(variable, graphState)
        graphState.graph.node(
            f"ROOT{rootIndex}", label=variable.GetName(), shape="box", style="filled"
        )
        graphState.graph.edge(f"ROOT{rootIndex}", rootStr)

    file = graphState.graph.save()
    print(f"Visualized graph to: {file}")


def __lldb_init_module(debugger: SBDebugger, internal_dict):
    debugger.HandleCommand(
        "command script add --overwrite -f commands.visualize_expr visualize-expr"
    )
    debugger.HandleCommand(
        "command script add --overwrite -f commands.visualize visualize"
    )
    print("Installed visualize-links commands.")
