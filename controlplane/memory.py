"""Resident memory of the model server, sampled after a run while the model is loaded.

Ollama reports loaded model sizes through /api/ps. The MLX server is a normal
process, so its RSS is read with `ps`. Both are approximations (unified memory,
Metal buffers) and are reported as such; None means "could not measure".
"""

import subprocess

import httpx


def ollama_loaded_mb(
    base_url: str = "http://localhost:11434", model: str | None = None
) -> float | None:
    try:
        data = httpx.get(f"{base_url}/api/ps", timeout=5).json()
    except (httpx.HTTPError, ValueError):
        return None
    sizes = [m.get("size", 0) for m in data.get("models", []) if model in (None, m.get("name"))]
    return sum(sizes) / 1e6 if sizes else None


def process_rss_mb(pattern: str) -> float | None:
    try:
        pids = subprocess.run(
            ["pgrep", "-f", pattern], capture_output=True, text=True, check=True
        ).stdout.split()
        rss_kb = sum(
            int(
                subprocess.run(
                    ["ps", "-o", "rss=", "-p", pid], capture_output=True, text=True, check=True
                ).stdout.strip()
                or 0
            )
            for pid in pids
        )
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None
    return rss_kb / 1024 if rss_kb else None


def runtime_memory_mb(runtime: str, model: str) -> float | None:
    if runtime == "ollama":
        return ollama_loaded_mb(model=model)
    if runtime == "mlx":
        return process_rss_mb("mlx_lm.server")
    return None
