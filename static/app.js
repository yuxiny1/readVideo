const state = {
  pollTimer: null,
  latestSummary: "",
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
  copySummary: document.querySelector("#copy-summary"),
  watchForm: document.querySelector("#watch-form"),
  watchName: document.querySelector("#watch-name"),
  watchUrl: document.querySelector("#watch-url"),
  watchNotes: document.querySelector("#watch-notes"),
  watchlist: document.querySelector("#watchlist"),
  watchCount: document.querySelector("#watch-count"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {"Content-Type": "application/json", ...(options.headers || {})},
    ...options,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(data?.detail || data?.error || response.statusText);
  }
  return data;
}

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
      step.classList.add(stepName === status ? "pending" : "active");
    }
  });
}

function updateOutput(task) {
  elements.videoPath.textContent = task.video_path || "-";
  elements.transcriptPath.textContent = task.transcription_path || "-";
  elements.markdownPath.textContent = task.markdown_path || "-";

  if (task.summary) {
    state.latestSummary = task.summary;
    elements.summaryBox.textContent = task.summary;
    elements.copySummary.disabled = false;
  }
}

function renderTask(task) {
  elements.taskId.textContent = task.task_id ? `Task ${task.task_id}` : "";
  setStep(task.status);
  updateOutput(task);

  if (task.status === "completed") {
    setNotice(`Completed\nMarkdown: ${task.markdown_path}`, "ok");
    elements.startButton.disabled = false;
    return;
  }

  if (task.status === "failed") {
    setNotice(`Failed\n${task.error || "Unknown error"}`, "error");
    elements.startButton.disabled = false;
    return;
  }

  const label = task.status.replaceAll("_", " ");
  setNotice(`Working: ${label}`, "pending");
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
  window.clearTimeout(state.pollTimer);

  const payload = {
    url: elements.videoUrl.value.trim(),
    notes_dir: elements.notesDir.value.trim() || null,
    notes_backend: elements.notesBackend.value,
    ollama_model: elements.ollamaModel.value.trim() || null,
  };

  elements.startButton.disabled = true;
  elements.summaryBox.textContent = "Waiting for task output...";
  elements.copySummary.disabled = true;
  state.latestSummary = "";
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
          <button class="danger-button" type="button" data-action="delete">Delete</button>
        </div>
      </article>
    `).join("");
  } catch (error) {
    elements.watchlist.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
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

  if (action === "delete") {
    await api(`/watchlist/${encodeURIComponent(id)}`, {method: "DELETE"});
    await loadWatchlist();
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

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

elements.processForm.addEventListener("submit", submitProcess);
elements.watchForm.addEventListener("submit", submitWatchItem);
elements.watchlist.addEventListener("click", handleWatchlistClick);
elements.copySummary.addEventListener("click", copySummary);

loadConfig();
loadWatchlist();
