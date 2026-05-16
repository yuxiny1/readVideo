import assert from "node:assert/strict";
import test from "node:test";

import {renderMarkdown} from "../js/markdown.js";

test("renderMarkdown supports segment subheadings and escaped code blocks", () => {
  const html = renderMarkdown("#### Original Transcript\n\n```text\n<raw transcript>\n```");

  assert.match(html, /<h4>Original Transcript<\/h4>/);
  assert.match(html, /&lt;raw transcript&gt;/);
});
