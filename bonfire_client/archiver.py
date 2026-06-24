from __future__ import annotations

import hashlib
import tarfile
import tempfile
from pathlib import Path


def compress_save(
    source_dir: Path,
    output_path: Path,
    method: str = "zstd",
    compression_level: int = 3,
) -> tuple[str, int]:
    tmp_tar = Path(tempfile.mktemp(suffix=".tar"))
    try:
        with tarfile.open(tmp_tar, "w") as tar:
            for entry in sorted(source_dir.rglob("*")):
                if entry.is_file():
                    arcname = str(entry.relative_to(source_dir))
                    tar.add(str(entry), arcname=arcname)

        raw = tmp_tar.read_bytes()

        if method == "brotli":
            import brotli
            compressed = brotli.compress(raw, quality=compression_level)
        else:
            import zstandard
            cctx = zstandard.ZstdCompressor(level=compression_level)
            compressed = cctx.compress(raw)

        digest = hashlib.sha256(compressed).hexdigest()
        output_path.write_bytes(compressed)

        return digest, len(compressed)
    finally:
        if tmp_tar.exists():
            tmp_tar.unlink()


def decompress_archive(archive_path: Path, output_dir: Path) -> None:
    data = archive_path.read_bytes()
    suffix = archive_path.suffix.lower()

    if suffix == ".bfr":
        try:
            import zstandard
            dctx = zstandard.ZstdDecompressor()
            tar_data = dctx.decompress(data)
        except Exception:
            try:
                import brotli
                tar_data = brotli.decompress(data)
            except Exception:
                raise ValueError("Could not decompress .bfr archive (tried zstd, brotli)")
    else:
        raise ValueError(f"Unknown archive format: {suffix}")

    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(tar_data)

    try:
        with tarfile.open(tmp_path, "r") as tar:
            tar.extractall(path=str(output_dir))
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
