"""Start the local API when needed, run the desktop UI, then clean up."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
HEALTH_TIMEOUT = 2.0
STARTUP_TIMEOUT = 20.0


class LaunchError(RuntimeError):
    """Raised when the backend cannot be reused or started."""


def backend_url() -> str:
    load_dotenv(ROOT / ".env")
    return os.getenv("BACKEND_BASE_URL", DEFAULT_BACKEND_URL).rstrip("/")


def health_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/health"


def check_health(
    base_url: str,
    timeout: float = HEALTH_TIMEOUT,
    expected_model: str | None = None,
) -> bool:
    try:
        response = requests.get(health_url(base_url), timeout=timeout)
        body = response.json()
    except (requests.RequestException, ValueError):
        return False
    return (
        response.ok
        and body.get("status") == "ok"
        and bool(body.get("active_model"))
        and (expected_model is None or body.get("active_model") == expected_model)
    )


def _address(base_url: str) -> tuple[str, int]:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise LaunchError(f"BACKEND_BASE_URL이 올바르지 않습니다: {base_url}")
    if parsed.hostname not in LOCAL_HOSTS:
        raise LaunchError(f"원격 백엔드에 연결할 수 없습니다: {base_url}")
    return parsed.hostname, parsed.port or 8000


def start_backend(base_url: str) -> subprocess.Popen:
    host, port = _address(base_url)
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.backend.main:app", "--host", host, "--port", str(port)],
        cwd=ROOT,
        env=os.environ.copy(),
    )


def wait_for_health(base_url: str, process: subprocess.Popen) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise LaunchError(f"백엔드 시작에 실패했습니다. 종료 코드: {process.returncode}")
        if check_health(base_url):
            return
        time.sleep(0.25)
    raise LaunchError(f"백엔드가 {STARTUP_TIMEOUT:.0f}초 안에 준비되지 않았습니다: {base_url}")


def stop_backend(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run() -> int:
    base_url = backend_url()
    owned_process: subprocess.Popen | None = None
    parsed = urlparse(base_url)
    is_local = parsed.hostname in LOCAL_HOSTS
    expected_model = None
    if is_local:
        from src.ml.model_adapter import manifest

        expected_model = manifest()["version"]
    if not check_health(base_url, expected_model=expected_model):
        if not is_local:
            raise LaunchError(f"원격 백엔드가 응답하지 않습니다: {base_url}")
        owned_process = start_backend(base_url)
        wait_for_health(base_url, owned_process)
    try:
        return subprocess.run(
            [sys.executable, "-m", "src.ui"],
            cwd=ROOT,
            env=os.environ.copy(),
            check=False,
        ).returncode
    finally:
        if owned_process is not None:
            stop_backend(owned_process)


def main() -> int:
    try:
        return run()
    except KeyboardInterrupt:
        return 130
    except LaunchError as exc:
        print(f"실행할 수 없습니다: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
