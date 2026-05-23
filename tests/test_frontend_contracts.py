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

    def test_reader_exposes_focus_mode(self):
        component = read_repo_file("frontend/angular/src/app/pages/reader-page/reader-page.component.ts")
        template = read_repo_file("frontend/angular/src/app/pages/reader-page/reader-page.component.html")
        library_styles = read_repo_file("frontend/css/partials/reader-library.css")
        document_styles = read_repo_file("frontend/css/partials/reader-document.css")

        self.assertIn("focusMode", component)
        self.assertIn("toggleFocusMode", component)
        self.assertIn("readvideo.reader.focusMode", component)
        self.assertIn("focusTheme", component)
        self.assertIn("readvideo.reader.focusTheme", component)
        self.assertIn("reader-focus-mode", template)
        self.assertIn("reader-focus-dark", template)
        self.assertIn("Focus Mode", template)
        self.assertIn("Dark", template)
        self.assertIn("@if (!focusMode())", template)
        self.assertIn(".reader-workspace.reader-focus-mode", library_styles)
        self.assertIn(".reader-workspace.reader-focus-dark", library_styles)
        self.assertIn(".app-layout:has(.reader-workspace.reader-focus-mode)", library_styles)
        self.assertIn(".reader-focus-mode .modern-reader", document_styles)
        self.assertIn(".reader-focus-dark .modern-reader", document_styles)

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

    def test_new_video_exposes_commercial_editorial_note_style(self):
        template = read_repo_file("frontend/angular/src/app/components/process-panel/process-panel.component.html")
        form_service = read_repo_file("frontend/angular/src/app/services/process-form.service.ts")
        types = read_repo_file("frontend/angular/src/app/types/readvideo.types.ts")

        self.assertIn('name="note_style"', template)
        self.assertIn("Commercial Editorial", template)
        self.assertIn("Business Lens", template)
        self.assertIn('note_style: form.noteStyle', form_service)
        self.assertIn('"detailed" | "commercial"', types)

    def test_copy_buttons_copy_full_markdown_notes(self):
        latest_template = read_repo_file("frontend/angular/src/app/components/latest-output/latest-output.component.html")
        workflow = read_repo_file("frontend/angular/src/app/services/task-workflow.service.ts")
        reader_template = read_repo_file("frontend/angular/src/app/pages/reader-page/reader-page.component.html")
        reader_component = read_repo_file("frontend/angular/src/app/pages/reader-page/reader-page.component.ts")

        self.assertIn("Copy Full Note", latest_template)
        self.assertIn("copyLatestOutput", latest_template)
        self.assertIn("markdownDocument(markdownPath)", workflow)
        self.assertIn("Full Markdown note copied", workflow)
        self.assertIn("Copy Full MD", reader_template)
        self.assertIn("Full Markdown copied", reader_component)

    def test_tags_are_shared_across_favorites_reader_and_history(self):
        api = read_repo_file("frontend/angular/src/app/services/readvideo-api.service.ts")
        types = read_repo_file("frontend/angular/src/app/types/readvideo.types.ts")
        favorites_component = read_repo_file("frontend/angular/src/app/pages/favorites-page/favorites-page.component.ts")
        favorites_template = read_repo_file("frontend/angular/src/app/pages/favorites-page/favorites-page.component.html")
        reader_component = read_repo_file("frontend/angular/src/app/pages/reader-page/reader-page.component.ts")
        reader_template = read_repo_file("frontend/angular/src/app/pages/reader-page/reader-page.component.html")
        history_component = read_repo_file("frontend/angular/src/app/pages/history-page/history-page.component.ts")
        history_template = read_repo_file("frontend/angular/src/app/pages/history-page/history-page.component.html")

        self.assertIn("TagSummary", types)
        self.assertIn("tags?: string[]", types)
        self.assertIn("updateFavoriteTags", api)
        self.assertIn("updateHistoryTags", api)
        self.assertIn("/api/tags", api)
        self.assertIn("Notebook Folders", favorites_template)
        self.assertIn("tagDrafts", favorites_component)
        self.assertIn("folder-visual-card", favorites_template)
        self.assertIn("note-tag-manager", favorites_template)
        self.assertIn("Save Tags", favorites_template)
        self.assertIn("openFolderInReader", favorites_component)
        self.assertIn("updateFavoriteFolder", api)
        self.assertNotIn('(click)="deleteFolder(folder)"', favorites_template)
        self.assertIn("saveTags(item)", favorites_template)
        self.assertIn("favoriteFolderId", reader_component)
        self.assertIn("setActiveFavoriteFolder", reader_component)
        self.assertIn("activeTag", reader_component)
        self.assertIn("reader-document-tags-row", reader_template)
        self.assertIn("No tags", reader_template)
        self.assertIn("reader-tag-filter", reader_template)
        self.assertIn("activeDocumentTags", reader_template)
        self.assertIn("filteredRecords", history_component)
        self.assertIn("saveTags(record)", history_template)


if __name__ == "__main__":
    unittest.main()
