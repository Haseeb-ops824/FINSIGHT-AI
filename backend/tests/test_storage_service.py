import httpx
import pytest

from app.core.config import get_settings
from app.services import storage_service


def test_local_storage_round_trip(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "SUPABASE_URL", "")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "")

    key = storage_service.document_object_key(7, "statement.pdf")
    storage_service.save_object(key, b"document bytes", "application/pdf")

    assert storage_service.read_object(key) == b"document bytes"
    storage_service.delete_object(key)
    with pytest.raises(FileNotFoundError):
        storage_service.read_object(key)


def test_local_storage_rejects_parent_traversal(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    with pytest.raises(ValueError, match="Invalid storage object key"):
        storage_service.save_object("../outside.txt", b"no", "text/plain")


def test_remote_storage_upload_uses_private_service_credentials(monkeypatch):
    settings = get_settings()
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://project.supabase.co/")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "server-only-key")
    monkeypatch.setattr(settings, "SUPABASE_STORAGE_BUCKET", "finsight-private")
    captured = {}

    def fake_post(url, headers, content, timeout):
        captured.update(url=url, headers=headers, content=content, timeout=timeout)
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(storage_service.httpx, "post", fake_post)
    storage_service.save_object("user_7/report.pdf", b"pdf bytes", "application/pdf")

    assert captured["url"] == (
        "https://project.supabase.co/storage/v1/object/finsight-private/user_7/report.pdf"
    )
    assert captured["headers"]["Authorization"] == "Bearer server-only-key"
    assert captured["headers"]["apikey"] == "server-only-key"
    assert captured["headers"]["x-upsert"] == "true"
    assert captured["content"] == b"pdf bytes"


def test_remote_private_download_uses_authenticated_route(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "server-only-key")
    monkeypatch.setattr(settings, "SUPABASE_STORAGE_BUCKET", "finsight-private")
    captured = {}

    def fake_get(url, headers, timeout):
        captured.update(url=url, headers=headers, timeout=timeout)
        return httpx.Response(
            200,
            content=b"private document",
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(storage_service.httpx, "get", fake_get)

    assert storage_service.read_object("user_7/statement.pdf") == b"private document"
    assert captured["url"].endswith(
        "/storage/v1/object/authenticated/finsight-private/user_7/statement.pdf"
    )
