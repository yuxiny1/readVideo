import {api} from "./api.js";
import {escapeHtml, formatElapsed} from "./format.js";


const elements = {
  count: document.querySelector("#history-count"),
  list: document.querySelector("#history-list"),
  refresh: document.querySelector("#refresh-history"),
};


async function loadHistory() {
  elements.count.textContent = "Loading";
  try {
    const records = await api("/api/history");
    elements.count.textContent = `${records.length} records`;

    if (!records.length) {
      elements.list.innerHTML = '<div class="empty-state">No processed videos yet.</div>';
      return;
    }

    elements.list.innerHTML = records.map(renderRecord).join("");
  } catch (error) {
    elements.count.textContent = "Error";
    elements.list.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
}


function renderRecord(record) {
  const title = record.title || record.url || record.task_id;
  const statusClass = record.status === "completed" ? "ok" : record.status === "failed" ? "error" : "pending";
  return `
    <article class="history-card">
      <div class="history-card-header">
        <div>
          <h2>${escapeHtml(title)}</h2>
          <a class="watch-url" href="${escapeHtml(record.url)}" target="_blank" rel="noreferrer">${escapeHtml(record.url || "No URL")}</a>
        </div>
        <span class="pill ${statusClass}">${escapeHtml(record.status)}</span>
      </div>

      <dl class="path-list">
        ${pathRow("Video", record.video_path)}
        ${pathRow("Transcript", record.transcription_path)}
        ${pathRow("Markdown", record.markdown_path)}
      </dl>

      <div class="history-meta">
        <span>Updated: ${escapeHtml(record.updated_at || "-")}</span>
        <span>Elapsed: ${escapeHtml(formatElapsed(record))}</span>
        <span>Transcription: ${escapeHtml(record.transcription_backend || "-")}</span>
        <span>Summary: ${escapeHtml(record.summary_backend || "-")}</span>
      </div>

      ${record.error ? `<pre class="history-error">${escapeHtml(record.error)}</pre>` : ""}
    </article>
  `;
}


function pathRow(label, value) {
  const path = value || "-";
  return `
    <div>
      <dt>${escapeHtml(label)}</dt>
      <dd><code>${escapeHtml(path)}</code></dd>
    </div>
  `;
}


elements.refresh.addEventListener("click", loadHistory);
loadHistory();
