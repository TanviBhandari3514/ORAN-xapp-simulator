"""O-RAN xApp Simulator - Entry Point

Run this file to start the application:
    python main.py

Then open http://192.168.68.112:8765 in your browser.
"""

import asyncio
import pathlib
import yaml

from backend.server import create_app, run_server


def load_config() -> dict:
    """Load configuration from config.yaml."""
    config_path = pathlib.Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path) as f:
        return yaml.safe_load(f)


def main():
    config = load_config()
    host = config["server"]["host"]
    port = config["server"]["port"]

    print(f"\n  O-RAN xApp Simulator")
    print(f"  ====================")
    print(f"  Starting on http://{host}:{port}")
    print(f"  Open http://192.168.68.112:{port} in your browser\n")

    app = create_app(config)
    run_server(app, host, port)


if __name__ == "__main__":
    main()
