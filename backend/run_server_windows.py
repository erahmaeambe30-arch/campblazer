"""Windows-friendly multi-process server (gunicorn does not run on Windows).

Uvicorn starts N worker PROCESSES, each serving the ASGI app (REST API +
WebSockets). With more than one worker, Redis is required so WebSocket
events reach users connected to a different worker (set REDIS_URL in .env).

    python run_server_windows.py --workers 4
"""
import argparse
import os

import uvicorn

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--workers", type=int, default=4)
    a = p.parse_args()
    print(f"CampBlazer on http://{a.host}:{a.port} with {a.workers} worker processes")
    uvicorn.run("config.asgi:application", host=a.host, port=a.port, workers=a.workers)
