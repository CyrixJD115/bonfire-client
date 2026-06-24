from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from bonfire_client.archiver import compress_save, decompress_archive


class TestCompressDecompress:
    def test_roundtrip_zstd(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        (source / "save.bin").write_text("save data " * 100)

        archive = tmp_path / "test.bfr"
        digest, size = compress_save(source, archive, method="zstd", compression_level=3)

        assert archive.exists()
        assert size > 0
        assert len(digest) == 64

        extracted = tmp_path / "extracted"
        extracted.mkdir()
        decompress_archive(archive, extracted)

        assert (extracted / "save.bin").exists()
        assert (extracted / "save.bin").read_text() == "save data " * 100

    def test_roundtrip_brotli(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        (source / "data.bin").write_text("brotli test " * 50)

        archive = tmp_path / "test.bfr"
        digest, size = compress_save(source, archive, method="brotli", compression_level=3)

        assert archive.exists()
        assert size > 0
        assert len(digest) == 64

        extracted = tmp_path / "extracted"
        extracted.mkdir()
        decompress_archive(archive, extracted)
        assert (extracted / "data.bin").read_text() == "brotli test " * 50

    def test_hash_matches(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        (source / "f.bin").write_text("content")
        archive = tmp_path / "h.bfr"
        digest, _ = compress_save(source, archive)

        raw = archive.read_bytes()
        expected = hashlib.sha256(raw).hexdigest()
        assert digest == expected

    def test_non_existent_source(self, tmp_path):
        archive = tmp_path / "out.bfr"
        digest, size = compress_save(Path("/nonexistent"), archive)
        assert archive.exists()
        assert size > 0
