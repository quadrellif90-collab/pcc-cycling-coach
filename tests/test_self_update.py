"""Test PCC — endpoint auto-aggiornamento (/api/self-update).

Verifica il flusso senza rete reale (conftest blocca la rete): mockiamo
api_update_check e httpx.AsyncClient. Copre il bug fix del turno precedente
(await su funzione sincrona) e il ramo Windows (installer silenzioso /S).
"""
import sys
import subprocess
from fastapi.testclient import TestClient
import app as app_mod

client = TestClient(app_mod.app)


class _FakeResponse:
    def raise_for_status(self):
        return None

    @property
    def content(self):
        return b"FAKE-INSTALLER-BYTES"


class _FakeAsyncClient:
    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, *a, **k):
        return _FakeResponse()


def test_self_update_no_asset_returns_400(monkeypatch):
    """Senza asset scaricabile: 400 pulito, nessun crash (bug await risolto)."""
    monkeypatch.setattr(
        app_mod, "api_update_check",
        lambda force=0: {"download_url": None, "release_url": "x"},
    )
    r = client.post("/api/self-update", json={})
    assert r.status_code == 400
    assert r.json().get("ok") is False


def test_self_update_windows_launches_installer(monkeypatch):
    """Con asset Win + download finto: lancia PCC-Setup.exe /S (silenzioso)."""
    if sys.platform != "win32":
        import pytest
        pytest.skip("ramo Windows")

    monkeypatch.setattr(
        app_mod, "api_update_check",
        lambda force=0: {
            "download_url": "https://example.com/PCC-Setup-4.0.0.exe",
            "asset_name": "PCC-Setup-4.0.0.exe",
            "release_url": "https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v4.0.0",
        },
    )
    import httpx as _httpx
    monkeypatch.setattr(_httpx, "AsyncClient", _FakeAsyncClient)
    captured = {}
    monkeypatch.setattr(
        subprocess, "Popen",
        lambda args, shell=False: captured.setdefault("args", args) or None,
    )
    r = client.post("/api/self-update", json={})
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert body.get("mode") == "windows-installer"
    # deve aver lanciato l'installer silenzioso con /S
    assert captured.get("args") == [captured["args"][0], "/S"]
