from typing import Optional

import lldb
from lldb import (
    SBDebugger,
    SBFrame,
    SBTarget,
    SBProcess,
    SBThread,
    SBValue,
    SBDeclaration,
    SBLineEntry,
    SBFileSpec,
    SBType,
)

from history import HistoryLabel


def get_current_frame(debugger: SBDebugger) -> SBFrame:
    target: SBTarget = debugger.GetSelectedTarget()
    process: SBProcess = target.GetProcess()
    thread: SBThread = process.GetSelectedThread()
    frame: SBFrame = thread.GetSelectedFrame()
    return frame


def is_initialized_in_current_frame(value: SBValue, frame: SBFrame) -> bool:
    decl_pc: SBDeclaration = value.GetDeclaration()
    frame_pc: SBLineEntry = frame.line_entry

    return decl_pc.file == frame_pc.file and frame_pc.line > decl_pc.line


def is_pointer_to_type(type: SBType, allowed_types: Optional[set[str]]) -> bool:
    pointee_type: SBType = type.GetPointeeType()

    return (
        type.is_pointer
        and pointee_type.GetTypeClass() == lldb.eTypeClassStruct
        and (allowed_types is None or pointee_type.name in allowed_types)
    )


def get_label_for_frame(frame: SBFrame) -> HistoryLabel:
    line_entry: SBLineEntry = frame.line_entry
    file_spec: SBFileSpec = line_entry.GetFileSpec()
    # remove argument type signature for now
    func_name: str = frame.GetFunctionName().split("(")[0]

    return HistoryLabel(
        filename=file_spec.basename,
        line=line_entry.line,
        column=line_entry.column,
        function_name=func_name,
    )
