import assert from "node:assert/strict";
import test from "node:test";

import {escapeHtml, formatElapsed} from "../js/format.js";

test("escapeHtml escapes characters that can break rendered markup", () => {
  assert.equal(
    escapeHtml("<script>alert('x') & \"quote\"</script>"),
    "&lt;script&gt;alert(&#39;x&#39;) &amp; &quot;quote&quot;&lt;/script&gt;",
  );
});

test("formatElapsed formats seconds and minute spans", () => {
  assert.equal(
    formatElapsed({
      created_at: "2026-05-11T10:00:00",
      updated_at: "2026-05-11T10:00:42",
    }),
    "42s",
  );
  assert.equal(
    formatElapsed({
      created_at: "2026-05-11T10:00:00",
      completed_at: "2026-05-11T10:02:05",
    }),
    "2m 5s",
  );
});

test("formatElapsed falls back to zero seconds for invalid ranges", () => {
  assert.equal(
    formatElapsed({
      created_at: "2026-05-11T10:00:00",
      updated_at: "2026-05-11T09:59:59",
    }),
    "0s",
  );
  assert.equal(formatElapsed({created_at: "not a date", updated_at: "also not a date"}), "0s");
});
