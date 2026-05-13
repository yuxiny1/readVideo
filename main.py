import argparse
import os
import socket

from backend.app import app

DEFAULT_PORT = int(os.environ.get("READVIDEO_PORT", "8000"))
MAX_PORT = 8100


def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def find_available_port(start_port: int = DEFAULT_PORT, max_port: int = MAX_PORT) -> int:
    for port in range(start_port, max_port + 1):
        if is_port_available(port):
            return port
    raise RuntimeError(f"No available ports found between {start_port} and {max_port}")


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="Run the readVideo FastAPI app.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Preferred port to start on")
    args = parser.parse_args()

    port = find_available_port(args.port)
    if port != args.port:
        print(f"Port {args.port} is busy; starting on available port {port} instead.")

    print(f"Starting readVideo on http://127.0.0.1:{port}")
    uvicorn.run("backend.app:app", host="0.0.0.0", port=port, reload=True)
