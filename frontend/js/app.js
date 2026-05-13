import {api} from "./api.js";
import {escapeHtml, formatElapsed} from "./format.js";
import {
  applyLocalSortOrder,
  buildDroppedOrder,
  buildMovedOrder,
  sortWatchItems,
  watchSortStatus,
} from "./saved_sources.js";

const state = {
  pollTimer: null,
  latestSummary: "",
  latestTask: null,
  whisperModelOptions: [],
  whisperInstalledModels: [],
  transcriptionLanguages: [],
  openaiTranscriptionModels: [],
  ollamaModelOptions: [],
  ollamaInstalledModels: [],
  watchItems: [],
  watchSort: "manual",
  draggedWatchId: null,
  pointerDrag: null,
};

const elements = {
  healthPill: document.querySelector("#health-pill"),
  backendPill: document.querySelector("#backend-pill"),
  processForm: document.querySelector("#process-form"),
  startButton: document.querySelector("#start-button"),
  videoUrl: document.querySelector("#video-url"),
  notesDir: document.querySelector("#notes-dir"),
  transcriptionBackend: document.querySelector("#transcription-backend"),
  transcriptionLanguage: document.querySelector("#transcription-language"),
  localWhisperModelSelect: document.querySelector("#local-whisper-model-select"),
  localWhisperModelCustom: document.querySelector("#local-whisper-model-custom"),
  downloadWhisperModel: document.querySelector("#download-whisper-model"),
  openaiTranscriptionModel: document.querySelector("#openai-transcription-model"),
  transcriptionPrompt: document.querySelector("#transcription-prompt"),
  notesBackend: document.querySelector("#notes-backend"),
  ollamaModelSelect: document.querySelector("#ollama-model-select"),
  ollamaModelCustom: document.querySelector("#ollama-model-custom"),
  pullOllamaModel: document.querySelector("#pull-ollama-model"),
  ollamaModelMessage: document.querySelector("#ollama-model-message"),
  whisperModelPill: document.querySelector("#whisper-model-pill"),
  whisperModelMessage: document.querySelector("#whisper-model-message"),
  taskId: document.querySelector("#task-id"),
  taskMessage: document.querySelector("#task-message"),
  steps: Array.from(document.querySelectorAll(".step")),
  videoPath: document.querySelector("#video-path"),
  transcriptPath: document.querySelector("#transcript-path"),
  markdownPath: document.querySelector("#markdown-path"),
  summaryBox: document.querySelector("#summary-box"),
  readSummary: document.querySelector("#read-summary"),
  favoriteSummary: document.querySelector("#favorite-summary"),
  copySummary: document.querySelector("#copy-summary"),
  refreshTasks: document.querySelector("#refresh-tasks"),
  recentTasks: document.querySelector("#recent-tasks"),
  watchForm: document.querySelector("#watch-form"),
  watchName: document.querySelector("#watch-name"),
  watchUrl: document.querySelector("#watch-url"),
  watchNotes: document.querySelector("#watch-notes"),
  watchSort: document.querySelector("#watch-sort"),
  watchSortStatus: document.querySelector("#watch-sort-status"),
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
  } else {
    state.latestSummary = "";
    elements.copySummary.disabled = true;
    elements.summaryBox.textContent = ["completed", "failed"].includes(task.status)
      ? "No summary available."
      : "Waiting for task output...";
  }

  const canFavorite = Boolean(task.task_id && (task.summary || task.markdown_path));
  elements.favoriteSummary.disabled = !canFavorite;
  if (canFavorite) {
    elements.favoriteSummary.textContent = "Favorite Summary";
  }

  updateReadSummaryLink(task.markdown_path);
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

function updateReadSummaryLink(markdownPath) {
  if (!markdownPath) {
    elements.readSummary.href = "/reader";
    elements.readSummary.classList.add("disabled-link");
    elements.readSummary.setAttribute("aria-disabled", "true");
    return;
  }

  elements.readSummary.href = `/reader?path=${encodeURIComponent(markdownPath)}`;
  elements.readSummary.classList.remove("disabled-link");
  elements.readSummary.setAttribute("aria-disabled", "false");
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
    const [health, config, models, transcriptionModels] = await Promise.all([
      api("/health"),
      api("/app_config"),
      api("/api/ollama/models"),
      api("/api/transcription/models"),
    ]);
    setPill(elements.healthPill, health.status === "ok" ? "Online" : "Check", health.status === "ok" ? "ok" : "muted");
    setPill(elements.backendPill, `${config.transcription_backend} / ${config.notes_backend}`, "muted");
    elements.notesDir.placeholder = config.notes_dir || "notes";
    elements.transcriptionBackend.value = config.transcription_backend || "local";
    elements.transcriptionPrompt.value = config.transcription_prompt || "";
    elements.notesBackend.value = config.notes_backend || "extractive";
    state.whisperModelOptions = transcriptionModels.whisper || [];
    state.whisperInstalledModels = transcriptionModels.installed_whisper || [];
    state.transcriptionLanguages = transcriptionModels.languages || [];
    state.openaiTranscriptionModels = transcriptionModels.openai || config.openai_transcription_model_options || [];
    renderTranscriptionLanguageOptions(state.transcriptionLanguages, config.local_whisper_language || "auto");
    renderWhisperModelOptions(state.whisperModelOptions, config.local_whisper_model || "models/ggml-small.bin");
    renderOpenAITranscriptionOptions(state.openaiTranscriptionModels, config.transcription_model || "gpt-4o-mini-transcribe");
    state.ollamaModelOptions = models.recommended || config.ollama_model_options || [];
    state.ollamaInstalledModels = models.installed || [];
    renderOllamaModelOptions(state.ollamaModelOptions, config.ollama_model || "qwen2.5:3b");
    updateTranscriptionStatus();
  } catch (error) {
    setPill(elements.healthPill, "Offline", "error");
    setNotice(error.message, "error");
  }
}

function renderTranscriptionLanguageOptions(options, selectedLanguage) {
  const languages = options.length ? options : [{code: "auto", label: "Auto detect"}];
  elements.transcriptionLanguage.innerHTML = languages.map((option) => `
    <option value="${escapeHtml(option.code)}" ${option.code === selectedLanguage ? "selected" : ""}>
      ${escapeHtml(option.label)}
    </option>
  `).join("");
  if (!languages.some((option) => option.code === selectedLanguage)) {
    elements.transcriptionLanguage.insertAdjacentHTML(
      "afterbegin",
      `<option value="${escapeHtml(selectedLanguage)}" selected>${escapeHtml(selectedLanguage)}</option>`,
    );
  }
}

function renderWhisperModelOptions(options, selectedModel) {
  const installed = new Set(state.whisperInstalledModels);
  const knownModels = new Set(options.flatMap((option) => [option.name, option.path]));
  const fallback = knownModels.has(selectedModel)
    ? ""
    : `<option value="${escapeHtml(selectedModel)}" selected>${escapeHtml(selectedModel)} (configured)</option>`;
  elements.localWhisperModelSelect.innerHTML = `
    ${fallback}
    ${options.map((option) => `
      <option value="${escapeHtml(option.path)}" ${option.path === selectedModel || option.name === selectedModel ? "selected" : ""}>
        ${escapeHtml(option.label)} - ${escapeHtml(option.size)}${installed.has(option.path) ? " - installed" : ""}
      </option>
    `).join("")}
  `;
}

function renderOpenAITranscriptionOptions(options, selectedModel) {
  const knownModels = new Set(options.map((option) => option.name));
  const fallback = knownModels.has(selectedModel) ? "" : `<option value="${escapeHtml(selectedModel)}" selected>${escapeHtml(selectedModel)}</option>`;
  elements.openaiTranscriptionModel.innerHTML = `
    ${fallback}
    ${options.map((option) => `
      <option value="${escapeHtml(option.name)}" ${option.name === selectedModel ? "selected" : ""}>
        ${escapeHtml(option.label)}
      </option>
    `).join("")}
  `;
}

function selectedWhisperModel() {
  return elements.localWhisperModelCustom.value.trim() || elements.localWhisperModelSelect.value;
}

function updateTranscriptionStatus() {
  const backend = elements.transcriptionBackend.value;
  const language = elements.transcriptionLanguage.value || "auto";
  const model = backend === "openai" ? elements.openaiTranscriptionModel.value : selectedWhisperModel();
  setPill(elements.whisperModelPill, `Transcription: ${backend} / ${language}`, "muted");
  const option = state.whisperModelOptions.find((item) => item.path === model || item.name === model);
  const installedText = option
    ? state.whisperInstalledModels.includes(option.path) ? "Installed." : "Not installed yet."
    : "Custom model path.";
  const languageHint = language === "auto"
    ? "Auto language detection is active; this is the safest choice for English, Chinese, and mixed videos."
    : `${language} is forced; use this only when the whole video is that language.`;
  elements.whisperModelMessage.textContent = backend === "openai"
    ? `${model}: OpenAI transcription. ${languageHint}`
    : `${model}: ${installedText} ${languageHint} ${option?.notes || ""}`;
}

function renderOllamaModelOptions(options, selectedModel) {
  const knownModels = new Set(options.map((option) => option.name));
  const fallback = knownModels.has(selectedModel) ? "" : `<option value="${escapeHtml(selectedModel)}" selected>${escapeHtml(selectedModel)} (configured)</option>`;
  const installedModels = new Set(state.ollamaInstalledModels);
  elements.ollamaModelSelect.innerHTML = `
    ${fallback}
    ${options.map((option) => `
      <option value="${escapeHtml(option.name)}" ${option.name === selectedModel ? "selected" : ""}>
        ${escapeHtml(option.label)} - ${escapeHtml(option.size)}${installedModels.has(option.name) ? " - installed" : ""}
      </option>
    `).join("")}
  `;
  updateOllamaModelMessage(options);
}

function selectedOllamaModel() {
  return elements.ollamaModelCustom.value.trim() || elements.ollamaModelSelect.value;
}

function updateOllamaModelMessage(options = []) {
  const model = selectedOllamaModel();
  const option = options.find((item) => item.name === model);
  const installText = state.ollamaInstalledModels.includes(model) ? "Installed." : "Not installed yet.";
  const backendHint = elements.notesBackend.value === "ollama"
    ? "Active for this run."
    : "Select Summary Backend = Ollama Local LLM to use this model.";
  elements.ollamaModelMessage.textContent = option
    ? `${option.name}: ${backendHint} ${installText} ${option.notes} Pull command: ollama pull ${option.name}`
    : `${model || "Custom model"}: ${backendHint} Custom Ollama model for summary generation.`;
}

async function submitProcess(event) {
  event.preventDefault();
  await startProcessingUrl(elements.videoUrl.value.trim());
}

function buildProcessPayload(url) {
  return {
    url,
    transcription_backend: elements.transcriptionBackend.value,
    transcription_model: elements.openaiTranscriptionModel.value,
    transcription_prompt: elements.transcriptionPrompt.value.trim() || null,
    local_whisper_model: selectedWhisperModel() || null,
    local_whisper_language: elements.transcriptionLanguage.value || "auto",
    notes_dir: elements.notesDir.value.trim() || null,
    notes_backend: elements.notesBackend.value,
    ollama_model: selectedOllamaModel() || null,
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
  updateReadSummaryLink(null);
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
    state.watchItems = items;
    renderWatchlist();
  } catch (error) {
    elements.watchlist.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
}

function renderWatchlist() {
  const items = sortedWatchItems();
  elements.watchCount.textContent = `${state.watchItems.length} saved`;
  elements.watchSort.value = state.watchSort;
  elements.watchSortStatus.textContent = sortStatusText();

  if (!items.length) {
    elements.watchlist.innerHTML = '<div class="empty-state">No saved sources yet.</div>';
    return;
  }

  elements.watchlist.innerHTML = items.map((item) => `
      <article class="watch-item" data-id="${item.id}" draggable="true">
        <div class="history-card-header">
          <div class="watch-title-wrap">
            <span class="drag-handle" title="Drag this source to reorder">Drag</span>
            <button class="icon-button" type="button" data-action="move-up" title="Move source up" aria-label="Move source up">Up</button>
            <button class="icon-button" type="button" data-action="move-down" title="Move source down" aria-label="Move source down">Down</button>
            <p class="watch-title">${escapeHtml(item.name)}</p>
          </div>
          <div class="actions-wrap">
            <button class="secondary-button small-button" type="button" data-action="toggle-actions">Actions</button>
            <div class="actions-menu hidden">
              <button type="button" data-action="use">Use</button>
              <button type="button" data-action="updates">Updates</button>
              <button type="button" data-action="move-up">Move Up</button>
              <button type="button" data-action="move-down">Move Down</button>
              <button type="button" data-action="edit-source">Edit</button>
              <button class="danger-text" type="button" data-action="delete">Delete</button>
            </div>
          </div>
        </div>
        <a class="watch-url" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.url)}</a>
        <p class="watch-meta">Saved ${escapeHtml(formatSavedDate(item.created_at))}</p>
        ${item.notes ? `<p class="watch-notes">${escapeHtml(item.notes)}</p>` : ""}
        <form class="watch-edit-form hidden">
          <label>Name<input name="name" required value="${escapeHtml(item.name)}"></label>
          <label>URL<input name="url" required value="${escapeHtml(item.url)}"></label>
          <label>Notes<textarea name="notes">${escapeHtml(item.notes || "")}</textarea></label>
          <div class="button-row">
            <button class="secondary-button small-button" type="submit">Save</button>
            <button class="secondary-button small-button" type="button" data-action="cancel-edit">Cancel</button>
          </div>
        </form>
        <div class="source-updates"></div>
      </article>
    `).join("");
}

function sortedWatchItems() {
  return sortWatchItems(state.watchItems, state.watchSort);
}

function sortStatusText() {
  return watchSortStatus(state.watchSort);
}

function formatSavedDate(value) {
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return value || "-";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(timestamp));
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

  if (action === "toggle-actions") {
    toggleActionsMenu(item);
    return;
  }

  if (action === "use") {
    hideActionsMenu(item);
    elements.videoUrl.value = item.querySelector(".watch-url").textContent;
    elements.videoUrl.focus();
    return;
  }

  if (action === "updates") {
    hideActionsMenu(item);
    await loadSourceUpdates(item, id);
    return;
  }

  if (action === "edit-source") {
    hideActionsMenu(item);
    item.querySelector(".watch-edit-form").classList.remove("hidden");
    return;
  }

  if (action === "move-up" || action === "move-down") {
    hideActionsMenu(item);
    await moveWatchItem(Number(id), action === "move-up" ? -1 : 1);
    return;
  }

  if (action === "cancel-edit") {
    item.querySelector(".watch-edit-form").classList.add("hidden");
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
    hideActionsMenu(item);
    await api(`/watchlist/${encodeURIComponent(id)}`, {method: "DELETE"});
    await loadWatchlist();
  }
}

function toggleActionsMenu(container) {
  const menu = container.querySelector(".actions-menu");
  elements.watchlist.querySelectorAll(".actions-menu").forEach((item) => {
    if (item !== menu) {
      item.classList.add("hidden");
    }
  });
  menu.classList.toggle("hidden");
}

function hideActionsMenu(container) {
  container.querySelector(".actions-menu")?.classList.add("hidden");
}

function handleWatchlistDragStart(event) {
  if (state.pointerDrag) {
    event.preventDefault();
    return;
  }

  const item = event.target.closest(".watch-item");
  if (!item || event.target.closest("a, button, input, textarea, select")) {
    event.preventDefault();
    return;
  }

  state.draggedWatchId = Number(item.dataset.id);
  item.classList.add("dragging");
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", String(state.draggedWatchId));
}

function handleWatchlistDragOver(event) {
  const item = event.target.closest(".watch-item");
  if (!item || state.draggedWatchId === null) return;
  event.preventDefault();
  elements.watchlist.querySelectorAll(".drop-target, .drop-before, .drop-after").forEach((target) => {
    if (target !== item) {
      target.classList.remove("drop-target", "drop-before", "drop-after");
    }
  });
  item.classList.add("drop-target");
  item.classList.toggle("drop-after", shouldDropAfter(event, item));
  item.classList.toggle("drop-before", !shouldDropAfter(event, item));
  event.dataTransfer.dropEffect = "move";
}

function handleWatchlistDragLeave(event) {
  const item = event.target.closest(".watch-item");
  if (item && !item.contains(event.relatedTarget)) {
    item.classList.remove("drop-target", "drop-before", "drop-after");
  }
}

async function handleWatchlistDrop(event) {
  const target = event.target.closest(".watch-item");
  if (!target || state.draggedWatchId === null) return;
  event.preventDefault();

  const itemIds = buildDroppedOrder(
    state.watchItems,
    state.draggedWatchId,
    Number(target.dataset.id),
    shouldDropAfter(event, target),
    state.watchSort,
  );
  clearWatchDragState();
  if (itemIds) {
    await saveWatchOrder(itemIds);
  }
}

function shouldDropAfter(event, item) {
  const rect = item.getBoundingClientRect();
  return event.clientY > rect.top + rect.height / 2;
}

function handleWatchlistDragEnd() {
  clearWatchDragState();
}

function handleWatchPointerDown(event) {
  const handle = event.target.closest(".drag-handle");
  if (!handle || event.button !== 0) return;

  const item = handle.closest(".watch-item");
  if (!item) return;

  event.preventDefault();
  state.pointerDrag = {
    id: Number(item.dataset.id),
    startX: event.clientX,
    startY: event.clientY,
    targetId: null,
    dropAfter: false,
    active: false,
  };
  handle.setPointerCapture?.(event.pointerId);
}

function handleWatchPointerMove(event) {
  const drag = state.pointerDrag;
  if (!drag) return;

  const distance = Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY);
  if (!drag.active && distance < 4) return;

  event.preventDefault();
  drag.active = true;

  const draggedItem = elements.watchlist.querySelector(`.watch-item[data-id="${drag.id}"]`);
  draggedItem?.classList.add("dragging");

  const target = document.elementFromPoint(event.clientX, event.clientY)?.closest(".watch-item");
  if (!target || Number(target.dataset.id) === drag.id) {
    drag.targetId = null;
    clearWatchDropTargets();
    return;
  }

  drag.targetId = Number(target.dataset.id);
  drag.dropAfter = shouldDropAfter(event, target);
  markWatchDropTarget(target, drag.dropAfter);
}

async function handleWatchPointerUp(event) {
  const drag = state.pointerDrag;
  if (!drag) return;

  event.preventDefault();
  state.pointerDrag = null;
  const shouldSave = drag.active && drag.targetId !== null && drag.targetId !== drag.id;
  clearWatchDragState();
  if (!shouldSave) return;

  const itemIds = buildDroppedOrder(state.watchItems, drag.id, drag.targetId, drag.dropAfter, state.watchSort);
  if (itemIds) {
    await saveWatchOrder(itemIds);
  }
}

function handleWatchPointerCancel() {
  state.pointerDrag = null;
  clearWatchDragState();
}

function markWatchDropTarget(item, dropAfter) {
  clearWatchDropTargets(item);
  item.classList.add("drop-target");
  item.classList.toggle("drop-after", dropAfter);
  item.classList.toggle("drop-before", !dropAfter);
}

function clearWatchDropTargets(exceptItem = null) {
  elements.watchlist.querySelectorAll(".drop-target, .drop-before, .drop-after").forEach((target) => {
    if (target !== exceptItem) {
      target.classList.remove("drop-target", "drop-before", "drop-after");
    }
  });
}

function clearWatchDragState() {
  state.draggedWatchId = null;
  elements.watchlist.querySelectorAll(".dragging, .drop-target, .drop-before, .drop-after").forEach((item) => {
    item.classList.remove("dragging", "drop-target", "drop-before", "drop-after");
  });
}

async function saveWatchOrder(itemIds) {
  const previousItems = state.watchItems;
  state.watchItems = applyLocalSortOrder(state.watchItems, itemIds);
  state.watchSort = "manual";
  elements.watchSort.value = "manual";
  renderWatchlist();

  try {
    state.watchItems = await api("/watchlist/reorder", {
      method: "PATCH",
      body: JSON.stringify({item_ids: itemIds}),
    });
    renderWatchlist();
  } catch (error) {
    state.watchItems = previousItems;
    renderWatchlist();
    setNotice(error.message, "error");
  }
}

async function moveWatchItem(itemId, direction) {
  const itemIds = buildMovedOrder(state.watchItems, itemId, direction, state.watchSort);
  if (itemIds) {
    await saveWatchOrder(itemIds);
  }
}

async function handleWatchlistSubmit(event) {
  const form = event.target.closest(".watch-edit-form");
  if (!form) return;

  event.preventDefault();
  const item = form.closest(".watch-item");
  const id = item.dataset.id;
  await api(`/watchlist/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify({
      name: form.elements.name.value.trim(),
      url: form.elements.url.value.trim(),
      notes: form.elements.notes.value.trim(),
    }),
  });
  await loadWatchlist();
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

async function pullSelectedOllamaModel() {
  const model = selectedOllamaModel();
  if (!model) return;

  const oldText = elements.pullOllamaModel.textContent;
  elements.pullOllamaModel.disabled = true;
  elements.pullOllamaModel.textContent = "Pulling...";
  elements.ollamaModelMessage.textContent = `Running: ollama pull ${model}`;
  try {
    await api("/api/ollama/pull", {
      method: "POST",
      body: JSON.stringify({model}),
    });
    if (!state.ollamaInstalledModels.includes(model)) {
      state.ollamaInstalledModels.push(model);
    }
    renderOllamaModelOptions(state.ollamaModelOptions, model);
    elements.ollamaModelMessage.textContent = `Installed ${model}.`;
  } catch (error) {
    elements.ollamaModelMessage.textContent = error.message;
  } finally {
    elements.pullOllamaModel.disabled = false;
    elements.pullOllamaModel.textContent = oldText;
  }
}

async function downloadSelectedWhisperModel() {
  const model = elements.localWhisperModelSelect.value;
  if (!model) return;

  const oldText = elements.downloadWhisperModel.textContent;
  elements.downloadWhisperModel.disabled = true;
  elements.downloadWhisperModel.textContent = "Downloading...";
  elements.whisperModelMessage.textContent = `Downloading ${model}. This can take a while for medium or large models.`;
  try {
    const result = await api("/api/transcription/models/download", {
      method: "POST",
      body: JSON.stringify({model}),
    });
    if (!state.whisperInstalledModels.includes(result.path)) {
      state.whisperInstalledModels.push(result.path);
    }
    renderWhisperModelOptions(state.whisperModelOptions, result.path);
    elements.localWhisperModelCustom.value = "";
    elements.whisperModelMessage.textContent = result.downloaded
      ? `Downloaded ${result.path}.`
      : `${result.path} is already installed.`;
    updateTranscriptionStatus();
  } catch (error) {
    elements.whisperModelMessage.textContent = error.message;
  } finally {
    elements.downloadWhisperModel.disabled = false;
    elements.downloadWhisperModel.textContent = oldText;
  }
}

elements.processForm.addEventListener("submit", submitProcess);
elements.watchForm.addEventListener("submit", submitWatchItem);
elements.watchlist.addEventListener("click", handleWatchlistClick);
elements.watchlist.addEventListener("submit", handleWatchlistSubmit);
elements.watchlist.addEventListener("dragstart", handleWatchlistDragStart);
elements.watchlist.addEventListener("dragover", handleWatchlistDragOver);
elements.watchlist.addEventListener("dragleave", handleWatchlistDragLeave);
elements.watchlist.addEventListener("drop", handleWatchlistDrop);
elements.watchlist.addEventListener("dragend", handleWatchlistDragEnd);
elements.watchlist.addEventListener("pointerdown", handleWatchPointerDown);
window.addEventListener("pointermove", handleWatchPointerMove);
window.addEventListener("pointerup", handleWatchPointerUp);
window.addEventListener("pointercancel", handleWatchPointerCancel);
elements.copySummary.addEventListener("click", copySummary);
elements.favoriteSummary.addEventListener("click", favoriteLatestSummary);
elements.pullOllamaModel.addEventListener("click", pullSelectedOllamaModel);
elements.downloadWhisperModel.addEventListener("click", downloadSelectedWhisperModel);
elements.transcriptionBackend.addEventListener("change", updateTranscriptionStatus);
elements.transcriptionLanguage.addEventListener("change", updateTranscriptionStatus);
elements.localWhisperModelSelect.addEventListener("change", updateTranscriptionStatus);
elements.localWhisperModelCustom.addEventListener("input", updateTranscriptionStatus);
elements.openaiTranscriptionModel.addEventListener("change", updateTranscriptionStatus);
elements.watchSort.addEventListener("change", () => {
  state.watchSort = elements.watchSort.value;
  renderWatchlist();
});
elements.notesBackend.addEventListener("change", () => updateOllamaModelMessage(state.ollamaModelOptions));
elements.ollamaModelSelect.addEventListener("change", () => updateOllamaModelMessage(state.ollamaModelOptions));
elements.ollamaModelCustom.addEventListener("input", () => updateOllamaModelMessage(state.ollamaModelOptions));
elements.refreshTasks.addEventListener("click", loadRecentTasks);
elements.recentTasks.addEventListener("click", handleRecentTaskClick);

loadConfig();
loadWatchlist();
loadRecentTasks();
