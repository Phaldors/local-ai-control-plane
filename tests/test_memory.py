import httpx

from controlplane import memory


def test_ollama_loaded_mb_sums_the_requested_model(monkeypatch):
    payload = {
        "models": [{"name": "a", "size": 2_000_000_000}, {"name": "b", "size": 1_000_000_000}]
    }
    monkeypatch.setattr(memory.httpx, "get", lambda *a, **k: httpx.Response(200, json=payload))
    assert memory.ollama_loaded_mb(model="a") == 2000.0


def test_ollama_loaded_mb_is_none_when_unreachable(monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(memory.httpx, "get", boom)
    assert memory.ollama_loaded_mb() is None


def test_unknown_runtime_has_no_memory():
    assert memory.runtime_memory_mb("fake", "m") is None
