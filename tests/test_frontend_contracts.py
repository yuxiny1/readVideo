import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_repo_file(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


class FrontendContractTest(unittest.TestCase):
    def test_reader_limits_favorite_notes_to_three_visible_items(self):
        component = read_repo_file("frontend/angular/src/app/pages/reader-page/reader-page.component.ts")
        template = read_repo_file("frontend/angular/src/app/pages/reader-page/reader-page.component.html")
        styles = read_repo_file("frontend/css/partials/reader-library.css")

        self.assertIn("visibleFavoriteNotes", component)
        self.assertIn(".slice(0, 3)", component)
        self.assertIn("@for (item of visibleFavoriteNotes(); track item.id)", template)
        self.assertIn("favorite-note-list", styles)

    def test_saved_sources_exposes_compact_actions_menu(self):
        template = read_repo_file("frontend/angular/src/app/components/saved-sources/saved-sources.component.html")
        component = read_repo_file("frontend/angular/src/app/components/saved-sources/saved-sources.component.ts")
        styles = read_repo_file("frontend/css/partials/saved-sources.css")

        self.assertIn("openActionsId", component)
        self.assertIn("action-menu-panel", template)
        self.assertIn("Use", template)
        self.assertIn("Updates", template)
        self.assertIn("Delete", template)
        self.assertIn(".action-menu-panel", styles)

    def test_check_script_runs_frontend_build_and_backend_coverage(self):
        package = json.loads(read_repo_file("package.json"))

        self.assertEqual(package["scripts"]["check"], "npm run check:frontend && npm run test:coverage")
        self.assertIn("coverage report --fail-under=80", package["scripts"]["test:coverage"])


if __name__ == "__main__":
    unittest.main()
