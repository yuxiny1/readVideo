import socket
import unittest
from pathlib import Path
from unittest.mock import patch

from main import BACKEND_DIRECTORY, build_uvicorn_options, find_available_port, is_port_available


class LaunchTest(unittest.TestCase):
    def test_is_port_available_detects_bound_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            sock.listen(1)
            port = sock.getsockname()[1]

            self.assertFalse(is_port_available(port))

    def test_find_available_port_returns_first_open_port(self):
        with patch("main.is_port_available", side_effect=lambda port: port == 8002):
            self.assertEqual(find_available_port(8000, 8003), 8002)

    def test_find_available_port_raises_when_range_is_full(self):
        with patch("main.is_port_available", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "No available ports"):
                find_available_port(8000, 8001)

    def test_reload_only_watches_backend_python_files(self):
        options = build_uvicorn_options(8002)

        self.assertTrue(options["reload"])
        self.assertEqual(options["reload_dirs"], [str(BACKEND_DIRECTORY)])
        self.assertEqual(options["reload_includes"], ["*.py"])
        self.assertEqual(Path(options["reload_dirs"][0]).name, "backend")

    def test_no_reload_omits_watcher_configuration(self):
        options = build_uvicorn_options(8002, reload=False)

        self.assertFalse(options["reload"])
        self.assertNotIn("reload_dirs", options)
        self.assertNotIn("reload_includes", options)


if __name__ == "__main__":
    unittest.main()
