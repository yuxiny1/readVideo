import assert from "node:assert/strict";
import test from "node:test";

import {
  applyLocalSortOrder,
  buildDroppedOrder,
  buildMovedOrder,
  sortWatchItems,
  watchSortStatus,
} from "../js/saved_sources.js";

const watchItems = [
  {
    id: 1,
    name: "Beta Channel",
    url: "https://www.youtube.com/@beta",
    created_at: "2026-05-10T10:00:00",
    sort_order: 2,
  },
  {
    id: 2,
    name: "alpha Channel",
    url: "https://www.youtube.com/@zeta",
    created_at: "2026-05-11T10:00:00",
    sort_order: 1,
  },
  {
    id: 3,
    name: "Gamma Channel",
    url: "https://www.youtube.com/@alpha",
    created_at: "2026-05-09T10:00:00",
    sort_order: 3,
  },
];

function ids(items) {
  return items.map((item) => item.id);
}

test("sortWatchItems supports all saved-source sort modes without mutating input", () => {
  assert.deepEqual(ids(sortWatchItems(watchItems, "manual")), [2, 1, 3]);
  assert.deepEqual(ids(sortWatchItems(watchItems, "newest")), [2, 1, 3]);
  assert.deepEqual(ids(sortWatchItems(watchItems, "oldest")), [3, 1, 2]);
  assert.deepEqual(ids(sortWatchItems(watchItems, "name-asc")), [2, 1, 3]);
  assert.deepEqual(ids(sortWatchItems(watchItems, "name-desc")), [3, 1, 2]);
  assert.deepEqual(ids(sortWatchItems(watchItems, "url-asc")), [3, 1, 2]);
  assert.deepEqual(ids(watchItems), [1, 2, 3]);
});

test("watchSortStatus labels known sorts and falls back to manual", () => {
  assert.equal(watchSortStatus("name-desc"), "Name Z-A");
  assert.equal(watchSortStatus("not-real"), "Manual order");
});

test("buildMovedOrder swaps the selected source within the current visual sort", () => {
  assert.deepEqual(buildMovedOrder(watchItems, 1, -1, "manual"), [1, 2, 3]);
  assert.deepEqual(buildMovedOrder(watchItems, 3, -1, "name-asc"), [2, 3, 1]);
  assert.equal(buildMovedOrder(watchItems, 2, -1, "manual"), null);
  assert.equal(buildMovedOrder(watchItems, 404, 1, "manual"), null);
});

test("buildDroppedOrder inserts before or after the target and ignores no-op drops", () => {
  assert.deepEqual(buildDroppedOrder(watchItems, 3, 2, false, "manual"), [3, 2, 1]);
  assert.deepEqual(buildDroppedOrder(watchItems, 2, 3, true, "manual"), [1, 3, 2]);
  assert.equal(buildDroppedOrder(watchItems, 2, 1, false, "manual"), null);
  assert.equal(buildDroppedOrder(watchItems, 2, 2, true, "manual"), null);
  assert.equal(buildDroppedOrder(watchItems, 2, 404, true, "manual"), null);
});

test("applyLocalSortOrder deduplicates ids, skips unknown ids, and appends trailing sources", () => {
  const reordered = applyLocalSortOrder(watchItems, [3, 999, 3]);
  assert.deepEqual(ids(reordered), [3, 2, 1]);
  assert.deepEqual(reordered.map((item) => item.sort_order), [1, 2, 3]);
  assert.deepEqual(ids(watchItems), [1, 2, 3]);
});
