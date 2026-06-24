from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from bonfire_client.config import load_config


class TestLoadConfig:
    def test_load_yaml_config(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("""
server_url: http://localhost
server_port: 8080
api_key: test-key
compression: brotli
poll_interval: 30
""")
        cfg = load_config(str(cfg_file))
        assert cfg.server_url == "http://localhost"
        assert cfg.server_port == 8080
        assert cfg.api_key == "test-key"
        assert cfg.compression == "brotli"
        assert cfg.poll_interval == 30

    def test_load_json_config(self, tmp_path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text('{"server_url":"http://localhost","server_port":8080,"api_key":"test-key","poll_interval":10}')
        cfg = load_config(str(cfg_file))
        assert cfg.server_url == "http://localhost"
        assert cfg.poll_interval == 10

    def test_defaults_for_missing_fields(self, tmp_path):
        cfg_file = tmp_path / "minimal.yaml"
        cfg_file.write_text("server_url: http://localhost\nserver_port: 8080\napi_key: test-key\n")
        cfg = load_config(str(cfg_file))
        assert cfg.max_retries == 3
        assert cfg.retry_delay == 5
