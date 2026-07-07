"""Shared pytest fixtures, including an in-process live server for e2e tests."""

import socket
import threading
import time
from collections.abc import Iterator

import pytest
import uvicorn

from app.main import app

_STARTUP_TIMEOUT_S = 10.0


def _free_port() -> int:
    """Pick an unused localhost TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def live_server() -> Iterator[str]:
    """Run the FastAPI app on a real port in a thread; yield its base URL.

    uvicorn's ``capture_signals`` already no-ops off the main thread, so the
    server runs safely in this background thread with no extra plumbing.
    """
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + _STARTUP_TIMEOUT_S
        while not server.started:
            if time.monotonic() > deadline:
                msg = "uvicorn server did not start in time"
                raise RuntimeError(msg)
            time.sleep(0.05)
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=_STARTUP_TIMEOUT_S)
