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
HISTORY_DICT_KEY = "visualize-links-history"


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
    g = builder.graph()

    server: Server = internal_dict[SERVER_DICT_KEY]
    server.send_graph(g)


def visualize_type(
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
            and utils.is_pointer_to_type(value.type, allowed_types)
            and utils.is_initialized_in_current_frame(value, frame)
        )

    variables: Iterable[SBValue] = filter(filter_fn, frame.variables)

    builder = GraphBuilder(allowed_types=allowed_types)
    for variable in variables:
        builder.extend_from_value(variable, {variable.name})
    g = builder.graph()

    server: Server = internal_dict[SERVER_DICT_KEY]
    server.send_graph(g)

    history: History = internal_dict[HISTORY_DICT_KEY]
    history.add(HistoryLabel(), g)


def visualize_diff(
    debugger: SBDebugger, command: str, result: SBCommandReturnObject, internal_dict
):
    history: History = internal_dict[HISTORY_DICT_KEY]

    _, g1 = history.at(-2)
    _, g2 = history.at(-1)
    g = g1.difference(g2)

    server: Server = internal_dict[SERVER_DICT_KEY]
    server.send_graph(g)


def __lldb_init_module(debugger: SBDebugger, internal_dict):
    debugger.HandleCommand(
        "command script add --overwrite -f commands.visualize_expr visualize-expr"
    )
    debugger.HandleCommand(
        "command script add --overwrite -f commands.visualize_type visualize"
    )
    debugger.HandleCommand(
        "command script add --overwrite -f commands.visualize_diff visualize-diff"
    )

    if SERVER_DICT_KEY not in internal_dict:
        internal_dict[SERVER_DICT_KEY] = Server()
    if HISTORY_DICT_KEY not in internal_dict:
        internal_dict[HISTORY_DICT_KEY] = History()
