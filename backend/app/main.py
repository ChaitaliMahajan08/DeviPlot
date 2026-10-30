import os
import json
import queue
import shutil
import threading
from pathlib import Path
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS

from .config import settings, BASE_DIR, FIXTURES_DIR, DATA_DIR
from .models.mission import MissionStatus, VerificationOutcome
from .core.state_manager import mission_state_manager
from .core.event_bus import mission_event_bus
from .core.orchestrator import guild_orchestrator
from .tools.file_ops import list_workspace_tree, read_workspace_file
from .tools.path_guard import validate_workspace_path, SecurityViolation

app = Flask(__name__, static_folder=str(BASE_DIR / "frontend" / "dist"), static_url_path="")
CORS(app)

# Active execution threads
active_mission_threads: dict = {}

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "DevPilot — Mystic Mikado Autonomous Engineering Guild",
        "version": "1.0.0",
        "python_version": os.sys.version.split()[0]
    })

# ----------------- Missions API -----------------

@app.route("/api/missions", methods=["POST"])
def create_mission():
    data = request.get_json() or {}
    user_request = data.get("user_request", "").strip()
    workspace_path = data.get("workspace_path", settings.DEFAULT_WORKSPACE).strip()
    max_retries = int(data.get("max_retries", settings.DEFAULT_MAX_RETRIES))
    
    if not user_request:
        return jsonify({"error": "user_request is required"}), 400

    # Ensure workspace exists
    ws_p = Path(workspace_path)
    if not ws_p.exists():
        ws_p.mkdir(parents=True, exist_ok=True)

    mission = guild_orchestrator.create_mission(
        user_request=user_request,
        workspace_path=str(ws_p.resolve()),
        max_retries=max_retries
    )
    
    # Auto-start if requested
    auto_start = data.get("auto_start", True)
    if auto_start:
        t = threading.Thread(target=guild_orchestrator.execute_mission, args=(mission.task_id,), daemon=True)
        active_mission_threads[mission.task_id] = t
        t.start()

    return jsonify(mission.model_dump()), 201

@app.route("/api/missions", methods=["GET"])
def list_missions():
    missions = mission_state_manager.list_missions()
    return jsonify([m.model_dump() for m in missions])

@app.route("/api/missions/<task_id>", methods=["GET"])
def get_mission(task_id):
    mission = mission_state_manager.get_mission(task_id)
    if not mission:
        return jsonify({"error": f"Mission {task_id} not found"}), 404
    return jsonify(mission.model_dump())

@app.route("/api/missions/<task_id>/start", methods=["POST"])
def start_mission_execution(task_id):
    mission = mission_state_manager.get_mission(task_id)
    if not mission:
        return jsonify({"error": f"Mission {task_id} not found"}), 404

    if task_id in active_mission_threads and active_mission_threads[task_id].is_alive():
        return jsonify({"status": "already_running"}), 200

    t = threading.Thread(target=guild_orchestrator.execute_mission, args=(task_id,), daemon=True)
    active_mission_threads[task_id] = t
    t.start()

    return jsonify({"status": "started", "task_id": task_id})

@app.route("/api/missions/<task_id>/events", methods=["GET"])
def stream_mission_events(task_id):
    mission = mission_state_manager.get_mission(task_id)
    if not mission:
        return jsonify({"error": f"Mission {task_id} not found"}), 404

    def event_stream():
        q = mission_event_bus.subscribe(task_id)
        try:
            # First send initial snapshot
            current_m = mission_state_manager.get_mission(task_id)
            if current_m:
                yield f"data: {json.dumps({'type': 'SNAPSHOT', 'mission': current_m.model_dump()})}\n\n"

            while True:
                try:
                    event = q.get(timeout=20)
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    # Heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'PING'})}\n\n"
        finally:
            mission_event_bus.unsubscribe(task_id, q)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )

@app.route("/api/missions/<task_id>/approvals/<request_id>", methods=["POST"])
def handle_approval(task_id, request_id):
    data = request.get_json() or {}
    approved = bool(data.get("approved", False))
    decided_by = data.get("decided_by", "human_operator")

    try:
        updated_mission = mission_state_manager.submit_approval_decision(
            task_id=task_id,
            request_id=request_id,
            approved=approved,
            decided_by=decided_by
        )
        
        # Resume mission execution if approved
        if approved:
            t = threading.Thread(target=guild_orchestrator.execute_mission, args=(task_id,), daemon=True)
            active_mission_threads[task_id] = t
            t.start()
            
        return jsonify(updated_mission.model_dump())
    except KeyError as e:
        return jsonify({"error": str(e)}), 404

@app.route("/api/missions/<task_id>/cancel", methods=["POST"])
def cancel_mission(task_id):
    mission = mission_state_manager.get_mission(task_id)
    if not mission:
        return jsonify({"error": f"Mission {task_id} not found"}), 404

    mission.status = MissionStatus.CANCELLED
    mission_state_manager.save_mission(mission)
    mission_event_bus.broadcast(task_id, {"type": "STATUS_CHANGE", "status": "CANCELLED"})

    return jsonify({"status": "cancelled", "task_id": task_id})

# ----------------- Workspaces & Fixtures API -----------------

@app.route("/api/workspaces", methods=["GET"])
def list_workspaces():
    fixtures = []
    if FIXTURES_DIR.exists():
        for d in FIXTURES_DIR.iterdir():
            if d.is_dir():
                fixtures.append({
                    "id": d.name,
                    "name": d.name.replace("_", " ").title(),
                    "path": str(d.resolve())
                })
    return jsonify({
        "default_workspace": settings.DEFAULT_WORKSPACE,
        "fixtures": fixtures
    })

@app.route("/api/workspaces/reset-fixture", methods=["POST"])
def reset_fixture():
    data = request.get_json() or {}
    fixture_id = data.get("fixture_id", "scenario_b_bug")
    
    # Destination workspace (under DATA_DIR for reliable writes)
    dest_dir = DATA_DIR / "workspaces" / f"run_{fixture_id}"
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
        
    src_dir = FIXTURES_DIR / fixture_id
    if not src_dir.exists():
        return jsonify({"error": f"Fixture {fixture_id} not found"}), 404

    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_dir, dest_dir)
    return jsonify({
        "status": "reset_success",
        "fixture_id": fixture_id,
        "workspace_path": str(dest_dir.resolve())
    })

@app.route("/api/workspaces/files", methods=["GET"])
def get_workspace_files():
    ws_path = request.args.get("workspace", settings.DEFAULT_WORKSPACE)
    try:
        tree = list_workspace_tree(ws_path)
        return jsonify(tree)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/workspaces/file-content", methods=["GET"])
def get_file_content():
    ws_path = request.args.get("workspace", settings.DEFAULT_WORKSPACE)
    rel_path = request.args.get("path", "")
    try:
        res = read_workspace_file(ws_path, rel_path)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ----------------- Frontend Static Serving -----------------

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    dist_dir = BASE_DIR / "frontend" / "dist"
    if path != "" and (dist_dir / path).exists():
        return send_from_directory(dist_dir, path)
    if (dist_dir / "index.html").exists():
        return send_from_directory(dist_dir, "index.html")
    # If build not present, return informative status
    return jsonify({
        "message": "DevPilot API is running.",
        "endpoints": {
            "health": "/api/health",
            "missions": "/api/missions",
            "workspaces": "/api/workspaces"
        }
    })

if __name__ == "__main__":
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
