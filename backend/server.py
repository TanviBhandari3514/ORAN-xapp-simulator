"""O-RAN xApp Simulator - Web Server

Serves the frontend HTML/CSS/JS and handles WebSocket connections.
"""

import json
import pathlib
from aiohttp import web

# Track connected WebSocket clients
connected_clients: set[web.WebSocketResponse] = set()

# Path to frontend static files
FRONTEND_DIR = pathlib.Path(__file__).parent.parent / "frontend"


async def index_handler(request: web.Request) -> web.FileResponse:
    """Serve the main HTML page."""
    return web.FileResponse(FRONTEND_DIR / "index.html")


async def static_handler(request: web.Request) -> web.FileResponse:
    """Serve static files (JS, CSS)."""
    filename = request.match_info["filename"]
    filepath = FRONTEND_DIR / filename
    if not filepath.exists():
        raise web.HTTPNotFound()
    return web.FileResponse(filepath)


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    """Handle WebSocket connections from the frontend."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    connected_clients.add(ws)
    print(f"  [WS] Client connected. Total: {len(connected_clients)}")

    # Send welcome message
    await ws.send_json({
        "type": "system",
        "message": "Connected to O-RAN xApp Simulator",
        "status": "ready"
    })

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                await handle_command(ws, data)
            elif msg.type == web.WSMsgType.ERROR:
                print(f"  [WS] Error: {ws.exception()}")
    finally:
        connected_clients.discard(ws)
        print(f"  [WS] Client disconnected. Total: {len(connected_clients)}")

    return ws


async def handle_command(ws: web.WebSocketResponse, data: dict) -> None:
    """Route incoming WebSocket commands to appropriate handlers."""
    command = data.get("command")

    if command == "ping":
        await ws.send_json({"type": "pong"})
    elif command == "get_status":
        await ws.send_json({
            "type": "status",
            "simulation": "stopped",
            "connected_clients": len(connected_clients)
        })
    else:
        await ws.send_json({
            "type": "error",
            "message": f"Unknown command: {command}"
        })


def create_app(config: dict) -> web.Application:
    """Create and configure the aiohttp application."""
    app = web.Application()
    app["config"] = config

    # Routes
    app.router.add_get("/", index_handler)
    app.router.add_get("/ws", websocket_handler)
    app.router.add_get("/static/{filename}", static_handler)

    return app


def run_server(app: web.Application, host: str, port: int) -> None:
    """Start the web server."""
    web.run_app(app, host=host, port=port, print=None)
