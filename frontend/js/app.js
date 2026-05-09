import {api} from "./api.js";
import {escapeHtml, formatElapsed} from "./format.js";

const state = {
  pollTimer: null,
  latestSummary: "",
  latestTask: null,
};

const elements = {
  healthPill: document.querySelector("#health-pill"),
  backendPill: document.querySelector("#backend-pill"),
  processForm: document.querySelector("#process-form"),
  startButton: document.querySelector("#start-button"),
  videoUrl: document.querySelector("#video-url"),
  notesDir: document.querySelector("#notes-dir"),
  notesBackend: document.querySelector("#notes-backend"),
  ollamaModel: document.querySelector("#ollama-model"),
  taskId: document.querySelector("#task-id"),
  taskMessage: document.querySelector("#task-message"),
  steps: Array.from(document.querySelectorAll(".step")),
  videoPath: document.querySelector("#video-path"),
  transcriptPath: document.querySelector("#transcript-path"),
  markdownPath: document.querySelector("#markdown-path"),
  summaryBox: document.querySelector("#summary-box"),
  favoriteSummary: document.querySelector("#favorite-summary"),
  copySummary: document.querySelector("#copy-summary"),
  refreshTasks: document.querySelector("#refresh-tasks"),
  recentTasks: document.querySelector("#recent-tasks"),
  watchForm: document.querySelector("#watch-form"),
  watchName: document.querySelector("#watch-name"),
  watchUrl: document.querySelector("#watch-url"),
  watchNotes: document.querySelector("#watch-notes"),
  watchlist: document.querySelector("#watchlist"),
  watchCount: document.querySelector("#watch-count"),
};

function setPill(element, text, kind = "muted") {
  element.textContent = text;
  element.className = `pill ${kind}`;
}

function setNotice(text, kind = "muted") {
  elements.taskMessage.textContent = text;
  elements.taskMessage.className = `notice ${kind}`;
}

function setStep(status) {
  const order = ["queued", "downloading", "transcribing", "organizing_notes", "completed"];
  const currentIndex = order.indexOf(status);

  elements.steps.forEach((step) => {
    const stepName = step.dataset.step;
    const stepIndex = order.indexOf(stepName);
    step.className = "step";

    if (status === "failed") {
      step.classList.add("failed");
    } else if (currentIndex >= 0 && stepIndex <= currentIndex) {
      const stepClass = status === "completed" || stepName !== status ? "active" : "pending";
      step.classList.add(stepClass);
    }
  });
}

function updateOutput(task) {
  state.latestTask = task;
  renderOutputPath(elements.videoPath, task, "video", task.video_path);
  renderOutputPath(elements.transcriptPath, task, "transcript", task.transcription_path);
  renderOutputPath(elements.markdownPath, task, "markdown", task.markdown_path);

  if (task.summary) {
    state.latestSummary = task.summary;
    elements.summaryBox.textContent = task.summary;
    elements.copySummary.disabled = false;
  }

  const canFavorite = Boolean(task.task_id && (task.summary || task.markdown_path));
  elements.favoriteSummary.disabled = !canFavorite;
  if (canFavorite) {
    elements.favoriteSummary.textContent = "Favorite Summary";
  }
}

function renderOutputPath(element, task, kind, value) {
  if (!value) {
    element.textContent = "-";
    return;
  }

  if (!task.task_id) {
    element.textContent = value;
    return;
  }

  const href = `/api/history/${encodeURIComponent(task.task_id)}/files/${kind}`;
  element.innerHTML = `<a class="path-anchor" href="${href}" target="_blank" rel="noreferrer">${escapeHtml(value)}</a>`;
}

function renderTask(task) {
  elements.taskId.textContent = task.task_id ? `Task ${task.task_id}` : "";
  setStep(task.status);
  updateOutput(task);
  const elapsed = formatElapsed(task);

  if (task.status === "completed") {
    setNotice(`Completed in ${elapsed}\nMarkdown: ${task.markdown_path}`, "ok");
    elements.startButton.disabled = false;
    loadRecentTasks();
    return;
  }

  if (task.status === "failed") {
    setNotice(`Failed after ${elapsed}\n${task.error || "Unknown error"}`, "error");
    elements.startButton.disabled = false;
    loadRecentTasks();
    return;
  }

  const label = task.status.replaceAll("_", " ");
  setNotice(`Working: ${label}\nElapsed: ${elapsed}`, "pending");
}

async function pollTask(taskId) {
  window.clearTimeout(state.pollTimer);
  try {
    const task = await api(`/task_status/${encodeURIComponent(taskId)}`);
    renderTask(task);
    if (!["completed", "failed"].includes(task.status)) {
      state.pollTimer = window.setTimeout(() => pollTask(taskId), 1800);
    }
  } catch (error) {
    setNotice(error.message, "error");
    elements.startButton.disabled = false;
  }
}

async function loadConfig() {
  try {
    const [health, config] = await Promise.all([api("/health"), api("/app_config")]);
    setPill(elements.healthPill, health.status === "ok" ? "Online" : "Check", health.status === "ok" ? "ok" : "muted");
    setPill(elements.backendPill, `${config.transcription_backend} / ${config.notes_backend}`, "muted");
    elements.notesDir.placeholder = config.notes_dir || "notes";
    elements.notesBackend.value = config.notes_backend || "extractive";
    elements.ollamaModel.placeholder = config.ollama_model || "qwen2.5:3b";
  } catch (error) {
    setPill(elements.healthPill, "Offline", "error");
    setNotice(error.message, "error");
  }
}

async function submitProcess(event) {
  event.preventDefault();
  await startProcessingUrl(elements.videoUrl.value.trim());
}

function buildProcessPayload(url) {
  return {
    url,
    notes_dir: elements.notesDir.value.trim() || null,
    notes_backend: elements.notesBackend.value,
    ollama_model: elements.ollamaModel.value.trim() || null,
  };
}

async function startProcessingUrl(url) {
  window.clearTimeout(state.pollTimer);

  const payload = buildProcessPayload(url);
  elements.videoUrl.value = url;
  elements.startButton.disabled = true;
  elements.summaryBox.textContent = "Waiting for task output...";
  elements.copySummary.disabled = true;
  elements.favoriteSummary.disabled = true;
  elements.favoriteSummary.textContent = "Favorite Summary";
  state.latestSummary = "";
  state.latestTask = null;
  setStep("queued");
  setNotice("Queued", "pending");

  try {
    const task = await api("/process_video/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderTask(task);
    await pollTask(task.task_id);
  } catch (error) {
    setNotice(error.message, "error");
    elements.startButton.disabled = false;
  }
}

async function loadWatchlist() {
  try {
    const items = await api("/watchlist");
    elements.watchCount.textContent = `${items.length} saved`;

    if (!items.length) {
      elements.watchlist.innerHTML = '<div class="empty-state">No saved sources yet.</div>';
      return;
    }

    elements.watchlist.innerHTML = items.map((item) => `
      <article class="watch-item" data-id="${item.id}">
        <p class="watch-title">${escapeHtml(item.name)}</p>
        <a class="watch-url" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.url)}</a>
        ${item.notes ? `<p class="watch-notes">${escapeHtml(item.notes)}</p>` : ""}
        <div class="watch-actions">
          <button class="secondary-button" type="button" data-action="use">Use</button>
          <button class="secondary-button" type="button" data-action="updates">Updates</button>
          <button class="danger-button" type="button" data-action="delete">Delete</button>
        </div>
        <div class="source-updates"></div>
      </article>
    `).join("");
  } catch (error) {
    elements.watchlist.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
}

async function loadRecentTasks() {
  try {
    const tasks = await api("/tasks");
    if (!tasks.length) {
      elements.recentTasks.innerHTML = '<div class="empty-state">No tasks yet.</div>';
      return;
    }

    elements.recentTasks.innerHTML = tasks.slice(0, 6).map((task) => `
      <button class="task-row" type="button" data-task-id="${escapeHtml(task.task_id)}">
        <span>
          <strong>${escapeHtml(task.status.replaceAll("_", " "))}</strong>
          <span>${escapeHtml(task.url || "No URL")}</span>
        </span>
        <span>${escapeHtml(formatElapsed(task))}</span>
      </button>
    `).join("");
  } catch (error) {
    elements.recentTasks.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
}

async function submitWatchItem(event) {
  event.preventDefault();
  try {
    await api("/watchlist", {
      method: "POST",
      body: JSON.stringify({
        name: elements.watchName.value.trim(),
        url: elements.watchUrl.value.trim(),
        notes: elements.watchNotes.value.trim(),
      }),
    });
    elements.watchForm.reset();
    await loadWatchlist();
  } catch (error) {
    setNotice(error.message, "error");
  }
}

async function handleWatchlistClick(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) return;

  const item = button.closest(".watch-item");
  const id = item.dataset.id;
  const action = button.dataset.action;

  if (action === "use") {
    elements.videoUrl.value = item.querySelector(".watch-url").textContent;
    elements.videoUrl.focus();
    return;
  }

  if (action === "updates") {
    await loadSourceUpdates(item, id);
    return;
  }

  if (action === "use-update" || action === "download-update") {
    const update = button.closest(".source-update");
    const url = update.dataset.url;
    elements.videoUrl.value = url;
    elements.videoUrl.focus();
    if (action === "download-update") {
      await startProcessingUrl(url);
    }
    return;
  }

  if (action === "delete") {
    await api(`/watchlist/${encodeURIComponent(id)}`, {method: "DELETE"});
    await loadWatchlist();
  }
}

async function loadSourceUpdates(item, id) {
  const container = item.querySelector(".source-updates");
  container.innerHTML = '<div class="empty-state">Checking source updates...</div>';

  try {
    const result = await api(`/watchlist/${encodeURIComponent(id)}/updates?limit=8`);
    if (!result.updates.length) {
      container.innerHTML = '<div class="empty-state">No videos found for this source.</div>';
      return;
    }

    container.innerHTML = `
      <div class="source-update-list">
        ${result.updates.map(renderSourceUpdate).join("")}
      </div>
    `;
  } catch (error) {
    container.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
}

function renderSourceUpdate(update) {
  const meta = [update.uploader, update.upload_date].filter(Boolean).join(" / ");
  return `
    <div class="source-update" data-url="${escapeHtml(update.url)}">
      <div>
        <p class="watch-title">${escapeHtml(update.title)}</p>
        <a class="watch-url" href="${escapeHtml(update.url)}" target="_blank" rel="noreferrer">${escapeHtml(update.url)}</a>
        ${meta ? `<p class="watch-notes">${escapeHtml(meta)}</p>` : ""}
      </div>
      <div class="watch-actions">
        <button class="secondary-button small-button" type="button" data-action="use-update">Use</button>
        <button class="secondary-button small-button" type="button" data-action="download-update">Download</button>
      </div>
    </div>
  `;
}

async function handleRecentTaskClick(event) {
  const button = event.target.closest("button[data-task-id]");
  if (!button) return;

  const task = await api(`/task_status/${encodeURIComponent(button.dataset.taskId)}`);
  renderTask(task);
  if (!["completed", "failed"].includes(task.status)) {
    await pollTask(task.task_id);
  }
}

async function copySummary() {
  if (!state.latestSummary) return;
  await navigator.clipboard.writeText(state.latestSummary);
  const oldText = elements.copySummary.textContent;
  elements.copySummary.textContent = "Copied";
  window.setTimeout(() => {
    elements.copySummary.textContent = oldText;
  }, 1200);
}

async function favoriteLatestSummary() {
  if (!state.latestTask?.task_id) return;

  const oldText = elements.favoriteSummary.textContent;
  elements.favoriteSummary.disabled = true;
  elements.favoriteSummary.textContent = "Saving";
  try {
    await api("/api/favorites", {
      method: "POST",
      body: JSON.stringify({task_id: state.latestTask.task_id}),
    });
    elements.favoriteSummary.textContent = "Favorited";
  } catch (error) {
    elements.favoriteSummary.disabled = false;
    elements.favoriteSummary.textContent = oldText;
    setNotice(error.message, "error");
  }
}

elements.processForm.addEventListener("submit", submitProcess);
elements.watchForm.addEventListener("submit", submitWatchItem);
elements.watchlist.addEventListener("click", handleWatchlistClick);
elements.copySummary.addEventListener("click", copySummary);
elements.favoriteSummary.addEventListener("click", favoriteLatestSummary);
elements.refreshTasks.addEventListener("click", loadRecentTasks);
elements.recentTasks.addEventListener("click", handleRecentTaskClick);

loadConfig();
loadWatchlist();
loadRecentTasks();
