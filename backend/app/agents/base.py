import uuid
from typing import Dict, Any, Optional
from ..models.mission import AgentEvent, ToolExecutionRecord
from ..core.state_manager import mission_state_manager
from ..core.event_bus import mission_event_bus
from ..tools.registry import ToolRegistry

class BaseAgent:
    def __init__(self, name: str, role: str, title: str):
        self.name = name
        self.role = role
        self.title = title

    def dispatch_event(
        self,
        task_id: str,
        recipient: str,
        event_type: str,
        content: str,
        evidence: Optional[str] = None,
        next_action: Optional[str] = None
    ) -> AgentEvent:
        event = AgentEvent(
            id=f"evt_{uuid.uuid4().hex[:8]}",
            sender=self.name,
            recipient=recipient,
            event_type=event_type,
            content=content,
            evidence=evidence,
            next_action=next_action
        )
        mission_state_manager.add_agent_event(task_id, event)
        mission_event_bus.broadcast(task_id, {
            "type": "AGENT_EVENT",
            "event": event.model_dump()
        })
        return event

    def call_tool(
        self,
        task_id: str,
        workspace: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> ToolExecutionRecord:
        record = ToolRegistry.execute(workspace, tool_name, arguments)
        mission_state_manager.record_tool_call(task_id, record)
        mission_event_bus.broadcast(task_id, {
            "type": "TOOL_CALL",
            "record": record.model_dump()
        })
        return record
