"""O-RAN xApp Simulator - Web Server

Serves the frontend HTML/CSS/JS and handles WebSocket connections.
"""

import json
import pathlib
import traceback
from aiohttp import web

from backend.simulation import SimulationController

# Track connected WebSocket clients
connected_clients: set[web.WebSocketResponse] = set()

# Path to frontend static files
FRONTEND_DIR = pathlib.Path(__file__).parent.parent / "frontend"

# Simulation controller (initialized in create_app)
sim_controller: SimulationController = None


async def broadcast(message: dict):
    """Send a message to all connected WebSocket clients."""
    print(f"  [BROADCAST] {message.get('type')}: {message}")
    for ws in list(connected_clients):
        try:
            await ws.send_json(message)
        except Exception:
            connected_clients.discard(ws)


async def log_callback(source: str, message: str):
    """Called by SimulationController when a log line is produced."""
    print(f"  [LOG] [{source}] {message}")
    await broadcast({
        "type": "log",
        "entries": [{"source": source, "message": message, "layer": None}]
    })


async def index_handler(request: web.Request) -> web.FileResponse:
    """Serve the main HTML page."""
    print(f"  [HTTP] Serving index.html")
    return web.FileResponse(FRONTEND_DIR / "index.html")


async def static_handler(request: web.Request) -> web.FileResponse:
    """Serve static files (JS, CSS)."""
    filename = request.match_info["filename"]
    filepath = FRONTEND_DIR / filename
    print(f"  [HTTP] Serving static: {filename} (exists: {filepath.exists()})")
    if not filepath.exists():
        raise web.HTTPNotFound()
    return web.FileResponse(filepath)


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    """Handle WebSocket connections from the frontend."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    connected_clients.add(ws)
    print(f"  [WS] Client connected. Total: {len(connected_clients)}")

    # Send welcome message + current status
    await ws.send_json({
        "type": "system",
        "message": "Connected to O-RAN xApp Simulator",
        "status": "ready"
    })
    await ws.send_json(sim_controller.get_status())
    print(f"  [WS] Sent welcome + status to client")

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                print(f"  [WS] Received command: {data}")
                await handle_command(ws, data)
            elif msg.type == web.WSMsgType.ERROR:
                print(f"  [WS] Error: {ws.exception()}")
    except Exception as e:
        print(f"  [WS] Exception in handler: {e}")
        traceback.print_exc()
    finally:
        connected_clients.discard(ws)
        print(f"  [WS] Client disconnected. Total: {len(connected_clients)}")

    return ws


async def handle_command(ws: web.WebSocketResponse, data: dict) -> None:
    """Route incoming WebSocket commands to appropriate handlers."""
    command = data.get("command")
    print(f"  [CMD] Handling command: {command}")

    if command == "ping":
        await ws.send_json({"type": "pong"})

    elif command == "get_status":
        status = sim_controller.get_status()
        print(f"  [CMD] Status: {status}")
        await ws.send_json(status)

    elif command == "start_simulation":
        print(f"  [CMD] Starting simulation...")
        result = await sim_controller.start()
        print(f"  [CMD] Start result: {result}")
        await broadcast(result)

    elif command == "stop_simulation":
        print(f"  [CMD] Stopping simulation...")
        result = await sim_controller.stop()
        print(f"  [CMD] Stop result: {result}")
        await broadcast(result)

    else:
        print(f"  [CMD] Unknown command: {command}")
        await ws.send_json({
            "type": "error",
            "message": f"Unknown command: {command}"
        })


def create_app(config: dict) -> web.Application:
    """Create and configure the aiohttp application."""
    global sim_controller

    app = web.Application()
    app["config"] = config

    # Initialize simulation controller
    sim_controller = SimulationController(config)
    sim_controller.set_log_callback(log_callback)
    print(f"  [INIT] SimulationController created. Container: {config['simulation']['docker_container']}")

    # Routes
    app.router.add_get("/", index_handler)
    app.router.add_get("/ws", websocket_handler)
    app.router.add_get("/static/{{filename}}", static_handler)

    return app


def run_server(app: web.Application, host: str, port: int) -> None:
    """Start the web server."""
    web.run_app(app, host=host, port=port, print=None)
