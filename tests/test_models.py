from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from bonfire_client.models import GameSave, ClientConfig, UploadResult


class TestGameSave:
    def test_minimal(self):
        gs = GameSave(game_name="Test", steam_app_id="12345", platform="linux", save_dir=Path("/tmp/saves"), files=[])
        assert gs.game_name == "Test"
        assert gs.steam_app_id == "12345"
        assert gs.platform == "linux"

    def test_defaults(self):
        gs = GameSave(game_name="Test", steam_app_id="", platform="linux", save_dir=Path("/tmp/saves"), files=[])
        assert gs.steam_app_id == ""


class TestClientConfig:
    def test_defaults(self):
        cfg = ClientConfig(server_url="http://localhost", server_port=8080, api_key="test-key")
        assert cfg.compression == "zstd"
        assert cfg.poll_interval == 30
        assert cfg.max_retries == 3

    def test_custom_values(self):
        cfg = ClientConfig(
            server_url="http://example.com",
            server_port=9090,
            api_key="key-123",
            compression="brotli",
            poll_interval=30,
            max_retries=5,
            retry_delay=10,
            machine_id="m1",
        )
        assert cfg.server_url == "http://example.com"
        assert cfg.server_port == 9090
        assert cfg.compression == "brotli"


class TestUploadResult:
    def test_minimal(self):
        ur = UploadResult(status="ok", game_id=42, game_title="Test", generation=3, hash="abc", size_bytes=1000)
        assert ur.status == "ok"
        assert ur.generation == 3
