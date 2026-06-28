import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_repo_file(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


class FrontendContractTest(unittest.TestCase):
    def test_reader_limits_favorite_notes_to_three_visible_items(self):
        facade = read_repo_file("frontend/angular/src/app/pages/reader-page/reader.facade.ts")
        template = read_repo_file("frontend/angular/src/app/pages/reader-page/reader-page.component.html")
        styles = read_repo_file("frontend/css/partials/reader-library.css")

        self.assertIn("visibleFavoriteNotes", facade)
        self.assertIn(".slice(0, 3)", facade)
        self.assertIn("@for (item of vm.visibleFavoriteNotes(); track item.id)", template)
        self.assertIn("favorite-note-list", styles)

    def test_reader_exposes_focus_mode(self):
        document_store = read_repo_file("frontend/angular/src/app/pages/reader-page/reader-document.store.ts")
        preferences = read_repo_file("frontend/angular/src/app/pages/reader-page/reader-preferences.ts")
        template = read_repo_file("frontend/angular/src/app/pages/reader-page/reader-page.component.html")
        library_styles = read_repo_file("frontend/css/partials/reader-library.css")
        document_styles = read_repo_file("frontend/css/partials/reader-document.css")

        self.assertIn("focusMode", document_store)
        self.assertIn("toggleFocusMode", document_store)
        self.assertIn("readvideo.reader.focusMode", preferences)
        self.assertIn("focusTheme", document_store)
        self.assertIn("readvideo.reader.focusTheme", preferences)
        self.assertIn("reader-focus-mode", template)
        self.assertIn("reader-focus-dark", template)
        self.assertIn("Focus Mode", template)
        self.assertIn("Dark", template)
        self.assertIn("@if (!vm.document.focusMode())", template)
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

        self.assertEqual(
            package["scripts"]["check"],
            "npm run check:frontend && npm run test:frontend:coverage && npm run test:coverage",
        )
        self.assertEqual(package["scripts"]["test:frontend"], "ng test --watch=false")
        self.assertEqual(package["scripts"]["test:frontend:coverage"], "ng test --watch=false --coverage")
        self.assertIn("coverage report --fail-under=80", package["scripts"]["test:coverage"])

    def test_every_frontend_typescript_module_has_a_colocated_spec(self):
        source_root = PROJECT_ROOT / "frontend" / "angular" / "src"
        production_files = sorted(
            path for path in source_root.rglob("*.ts")
            if not path.name.endswith(".spec.ts")
        )
        missing_specs = [
            path.relative_to(PROJECT_ROOT).as_posix()
            for path in production_files
            if not path.with_name(f"{path.stem}.spec.ts").is_file()
        ]

        self.assertEqual(missing_specs, [], f"Missing frontend specs: {missing_specs}")

    def test_angular_vitest_runner_enforces_frontend_coverage(self):
        workspace = json.loads(read_repo_file("angular.json"))
        test_options = workspace["projects"]["readvideo"]["architect"]["test"]

        self.assertEqual(test_options["builder"], "@angular/build:unit-test")
        self.assertEqual(test_options["options"]["runner"], "vitest")
        self.assertEqual(
            test_options["options"]["coverageThresholds"],
            {"statements": 80, "branches": 60, "functions": 80, "lines": 80},
        )

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
        reader_document = read_repo_file("frontend/angular/src/app/pages/reader-page/reader-document.store.ts")

        self.assertIn("Copy Full Note", latest_template)
        self.assertIn("copyRequested.emit()", latest_template)
        self.assertIn("markdownDocument(markdownPath)", workflow)
        self.assertIn("Full Markdown note copied", workflow)
        self.assertIn("Copy Full MD", reader_template)
        self.assertIn("Full Markdown copied", reader_document)

    def test_tags_are_shared_across_favorites_reader_and_history(self):
        api = read_repo_file("frontend/angular/src/app/services/readvideo-api.service.ts")
        types = read_repo_file("frontend/angular/src/app/types/readvideo.types.ts")
        library_store = read_repo_file("frontend/angular/src/app/features/library/data-access/library.store.ts")
        favorites_facade = read_repo_file("frontend/angular/src/app/pages/favorites-page/favorites.facade.ts")
        favorites_template = read_repo_file("frontend/angular/src/app/pages/favorites-page/favorites-page.component.html")
        reader_facade = read_repo_file("frontend/angular/src/app/pages/reader-page/reader.facade.ts")
        reader_template = read_repo_file("frontend/angular/src/app/pages/reader-page/reader-page.component.html")
        history_facade = read_repo_file("frontend/angular/src/app/pages/history-page/history.facade.ts")
        history_template = read_repo_file("frontend/angular/src/app/pages/history-page/history-page.component.html")

        self.assertIn("TagSummary", types)
        self.assertIn("tags?: string[]", types)
        self.assertIn("updateFavoriteTags", api)
        self.assertIn("updateHistoryTags", api)
        self.assertIn("/api/tags", api)
        self.assertIn("Notebook Folders", favorites_template)
        self.assertIn("tagDrafts", favorites_facade)
        self.assertIn("folder-visual-card", favorites_template)
        self.assertIn("note-tag-manager", favorites_template)
        self.assertIn("Save Tags", favorites_template)
        self.assertIn("openFolderInReader", favorites_facade)
        self.assertIn("updateFavoriteFolder", api)
        self.assertNotIn('(click)="deleteFolder(folder)"', favorites_template)
        self.assertIn("saveTags(item)", favorites_template)
        self.assertIn("favoriteFolderId", reader_facade)
        self.assertIn("setActiveFavoriteFolder", reader_facade)
        self.assertIn("activeTag", reader_facade)
        self.assertIn("saveActiveTags", reader_facade)
        self.assertIn("updateFavoriteTags", library_store)
        self.assertIn("this.library.updateTags", reader_facade)
        self.assertIn("reader-document-tags-row", reader_template)
        self.assertIn("reader-tag-edit-row", reader_template)
        self.assertIn("Save Tags", reader_template)
        self.assertIn("No tags", reader_template)
        self.assertIn("reader-tag-filter", reader_template)
        self.assertIn("activeDocumentTags", reader_template)
        self.assertIn("filteredRecords", history_facade)
        self.assertIn("vm.saveTags(record)", history_template)

    def test_angular_architecture_uses_scoped_signals_and_observable_boundaries(self):
        app_root = PROJECT_ROOT / "frontend/angular/src/app"
        api = read_repo_file("frontend/angular/src/app/services/readvideo-api.service.ts")
        routes = read_repo_file("frontend/angular/src/app/app.routes.ts")
        new_video = read_repo_file("frontend/angular/src/app/pages/new-video-page/new-video-page.component.ts")

        self.assertIn("HttpClient", api)
        self.assertIn("Observable<", api)
        self.assertNotIn("fetch(", api)
        self.assertNotIn("Promise<", api)
        self.assertIn("loadComponent", routes)
        self.assertIn("providers: [ProcessFormService, LocalModelsService, TaskWorkflowService]", new_video)

        for component in app_root.rglob("*.component.ts"):
            source = component.read_text(encoding="utf-8")
            self.assertIn(
                "ChangeDetectionStrategy.OnPush",
                source,
                f"{component.relative_to(PROJECT_ROOT)} must use OnPush",
            )

        for relative_path in [
            "frontend/angular/src/app/components/process-panel/process-panel.component.ts",
            "frontend/angular/src/app/components/latest-output/latest-output.component.ts",
        ]:
            source = read_repo_file(relative_path)
            self.assertIn("input.required", source)
            self.assertIn("output<", source)
            self.assertNotIn("inject(", source)

    def test_ngrx_signal_stores_manage_library_and_reader_state(self):
        package = json.loads(read_repo_file("package.json"))
        library_store = read_repo_file("frontend/angular/src/app/features/library/data-access/library.store.ts")
        reader_store = read_repo_file("frontend/angular/src/app/pages/reader-page/reader-document.store.ts")
        favorites_page = read_repo_file("frontend/angular/src/app/pages/favorites-page/favorites-page.component.ts")
        favorites_facade = read_repo_file("frontend/angular/src/app/pages/favorites-page/favorites.facade.ts")
        reader_page = read_repo_file("frontend/angular/src/app/pages/reader-page/reader-page.component.ts")
        reader_facade = read_repo_file("frontend/angular/src/app/pages/reader-page/reader.facade.ts")

        self.assertEqual(package["dependencies"]["@ngrx/signals"], "^21.1.1")
        for store in [library_store, reader_store]:
            self.assertIn("signalStore(", store)
            self.assertIn("withState", store)
            self.assertIn("withComputed", store)
            self.assertIn("withMethods", store)
            self.assertIn("patchState", store)
            self.assertIn("rxMethod", store)
            self.assertNotIn("providedIn", store)

        self.assertIn("providers: [LibraryStore, FavoritesFacade]", favorites_page)
        self.assertIn("providers: [LibraryStore, ReaderDocumentStore, ReaderFacade]", reader_page)
        self.assertIn("readonly favorites = this.library.favorites", favorites_facade)
        self.assertIn("readonly favorites = this.library.favorites", reader_facade)
        self.assertNotIn("readonly favorites = signal", favorites_facade)
        self.assertNotIn("readonly favorites = signal", reader_facade)

    def test_frontend_typescript_modules_stay_focused(self):
        app_root = PROJECT_ROOT / "frontend/angular/src/app"
        for module in app_root.rglob("*.ts"):
            line_count = len(module.read_text(encoding="utf-8").splitlines())
            self.assertLessEqual(
                line_count,
                350,
                f"{module.relative_to(PROJECT_ROOT)} has {line_count} lines; split its responsibilities",
            )


if __name__ == "__main__":
    unittest.main()
