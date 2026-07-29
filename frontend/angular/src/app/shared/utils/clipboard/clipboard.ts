const COPY_ERROR_MESSAGE = "复制失败，请手动选择文本复制。";

export async function copyTextToClipboard(value: string): Promise<void> {
  if (!value) return;

  const clipboard = typeof navigator === "undefined" ? undefined : navigator.clipboard;
  const writeText = clipboard?.writeText;
  if (typeof writeText === "function") {
    try {
      await writeText.call(clipboard, value);
      return;
    } catch {
      // Browsers can reject or synchronously throw when clipboard permission is unavailable.
    }
  }

  legacyCopyText(value);
}

function legacyCopyText(value: string): void {
  if (typeof document === "undefined" || !document.body) {
    throw new Error(COPY_ERROR_MESSAGE);
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.top = "-1000px";
  textarea.style.left = "-1000px";
  textarea.style.opacity = "0";

  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  textarea.setSelectionRange(0, value.length);

  try {
    const execCopy = document.execCommand;
    if (typeof execCopy !== "function" || !execCopy.call(document, "copy")) {
      throw new Error(COPY_ERROR_MESSAGE);
    }
  } catch {
    throw new Error(COPY_ERROR_MESSAGE);
  } finally {
    textarea.remove();
  }
}
