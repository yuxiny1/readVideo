import {api} from "./api.js";
import {escapeHtml, formatElapsed} from "./format.js";


const elements = {
  count: document.querySelector("#history-count"),
  list: document.querySelector("#history-list"),
  refresh: document.querySelector("#refresh-history"),
};

const state = {
  folders: [],
};


async function loadFolders() {
  try {
    state.folders = await api("/api/favorites/folders");
  } catch {
    state.folders = [];
  }
}


async function loadHistory() {
  elements.count.textContent = "Loading";
  try {
    await loadFolders();
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
  const canFavorite = Boolean(record.summary || record.markdown_path);
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
        ${pathRow("Source", record.url)}
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

      <div class="history-favorite-row">
        <label for="history-folder-${escapeHtml(record.task_id)}">Favorite Folder</label>
        <select id="history-folder-${escapeHtml(record.task_id)}" data-role="favorite-folder" ${canFavorite ? "" : "disabled"}>
          <option value="">Unfiled</option>
          ${state.folders.map((folder) => `<option value="${folder.id}">${escapeHtml(folder.name)}</option>`).join("")}
        </select>
      </div>

      <div class="card-actions">
        <button class="secondary-button small-button" type="button" data-action="favorite" data-task-id="${escapeHtml(record.task_id)}" ${canFavorite ? "" : "disabled"}>Favorite</button>
        ${record.markdown_path ? `<a class="quiet-link small-link" href="/reader?path=${encodeURIComponent(record.markdown_path)}" target="_blank" rel="noreferrer">Read MD</a>` : ""}
        ${record.markdown_path ? `<a class="quiet-link small-link" href="/api/markdown_files/download?path=${encodeURIComponent(record.markdown_path)}">Download MD</a>` : ""}
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


async function handleHistoryClick(event) {
  const button = event.target.closest("button[data-action='favorite']");
  if (!button) return;

  const oldText = button.textContent;
  const card = button.closest(".history-card");
  const folderSelect = card.querySelector("select[data-role='favorite-folder']");
  const folderId = folderSelect?.value ? Number(folderSelect.value) : null;
  button.disabled = true;
  button.textContent = "Saving";
  try {
    await api("/api/favorites", {
      method: "POST",
      body: JSON.stringify({
        task_id: button.dataset.taskId,
        folder_id: folderId,
      }),
    });
    button.textContent = "Favorited";
  } catch (error) {
    button.disabled = false;
    button.textContent = oldText;
    elements.list.insertAdjacentHTML("afterbegin", `<div class="empty-state">${escapeHtml(error.message)}</div>`);
  }
}


elements.refresh.addEventListener("click", loadHistory);
elements.list.addEventListener("click", handleHistoryClick);
loadHistory();
