from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx

from bonfire_client.models import UploadResult

logger = logging.getLogger("bonfire-client.uploader")


async def upload_save(
    server_url: str,
    server_port: int,
    api_key: str,
    archive_path: Path,
    steam_app_id: str = "",
    game_name: str = "",
    platform: str = "",
    machine_id: str = "",
    hash_value: str = "",
    generation: int = 0,
    max_retries: int = 3,
    retry_delay: int = 5,
) -> UploadResult:
    url = f"{server_url.rstrip('/')}:{server_port}/api/v1/saves/upload"
    headers = {"Authorization": f"Bearer {api_key}"}

    data: dict = {}
    if steam_app_id:
        data["steam_app_id"] = steam_app_id
    if game_name:
        data["game_name"] = game_name
    if platform:
        data["platform"] = platform
    if machine_id:
        data["machine_id"] = machine_id
    if hash_value:
        data["hash"] = hash_value
    if generation > 0:
        data["generation"] = str(generation)

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                with archive_path.open("rb") as f:
                    resp = await client.post(
                        url,
                        headers=headers,
                        files={"archive": (archive_path.name, f, "application/octet-stream")},
                        data=data,
                    )
                resp.raise_for_status()
                payload = resp.json()
                return UploadResult(
                    status=payload.get("status", "ok"),
                    game_id=payload.get("game_id", 0),
                    game_title=payload.get("game_title", ""),
                    generation=payload.get("generation", 0),
                    hash=payload.get("hash", ""),
                    size_bytes=payload.get("size_bytes", 0),
                )
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            logger.warning("Upload attempt %d/%d failed: %s", attempt + 1, max_retries, e)
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                raise
