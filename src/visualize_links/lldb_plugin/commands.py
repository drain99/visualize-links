# Copyright (c) Indrajit Banerjee
# Licensed under the MIT License.

from typing import Iterable

from lldb import (
    SBValue,
    SBDebugger,
    SBCommandReturnObject,
)

from . import lldb_utils as utils
from .graph import GraphBuilder
from .server import Server

SERVER_DICT_KEY = "visualize_links_server"


def visualize_expr(
    debugger: SBDebugger,
    command: str,
    result: SBCommandReturnObject,
    internal_dict: dict,
):
    args = command.strip().split()
    if len(args) != 1:
        result.AppendWarning(
            "visualize-expr requires exactly one argument: an expression!"
        )
        return

    expr_str = args[0]

    frame = utils.get_current_frame(debugger)
    value: SBValue = frame.EvaluateExpression(expr_str)
    assert value.IsValid(), "Failed to evaluate given <expr>"

    builder = GraphBuilder(allowed_types=None)
    builder.extend_from_value(value, {expr_str})
    g = builder.graph()

    server: Server = internal_dict[SERVER_DICT_KEY]

    desc = f"expr: {expr_str}"
    label = utils.get_label_for_frame(frame, desc)
    index = server.publish_new_graph(label, g)

    result.AppendMessage(f"{index}: {label}")


def visualize_type(
    debugger: SBDebugger,
    command: str,
    result: SBCommandReturnObject,
    internal_dict: dict,
):
    args = command.strip().split()
    if len(args) != 1:
        result.AppendWarning("visualize requires exactly one argument: a type name!")
        return

    allowed_types = {args[0]}

    frame = utils.get_current_frame(debugger)

    def filter_fn(value: SBValue) -> bool:
        return (
            value.IsValid()
            and utils.is_pointer_to_type(value.type, allowed_types)
            and utils.is_initialized_in_current_frame(value, frame)
        )

    variables: Iterable[SBValue] = filter(filter_fn, frame.variables)

    builder = GraphBuilder(allowed_types=allowed_types)
    for variable in variables:
        builder.extend_from_value(variable, {variable.name})
    g = builder.graph()

    server: Server = internal_dict[SERVER_DICT_KEY]

    desc = f"type: {args[0]}"
    label = utils.get_label_for_frame(frame, desc)
    index = server.publish_new_graph(label, g)

    result.AppendMessage(f"{index}: {label}")


def visualize_diff(
    debugger: SBDebugger,
    command: str,
    result: SBCommandReturnObject,
    internal_dict: dict,
):
    args = command.strip().split()
    if len(args) != 2:
        result.AppendWarning(
            "visualize-diff requires exactly two arguments: a pair of graph indices!"
        )
        return

    try:
        index1 = int(args[0])
        index2 = int(args[1])
    except ValueError:
        result.AppendWarning(
            "visualize-diff requires exactly two arguments: a pair of graph indices!"
        )
        return

    server: Server = internal_dict[SERVER_DICT_KEY]
    server.publish_diff_graph(index1, index2)


def visualize_history(
    debugger: SBDebugger,
    command: str,
    result: SBCommandReturnObject,
    internal_dict: dict,
):
    server: Server = internal_dict[SERVER_DICT_KEY]

    for index, label in server.history:
        result.AppendMessage(f"{index} {label}")

