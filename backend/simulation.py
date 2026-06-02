"""O-RAN xApp Simulator - Simulation Controller

Manages the xApp lifecycle via docker exec commands.
"""

import asyncio
import json
from datetime import datetime


class SimulationController:
    """Controls the xApp simulation running inside a Docker container."""

    def __init__(self, config: dict):
        self.container = config["simulation"]["docker_container"]
        self.xapp_script = config["simulation"]["xapp_script"]
        self.shutdown_timeout = config["simulation"]["shutdown_timeout_seconds"]
        self.state = "stopped"  # stopped, starting, running, stopping, error
        self.process = None
        self._log_callback = None

    def set_log_callback(self, callback):
        """Set a callback function that receives log lines: callback(source, message)"""
        self._log_callback = callback

    async def start(self) -> dict:
        """Start the xApp simulation."""
        if self.state in ("running", "starting"):
            return {"type": "status", "simulation": self.state, "message": "Already running"}

        self.state = "starting"

    # verify container exists first ---
    check = await asyncio.create_subprocess_exec(
        "docker", "inspect", "--format={{.State.Running}}", self.container,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await check.communicate()
    if stdout.decode().strip() != "true":
        self.state = "error"
        msg = f"Container '{self.container}' is not running. Run setup-ric-bronze.sh first."
        if self._log_callback:
            await self._log_callback("system", msg)
        return {"type": "status", "simulation": "error", "message": msg}
        
        try:
            # Execute run_xapp.sh inside the Docker container
            self.process = await asyncio.create_subprocess_exec(
                "docker", "exec", "-i", self.container, "bash", self.xapp_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            self.state = "running"

            # Start reading output in background
            asyncio.create_task(self._stream_output())

            # Stream 2: e2term logs
            self.e2term_process = await asyncio.create_subprocess_exec(
                "docker", "logs", "e2term", "-f", "--since=1s",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            asyncio.create_task(self._stream_generic(self.e2term_process, "e2term"))
        
            self.state = "running"
            return {"type": "status", "simulation": "running", "message": "Simulation started"}

        except FileNotFoundError:
            self.state = "error"
            return {"type": "status", "simulation": "error", "message": "Docker not found. Is Docker installed?"}
        except Exception as e:
            self.state = "error"
            return {"type": "status", "simulation": "error", "message": str(e)}

    async def stop(self) -> dict:
        """Stop the xApp simulation."""
        if self.state not in ("running", "starting"):
            return {"type": "status", "simulation": self.state, "message": "Not running"}

        self.state = "stopping"
        try:
            # Send SIGTERM to the process inside the container
            stop_proc = await asyncio.create_subprocess_exec(
                "docker", "exec", self.container, "pkill", "-f", self.xapp_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(stop_proc.wait(), timeout=self.shutdown_timeout)

            # Also terminate our local process handle
            if self.process and self.process.returncode is None:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    self.process.kill()

            self.state = "stopped"
            return {"type": "status", "simulation": "stopped", "message": "Simulation stopped"}

        except asyncio.TimeoutError:
            # Force kill
            if self.process and self.process.returncode is None:
                self.process.kill()
            self.state = "stopped"
            return {"type": "status", "simulation": "stopped", "message": "Force stopped after timeout"}
        except Exception as e:
            self.state = "error"
            return {"type": "status", "simulation": "error", "message": str(e)}

    async def _stream_generic(self, process, source: str):
        """Generic stream reader for any subprocess."""
        if self._log_callback:
            await self._log_callback("system", f"[{source}] stream started")
        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").rstrip()
                if decoded and self._log_callback:
                    await self._log_callback(source, decoded)
        except Exception as e:
            if self._log_callback:
                await self._log_callback("system", f"[{source}] stream error: {e}")

        # Process ended
        if self.state == "running":
            exit_code = self.process.returncode
            self.state = "stopped" if exit_code == 0 else "error"
            if self._log_callback:
                await self._log_callback(
                    "system",
                    f"Simulation process exited with code {exit_code}"
                )

    def get_status(self) -> dict:
        """Return current simulation status."""
        return {"type": "status", "simulation": self.state}
