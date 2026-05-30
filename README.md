# O-RAN xApp Simulator

Visual dashboard for configuring, running, and testing xapp simulations.

## Quick Start

On your VM (192.168.68.112):

```bash
cd /home/tanvib/ran-sim/ns-O-RAN/cdot-gui
pip install -e .
python main.py
```

Then open **http://192.168.68.112:8765** in your laptop's browser.

## Project Structure

```
cdot-gui/
├── main.py              # Entry point - run this
├── config.yaml          # All settings (paths, ports, ranges)
├── pyproject.toml       # Python dependencies
├── backend/
│   ├── __init__.py
│   └── server.py        # Web server + WebSocket handler
└── frontend/
    ├── index.html       # Dashboard page
    ├── app.js           # WebSocket client + UI logic
    └── style.css        # Light theme styling
```

## Requirements

- Python 3.12+
- pip install: `aiohttp`, `pyyaml`

## Configuration

Edit `config.yaml` to change:
- Server port (default: 8765)
- Path to scenario-zero.cc
- Docker container name for xApp
- Parameter validation ranges
