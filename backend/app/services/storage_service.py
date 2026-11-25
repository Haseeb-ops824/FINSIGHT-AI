import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator, Optional, Tuple
from urllib.parse import quote

import httpx

from app.core.config import get_settings


class StorageServiceError(RuntimeError):
    pass


def _raise_for_storage_error(response: httpx.Response) -> None:
    if response.is_success:
        return

    try:
        body = response.json()
    except ValueError:
        body = response.text

    if isinstance(body, dict):
        detail = body.get("message") or body.get("error") or body.get("statusCode")
    else:
        detail = body
    if not detail:
        detail = response.reason_phrase
    raise StorageServiceError(
        f"Supabase Storage returned HTTP {response.status_code}: {str(detail)[:500]}"
    )


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


def create_signed_upload_url(key: str) -> str:
    config = _supabase_config()
    if config is None:
        raise StorageServiceError("Supabase Storage is not configured.")

    url, _, bucket = config
    encoded_bucket = quote(bucket, safe="")
    encoded_key = quote(key, safe="/")
    endpoint = (
        f"{url}/storage/v1/object/upload/sign/"
        f"{encoded_bucket}/{encoded_key}"
    )
    headers = _remote_headers(config)
    headers["x-upsert"] = "true"
    response = httpx.post(endpoint, headers=headers, timeout=15.0)
    _raise_for_storage_error(response)

    try:
        payload = response.json()
    except ValueError as exc:
        raise StorageServiceError("Supabase returned an invalid upload URL response.") from exc

    signed_url = payload.get("url") or payload.get("signedURL") or payload.get("signedUrl")
    if not signed_url and payload.get("token"):
        signed_url = (
            f"/object/upload/sign/{encoded_bucket}/{encoded_key}"
            f"?token={quote(str(payload['token']), safe='')}"
        )
    if not isinstance(signed_url, str) or not signed_url:
        raise StorageServiceError("Supabase did not return a signed upload URL.")
    if signed_url.startswith("https://"):
        return signed_url
    if signed_url.startswith("/storage/v1/"):
        return f"{url}{signed_url}"
    if signed_url.startswith("/"):
        return f"{url}/storage/v1{signed_url}"
    return f"{url}/storage/v1/{signed_url}"


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
    _raise_for_storage_error(response)


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
    _raise_for_storage_error(response)
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
    _raise_for_storage_error(response)


@contextmanager
def temporary_file(content: bytes, suffix: str) -> Iterator[Path]:
    with TemporaryDirectory(prefix="finsight-") as directory:
        path = Path(directory) / f"upload{suffix}"
        path.write_bytes(content)
        yield path
