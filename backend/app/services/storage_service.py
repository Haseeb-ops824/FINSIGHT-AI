import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator, Optional, Tuple
from urllib.parse import quote

import httpx

from app.core.config import get_settings


def _supabase_config() -> Optional[Tuple[str, str, str]]:
    settings = get_settings()
    url = settings.SUPABASE_URL.strip().rstrip("/")
    key = settings.SUPABASE_SERVICE_ROLE_KEY.strip()
    bucket = settings.SUPABASE_STORAGE_BUCKET.strip()

    if bool(url) != bool(key):
        raise RuntimeError("Set both SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
    if os.environ.get("VERCEL") and not url:
        raise RuntimeError("Configure Supabase Storage before deploying the API on Vercel.")
    if not url:
        return None
    if os.environ.get("VERCEL") and not url.startswith("https://"):
        raise RuntimeError("SUPABASE_URL must use HTTPS on Vercel.")
    if not bucket:
        raise RuntimeError("SUPABASE_STORAGE_BUCKET cannot be empty.")
    return url, key, bucket


def uses_remote_storage() -> bool:
    return _supabase_config() is not None


def document_object_key(user_id: int, filename: str) -> str:
    return f"user_{user_id}/{filename}"


def report_object_key(user_id: int, filename: str) -> str:
    return f"user_{user_id}/reports/{filename}"


def _local_path(key: str) -> Path:
    root = get_settings().upload_path.resolve()
    relative = Path(key)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Invalid storage object key.")
    target = (root / relative).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("Invalid storage object key.") from exc
    return target


def _remote_url(
    config: Tuple[str, str, str],
    key: str,
    authenticated: bool = False,
) -> str:
    url, _, bucket = config
    access_path = "authenticated/" if authenticated else ""
    return (
        f"{url}/storage/v1/object/{access_path}"
        f"{quote(bucket, safe='')}/{quote(key, safe='/')}"
    )


def _remote_headers(config: Tuple[str, str, str]) -> dict[str, str]:
    _, key, _ = config
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def save_object(key: str, content: bytes, content_type: str) -> None:
    config = _supabase_config()
    if config is None:
        path = _local_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return

    headers = _remote_headers(config)
    headers["Content-Type"] = content_type
    headers["x-upsert"] = "true"
    response = httpx.post(
        _remote_url(config, key),
        headers=headers,
        content=content,
        timeout=30.0,
    )
    response.raise_for_status()


def read_object(key: str) -> bytes:
    config = _supabase_config()
    if config is None:
        return _local_path(key).read_bytes()

    response = httpx.get(
        _remote_url(config, key, authenticated=True),
        headers=_remote_headers(config),
        timeout=30.0,
    )
    if response.status_code == 404:
        raise FileNotFoundError(key)
    response.raise_for_status()
    return response.content


def delete_object(key: str) -> None:
    config = _supabase_config()
    if config is None:
        path = _local_path(key)
        if path.exists():
            path.unlink()
        return

    url, _, bucket = config
    response = httpx.request(
        "DELETE",
        f"{url}/storage/v1/object/{quote(bucket, safe='')}",
        headers=_remote_headers(config),
        json={"prefixes": [key]},
        timeout=30.0,
    )
    response.raise_for_status()


@contextmanager
def temporary_file(content: bytes, suffix: str) -> Iterator[Path]:
    with TemporaryDirectory(prefix="finsight-") as directory:
        path = Path(directory) / f"upload{suffix}"
        path.write_bytes(content)
        yield path
