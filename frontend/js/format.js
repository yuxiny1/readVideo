export function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}


export function formatElapsed(task) {
  const start = Date.parse(task.created_at);
  const end = Date.parse(task.completed_at || task.updated_at || new Date().toISOString());
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) {
    return "0s";
  }

  const seconds = Math.round((end - start) / 1000);
  if (seconds < 60) {
    return `${seconds}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}
