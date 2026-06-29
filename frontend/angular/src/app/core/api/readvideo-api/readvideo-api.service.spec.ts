import {HttpErrorResponse, provideHttpClient} from "@angular/common/http";
import {HttpTestingController, provideHttpClientTesting} from "@angular/common/http/testing";
import {TestBed} from "@angular/core/testing";
import {Observable} from "rxjs";
import {afterEach, beforeEach, describe, expect, it} from "vitest";

import {ProcessPayload} from "../../../shared/models/readvideo-types/readvideo.types";
import {ReadvideoApiService} from "./readvideo-api.service";

describe("ReadvideoApiService", () => {
  let api: ReadvideoApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({providers: [provideHttpClient(), provideHttpClientTesting()]});
    api = TestBed.inject(ReadvideoApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function expectRequest<T>(
    source$: Observable<T>,
    method: string,
    url: string,
    body: unknown = undefined,
    response: unknown = {},
  ): void {
    let received: T | undefined;
    source$.subscribe((value) => received = value);
    const request = http.expectOne(url);
    expect(request.request.method).toBe(method);
    if (body !== undefined) expect(request.request.body).toEqual(body);
    request.flush(response as never);
    expect(received).toEqual(response);
  }

  it("calls health, configuration, model, task, and processing endpoints", () => {
    expectRequest(api.health(), "GET", "/health", undefined, {status: "ok"});
    expectRequest(api.appConfig(), "GET", "/app_config");
    expectRequest(api.ollamaModels(), "GET", "/api/ollama/models");
    expectRequest(api.transcriptionModels(), "GET", "/api/transcription/models");
    expectRequest(api.downloadTranscriptionModel("large v3"), "POST", "/api/transcription/models/download", {model: "large v3"});
    expectRequest(api.lookupHistory("https://x.test/?a=1&b=2"), "GET", "/api/history/lookup?url=https%3A%2F%2Fx.test%2F%3Fa%3D1%26b%3D2");
    const payload = {url: "x"} as ProcessPayload;
    expectRequest(api.processVideo(payload), "POST", "/process_video/", payload);
    expectRequest(api.taskStatus("task/1"), "GET", "/task_status/task%2F1");
    expectRequest(api.tasks(), "GET", "/tasks", undefined, []);
  });

  it("calls history, tag, and favorite endpoints with encoded identifiers", () => {
    expectRequest(api.history(), "GET", "/api/history", undefined, []);
    expectRequest(api.tags(), "GET", "/api/tags", undefined, []);
    expectRequest(api.updateHistoryTags("task/1", ["AI"]), "PATCH", "/api/history/task%2F1/tags", {tags: ["AI"]});
    expectRequest(api.favoriteTask("task-1"), "POST", "/api/favorites", {task_id: "task-1"});
    expectRequest(api.favorites(), "GET", "/api/favorites", undefined, []);
    expectRequest(api.favoriteFolders(), "GET", "/api/favorites/folders", undefined, []);
    expectRequest(api.addFavoriteFolder("Course", "Notes"), "POST", "/api/favorites/folders", {name: "Course", notes: "Notes"});
    expectRequest(api.updateFavoriteFolder(4, "New", "Text"), "PATCH", "/api/favorites/folders/4", {name: "New", notes: "Text"});
    expectRequest(api.deleteFavoriteFolder(4), "DELETE", "/api/favorites/folders/4");
    expectRequest(api.assignFavoriteFolder(8, null), "PATCH", "/api/favorites/8/folder", {folder_id: null});
    expectRequest(api.updateFavoriteTags(8, ["reader"]), "PATCH", "/api/favorites/8/tags", {tags: ["reader"]});
    expectRequest(api.deleteFavorite(8), "DELETE", "/api/favorites/8");
    expectRequest(api.favoriteMarkdown(8), "GET", "/api/favorites/8/markdown");
  });

  it("calls Markdown and saved-source endpoints", () => {
    expectRequest(api.markdownFiles("Course Notes"), "GET", "/api/markdown_files?directory=Course%20Notes", undefined, []);
    expectRequest(api.markdownDocument("/notes/a b.md"), "GET", "/api/markdown_files/read?path=%2Fnotes%2Fa%20b.md");
    expectRequest(api.watchlist(), "GET", "/watchlist", undefined, []);
    const item = {name: "Channel", url: "https://x.test", notes: "Weekly"};
    expectRequest(api.addWatchItem(item), "POST", "/watchlist", item);
    expectRequest(api.reorderWatchItems([3, 1]), "PATCH", "/watchlist/reorder", {item_ids: [3, 1]}, []);
    expectRequest(api.deleteWatchItem(3), "DELETE", "/watchlist/3");
    expectRequest(api.sourceUpdates(3, 12), "GET", "/watchlist/3/updates?limit=12");
  });

  it.each([
    ["plain failure", "plain failure"],
    [{detail: "detailed failure"}, "detailed failure"],
    [{error: "payload failure"}, "payload failure"],
  ])("normalizes API errors from %j", (response, expected) => {
    let received: unknown;
    api.health().subscribe({error: (error) => received = error});
    http.expectOne("/health").flush(response, {status: 500, statusText: "Server Error"});

    expect(received).toBeInstanceOf(Error);
    expect((received as Error).message).toBe(expected);
    expect(received).not.toBeInstanceOf(HttpErrorResponse);
  });
});
