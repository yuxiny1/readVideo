import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ContainerPlatformContractTests(unittest.TestCase):
    def test_compose_defines_the_required_services(self):
        compose = (PROJECT_ROOT / "compose.yml").read_text(encoding="utf-8")

        for service in ("frontend", "api", "worker", "postgres", "redis", "ollama", "portainer"):
            self.assertIn(f"  {service}:\n", compose)

    def test_backend_services_share_persistent_output_directories(self):
        compose = (PROJECT_ROOT / "compose.yml").read_text(encoding="utf-8")

        self.assertIn("./downloads:/data/downloads", compose)
        self.assertIn("./notes:/data/notes", compose)
        self.assertIn("READVIDEO_DATABASE_URL", compose)
        self.assertIn("READVIDEO_REDIS_URL", compose)

    def test_container_script_is_executable(self):
        script = PROJECT_ROOT / "scripts" / "containers.sh"

        self.assertTrue(script.stat().st_mode & 0o111)

    def test_host_ollama_override_reuses_native_models(self):
        override = (PROJECT_ROOT / "compose.host-ollama.yml").read_text(encoding="utf-8")

        self.assertIn("host.docker.internal:11434", override)
        self.assertIn("worker:", override)

    def test_nginx_resolves_recreated_api_containers_dynamically(self):
        nginx = (PROJECT_ROOT / "deploy" / "nginx.conf").read_text(encoding="utf-8")

        self.assertIn("resolver 127.0.0.11", nginx)
        self.assertIn("proxy_pass $api_upstream$request_uri", nginx)


if __name__ == "__main__":
    unittest.main()
