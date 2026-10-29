import os
import json
from typing import Dict, Any, List, Optional
from .base import BaseAgent
from ..models.mission import Mission, MissionStatus, PlannedTask
from ..core.state_manager import mission_state_manager

class SamuraiDeveloper(BaseAgent):
    def __init__(self):
        super().__init__(
            name="samurai",
            role="Software Engineer & Master Craftsman",
            title="Disciplined Developer of Context-Aware Code"
        )

    def execute_development(
        self,
        mission: Mission,
        repair_context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        task_id = mission.task_id
        workspace = mission.workspace_path

        if repair_context:
            self.dispatch_event(
                task_id=task_id,
                recipient="sentinel",
                event_type="repair_initiated",
                content=f"Samurai received defect evidence: {repair_context.get('summary', 'Repair requested')}. Initiating targeted patch.",
                evidence=repair_context.get("diagnostic_details")
            )
        else:
            self.dispatch_event(
                task_id=task_id,
                recipient="orchestrator",
                event_type="development_start",
                content=f"Samurai beginning context search and implementation for: '{mission.user_request}'"
            )

        changed_files: List[str] = []

        # Determine target repository context
        # 1. Search existing files for relevant tokens in user request
        keywords = [w.strip(".,;:\"'?") for w in mission.user_request.split() if len(w) > 3]
        target_files = []
        for kw in keywords[:4]:
            search_record = self.call_tool(
                task_id=task_id,
                workspace=workspace,
                tool_name="search_files",
                arguments={"pattern": kw}
            )
            try:
                matches = json.loads(search_record.output)
                for m in matches:
                    if m["file"] not in target_files and not m["file"].endswith((".json", ".md")):
                        target_files.append(m["file"])
            except Exception:
                pass

        # If no specific files found through keyword search, look at existing python files
        if not target_files:
            list_res = self.call_tool(task_id=task_id, workspace=workspace, tool_name="list_files", arguments={})
            try:
                tree = json.loads(list_res.output)
                target_files = [item["path"] for item in tree if item["path"].endswith(".py") and not item["is_dir"] and not item["path"].startswith("test")]
            except Exception:
                pass

        self.dispatch_event(
            task_id=task_id,
            recipient="orchestrator",
            event_type="context_analysis",
            content=f"Identified potential target files: {target_files or 'None found, constructing new targeted module'}"
        )

        return changed_files

    def apply_patch(
        self,
        mission: Mission,
        target_file: str,
        target_snippet: Optional[str],
        replacement_snippet: str,
        full_content: Optional[str] = None
    ) -> bool:
        task_id = mission.task_id
        workspace = mission.workspace_path

        # 1. Read existing file if it exists
        read_res = self.call_tool(
            task_id=task_id,
            workspace=workspace,
            tool_name="read_file",
            arguments={"path": target_file}
        )

        file_exists = read_res.status == "SUCCESS"

        if file_exists and target_snippet:
            # Context-aware edit
            edit_res = self.call_tool(
                task_id=task_id,
                workspace=workspace,
                tool_name="edit_file",
                arguments={
                    "path": target_file,
                    "target": target_snippet,
                    "replacement": replacement_snippet
                }
            )
            success = edit_res.status == "SUCCESS"
        else:
            # Full write or create
            content_to_write = full_content if full_content is not None else replacement_snippet
            write_res = self.call_tool(
                task_id=task_id,
                workspace=workspace,
                tool_name="write_file",
                arguments={
                    "path": target_file,
                    "content": content_to_write,
                    "overwrite": True
                }
            )
            success = write_res.status == "SUCCESS"

        if success:
            # Capture actual git diff
            diff_record = self.call_tool(
                task_id=task_id,
                workspace=workspace,
                tool_name="git_diff",
                arguments={}
            )
            
            mission_state_manager.update_diff_and_files(
                task_id=task_id,
                diff=diff_record.output,
                changed_files=[target_file]
            )

            self.dispatch_event(
                task_id=task_id,
                recipient="sentinel",
                event_type="code_modified",
                content=f"Samurai successfully modified {target_file}. Verified on disk. Handing off to Sentinel for automated testing.",
                evidence=f"Target File: {target_file}\nVerified filesystem write confirmed."
            )
            return True
        else:
            self.dispatch_event(
                task_id=task_id,
                recipient="orchestrator",
                event_type="modification_failed",
                content=f"Failed to apply modification to {target_file}.",
                evidence=f"File: {target_file}"
            )
            return False
