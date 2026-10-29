import uuid
import time
from typing import Dict, Any, Optional
from ..models.mission import ToolExecutionRecord
from .path_guard import SecurityViolation
from .file_ops import (
    read_workspace_file,
    write_workspace_file,
    edit_workspace_file,
    search_workspace_files,
    list_workspace_tree
)
from .terminal import execute_workspace_command
from .git_ops import get_git_diff, get_git_status

class ToolRegistry:
    @staticmethod
    def execute(workspace: str, tool_name: str, arguments: Dict[str, Any]) -> ToolExecutionRecord:
        record_id = f"tool_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        try:
            if tool_name == "read_file":
                rel_path = arguments.get("path")
                s_line = arguments.get("start_line")
                e_line = arguments.get("end_line")
                res = read_workspace_file(workspace, rel_path, s_line, e_line)
                duration_ms = (time.time() - start_time) * 1000
                return ToolExecutionRecord(
                    id=record_id,
                    tool_name=tool_name,
                    input_summary=f"Read {rel_path} (lines {s_line or 1}-{e_line or res['total_lines']})",
                    target_path=rel_path,
                    status="SUCCESS",
                    output=res["content"],
                    duration_ms=round(duration_ms, 2)
                )
                
            elif tool_name == "write_file":
                rel_path = arguments.get("path")
                content = arguments.get("content", "")
                overwrite = arguments.get("overwrite", True)
                res = write_workspace_file(workspace, rel_path, content, overwrite)
                duration_ms = (time.time() - start_time) * 1000
                return ToolExecutionRecord(
                    id=record_id,
                    tool_name=tool_name,
                    input_summary=f"Write {rel_path} ({res['bytes_written']} bytes)",
                    target_path=rel_path,
                    status="SUCCESS",
                    output=f"Successfully wrote {res['bytes_written']} bytes. Verified on disk.",
                    duration_ms=round(duration_ms, 2)
                )
                
            elif tool_name == "edit_file":
                rel_path = arguments.get("path")
                target = arguments.get("target")
                replacement = arguments.get("replacement")
                res = edit_workspace_file(workspace, rel_path, target, replacement)
                duration_ms = (time.time() - start_time) * 1000
                return ToolExecutionRecord(
                    id=record_id,
                    tool_name=tool_name,
                    input_summary=f"Edit {rel_path} ({res['replacements_made']} replacements)",
                    target_path=rel_path,
                    status="SUCCESS",
                    output=f"Successfully modified {rel_path}. Verified on disk.",
                    duration_ms=round(duration_ms, 2)
                )
                
            elif tool_name == "search_files":
                pattern = arguments.get("pattern", "")
                f_pattern = arguments.get("file_pattern", "*")
                matches = search_workspace_files(workspace, pattern, f_pattern)
                duration_ms = (time.time() - start_time) * 1000
                import json
                return ToolExecutionRecord(
                    id=record_id,
                    tool_name=tool_name,
                    input_summary=f"Search '{pattern}' in '{f_pattern}'",
                    status="SUCCESS",
                    output=json.dumps(matches, indent=2),
                    duration_ms=round(duration_ms, 2)
                )
                
            elif tool_name == "list_files":
                subpath = arguments.get("subpath", "")
                tree = list_workspace_tree(workspace)
                duration_ms = (time.time() - start_time) * 1000
                import json
                return ToolExecutionRecord(
                    id=record_id,
                    tool_name=tool_name,
                    input_summary="List workspace directory tree",
                    status="SUCCESS",
                    output=json.dumps(tree[:50], indent=2),
                    duration_ms=round(duration_ms, 2)
                )
                
            elif tool_name == "run_command":
                cmd = arguments.get("command")
                timeout = arguments.get("timeout", 45)
                res = execute_workspace_command(workspace, cmd, timeout)
                duration_ms = res["duration_ms"]
                status = "SUCCESS" if res["exit_code"] == 0 else "FAILED"
                return ToolExecutionRecord(
                    id=record_id,
                    tool_name=tool_name,
                    input_summary=f"Execute: {cmd}",
                    command=cmd,
                    status=status,
                    exit_code=res["exit_code"],
                    output=res["stdout"],
                    error_details=res["stderr"] if res["exit_code"] != 0 else None,
                    duration_ms=round(duration_ms, 2)
                )
                
            elif tool_name == "git_diff":
                diff_text = get_git_diff(workspace)
                duration_ms = (time.time() - start_time) * 1000
                return ToolExecutionRecord(
                    id=record_id,
                    tool_name=tool_name,
                    input_summary="Get Git Diff",
                    status="SUCCESS",
                    output=diff_text,
                    duration_ms=round(duration_ms, 2)
                )
                
            elif tool_name == "git_status":
                status_res = get_git_status(workspace)
                duration_ms = (time.time() - start_time) * 1000
                import json
                return ToolExecutionRecord(
                    id=record_id,
                    tool_name=tool_name,
                    input_summary="Get Git Status",
                    status="SUCCESS",
                    output=json.dumps(status_res, indent=2),
                    duration_ms=round(duration_ms, 2)
                )
                
            else:
                duration_ms = (time.time() - start_time) * 1000
                return ToolExecutionRecord(
                    id=record_id,
                    tool_name=tool_name,
                    input_summary="Unknown tool requested",
                    status="FAILED",
                    error_details=f"Tool '{tool_name}' is not registered.",
                    duration_ms=round(duration_ms, 2)
                )
                
        except SecurityViolation as sv:
            duration_ms = (time.time() - start_time) * 1000
            return ToolExecutionRecord(
                id=record_id,
                tool_name=tool_name,
                input_summary=f"Tool execution blocked: {tool_name}",
                status="BLOCKED",
                blocked_reason=str(sv),
                duration_ms=round(duration_ms, 2)
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ToolExecutionRecord(
                id=record_id,
                tool_name=tool_name,
                input_summary=f"Failed tool execution: {tool_name}",
                status="FAILED",
                error_details=str(e),
                duration_ms=round(duration_ms, 2)
            )
