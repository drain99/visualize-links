# Copyright (c) Indrajit Banerjee
# Licensed under the MIT License.

# when imported within lldb, import succeeds
# when ran as part of visualize-links-ui, simply ignore

try:
    from lldb import SBDebugger

    from .lldb_plugin.commands import (
        SERVER_DICT_KEY,
        visualize_expr,
        visualize_type,
        visualize_diff,
        visualize_history,
    )

    from .lldb_plugin.server import Server

    def __lldb_init_module(debugger: SBDebugger, internal_dict: dict):
        debugger.HandleCommand(
            "command script add --overwrite -f visualize_links.visualize_expr visualize-expr"
        )
        debugger.HandleCommand(
            "command script add --overwrite -f visualize_links.visualize_type visualize-type"
        )
        debugger.HandleCommand(
            "command script add --overwrite -f visualize_links.visualize_diff visualize-diff"
        )
        debugger.HandleCommand(
            "command script add --overwrite -f visualize_links.visualize_history visualize-history"
        )

        if SERVER_DICT_KEY not in internal_dict:
            internal_dict[SERVER_DICT_KEY] = Server()

except ImportError:
    pass
