from __future__ import annotations

import hashlib
import uuid
from urllib.parse import quote


def hash_archive_token(archive_token: str) -> str:
    return hashlib.sha256(archive_token.encode("utf-8")).hexdigest()


def build_archive_url(
    public_base_url: str | None,
    session_id: uuid.UUID,
    archive_token: str,
) -> str:
    archive_path = f"/archive/{session_id}?token={quote(archive_token, safe='')}"
    if public_base_url is None or public_base_url.strip() == "":
        return archive_path
    return f"{public_base_url.rstrip('/')}{archive_path}"
