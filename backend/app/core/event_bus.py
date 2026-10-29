import json
import queue
import threading
from typing import Dict, List, Any

class MissionEventBus:
    def __init__(self):
        self._lock = threading.Lock()
        self._subscribers: Dict[str, List[queue.Queue]] = {}

    def subscribe(self, task_id: str) -> queue.Queue:
        with self._lock:
            q = queue.Queue(maxsize=200)
            if task_id not in self._subscribers:
                self._subscribers[task_id] = []
            self._subscribers[task_id].append(q)
            return q

    def unsubscribe(self, task_id: str, q: queue.Queue):
        with self._lock:
            if task_id in self._subscribers and q in self._subscribers[task_id]:
                self._subscribers[task_id].remove(q)
                if not self._subscribers[task_id]:
                    del self._subscribers[task_id]

    def broadcast(self, task_id: str, event_data: Dict[str, Any]):
        with self._lock:
            if task_id in self._subscribers:
                dead_queues = []
                for q in self._subscribers[task_id]:
                    try:
                        q.put_nowait(event_data)
                    except queue.Full:
                        dead_queues.append(q)
                for dq in dead_queues:
                    self._subscribers[task_id].remove(dq)

mission_event_bus = MissionEventBus()
