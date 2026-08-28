from types import SimpleNamespace
from unittest.mock import patch

import pytest

import run_app


class FakeProcess:
    returncode = None

    def poll(self):
        return self.returncode


def test_run_reuses_healthy_backend():
    with patch("run_app.backend_url", return_value="http://127.0.0.1:8000"), \
        patch("run_app.check_health", return_value=True), \
        patch("run_app.start_backend") as start, \
        patch("run_app.subprocess.run", return_value=SimpleNamespace(returncode=0)) as ui:
        assert run_app.run() == 0

    start.assert_not_called()
    ui.assert_called_once()


def test_check_health_can_reject_a_different_local_model():
    response = SimpleNamespace(
        ok=True,
        json=lambda: {"status": "ok", "active_model": "reviewed-xgb-3.2.0"},
    )
    with patch("run_app.requests.get", return_value=response):
        assert not run_app.check_health("http://127.0.0.1:8000", expected_model="lightgbm-ver2")


def test_run_starts_and_cleans_up_local_backend():
    process = FakeProcess()
    with patch("run_app.backend_url", return_value="http://127.0.0.1:8000"), \
        patch("run_app.check_health", side_effect=[False, True]), \
        patch("run_app.start_backend", return_value=process) as start, \
        patch("run_app.subprocess.run", return_value=SimpleNamespace(returncode=0)), \
        patch("run_app.stop_backend") as stop:
        assert run_app.run() == 0

    start.assert_called_once_with("http://127.0.0.1:8000")
    stop.assert_called_once_with(process)


def test_run_does_not_start_local_process_for_unavailable_remote_backend():
    with patch("run_app.backend_url", return_value="https://api.example.com"), \
        patch("run_app.check_health", return_value=False), \
        patch("run_app.start_backend") as start:
        with pytest.raises(run_app.LaunchError, match="원격 백엔드"):
            run_app.run()

    start.assert_not_called()
