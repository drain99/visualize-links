from typing import Optional, Iterable, Literal, cast

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

import lldb_utils as utils
from graph import GraphBuilder
import model as M
from server import Server
from history import HistoryLabel, History

SERVER_DICT_KEY = "visualize-links-server"


def publish_graph(
    g: M.Graph, internal_dict: dict, frame: Optional[SBFrame] = None
) -> Optional[str]:
    label: Optional[HistoryLabel] = None
    if frame is not None:
        line_entry: lldb.SBLineEntry = frame.line_entry
        file_spec: lldb.SBFileSpec = line_entry.GetFileSpec()
        func_name: str = frame.GetFunctionName().split('(')[0]
        label = HistoryLabel(
            filename=file_spec.basename,
            line=line_entry.line,
            column=line_entry.column,
            function_name=func_name,
        )

    server: Server = internal_dict[SERVER_DICT_KEY]
    index = server.publish_graph(g, label)

    return f"{index}: {label}" if index is not None else None


def get_history(internal_dict: dict) -> History:
    server: Server = internal_dict[SERVER_DICT_KEY]
    return server.history


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

    msg = publish_graph(g, internal_dict, frame)
    result.AppendMessage(msg)


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

    msg = publish_graph(g, internal_dict, frame)
    result.AppendMessage(msg)


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
        old = int(args[0])
        new = int(args[1])
    except ValueError:
        result.AppendWarning(
            "visualize-diff requires exactly two arguments: a pair of graph indices!"
        )
        return

    history = get_history(internal_dict)
    _l1, g1 = history.at(old)
    _l2, g2 = history.at(new)
    g = g1.difference(g2)

    publish_graph(g, internal_dict)


def visualize_history(
    debugger: SBDebugger,
    command: str,
    result: SBCommandReturnObject,
    internal_dict: dict,
):
    history = get_history(internal_dict)

    for i, label, _g in history:
        result.AppendMessage(f"{i}: {label}")


def __lldb_init_module(debugger: SBDebugger, internal_dict):
    debugger.HandleCommand(
        "command script add --overwrite -f commands.visualize_expr visualize-expr"
    )
    debugger.HandleCommand(
        "command script add --overwrite -f commands.visualize_type visualize-type"
    )
    debugger.HandleCommand(
        "command script add --overwrite -f commands.visualize_diff visualize-diff"
    )
    debugger.HandleCommand(
        "command script add --overwrite -f commands.visualize_history visualize-history"
    )

    if SERVER_DICT_KEY not in internal_dict:
        internal_dict[SERVER_DICT_KEY] = Server()
