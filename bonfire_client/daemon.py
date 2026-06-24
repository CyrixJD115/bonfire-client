from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import threading
from collections.abc import Callable
from functools import lru_cache
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

from bonfire_client.config import load_config
from bonfire_client.scanner import run_scan

logger = logging.getLogger("bonfired")

DAEMON_HOST = "127.0.0.1"
DAEMON_PORT = 21466


class BonfireDaemonHandler(BaseHTTPRequestHandler):
    daemon: BonfireDaemon  # type: ignore[override]

    def log_message(self, fmt: str, *args: Any) -> None:
        logger.debug(fmt, *args)

    def _send_json(self, data: Any, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(data, default=_json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, status: int, message: str) -> None:
        self._send_json({"error": message}, status)

    def do_GET(self) -> None:
        match self.path:
            case "/api/health":
                self._handle_health()
            case "/api/scan":
                self._handle_scan()
            case "/api/games":
                self._handle_games()
            case _:
                self._send_error_json(HTTPStatus.NOT_FOUND, "not found")

    def do_POST(self) -> None:
        match self.path:
            case "/api/watch/start":
                self._handle_watch_start()
            case "/api/watch/stop":
                self._handle_watch_stop()
            case "/shutdown":
                self._handle_shutdown()
            case _:
                self._send_error_json(HTTPStatus.NOT_FOUND, "not found")

    def _handle_shutdown(self) -> None:
        self._send_json({"status": "shutting down"})
        threading.Thread(target=self.daemon.stop, daemon=True).start()

    def _handle_health(self) -> None:
        self._send_json({"status": "ok"})

    def _handle_scan(self) -> None:
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(run_scan())
        finally:
            loop.close()
        self.daemon._last_scan = result
        self._send_json(self._scan_result_to_dict(result))

    def _handle_games(self) -> None:
        scan = self.daemon._last_scan
        if scan is None:
            self._send_json({"steam": [], "heroic": []})
            return
        self._send_json(self._scan_result_to_dict(scan))

    def _handle_watch_start(self) -> None:
        self.daemon._watch_active = True
        self._send_json({"status": "watch started"})

    def _handle_watch_stop(self) -> None:
        self.daemon._watch_active = False
        self._send_json({"status": "watch stopped"})

    @staticmethod
    def _scan_result_to_dict(scan: Any) -> dict:
        return {
            "steam": [
                {
                    "game_name": g.game_name,
                    "steam_app_id": g.steam_app_id,
                    "platform": g.platform,
                    "save_dir": str(g.save_dir) if g.save_dir else None,
                    "files": [str(f) for f in g.files],
                    "hash": g.hash,
                }
                for g in scan.steam_games
            ],
            "heroic": [
                {
                    "app_name": g.app_name,
                    "title": g.title,
                    "wine_prefix": str(g.wine_prefix) if g.wine_prefix else None,
                    "platform": g.platform,
                    "cloud_save_folder": g.cloud_save_folder,
                    "cloud_saves_supported": g.cloud_saves_supported,
                    "save_dir": str(g.save_dir) if g.save_dir else None,
                    "files": [str(f) for f in g.files],
                }
                for g in scan.heroic_games
            ],
        }


def _json_default(obj: Any) -> str:
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class BonfireDaemon:
    def __init__(self, host: str = DAEMON_HOST, port: int = DAEMON_PORT) -> None:
        self.host = host
        self.port = port
        self._httpd: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._last_scan: Any = None
        self._watch_active = False

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def run_forever(self) -> None:
        handler = BonfireDaemonHandler
        handler.daemon = self  # type: ignore[attr-defined]
        self._httpd = HTTPServer((self.host, self.port), handler)
        logger.info("Daemon listening on %s:%d", self.host, self.port)
        try:
            self._httpd.serve_forever()
        except KeyboardInterrupt:
            self._httpd.shutdown()

    def start(self) -> None:
        if self.running:
            return
        self._thread = threading.Thread(target=self.run_forever, daemon=True)
        self._thread.start()
        logger.info("Daemon started on %s:%d", self.host, self.port)

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
        self._thread = None
        logger.info("Daemon stopped")


def run_daemon(host: str = DAEMON_HOST, port: int = DAEMON_PORT) -> None:
    daemon = BonfireDaemon(host, port)
    daemon.run_forever()
