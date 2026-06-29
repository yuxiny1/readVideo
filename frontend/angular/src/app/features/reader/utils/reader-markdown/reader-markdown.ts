import {ReaderHeading} from "../../models/reader-types/reader.types";

export type MarkdownMetadataLabel = "source" | "generated" | "transcript";

const METADATA_LABELS: Readonly<Record<MarkdownMetadataLabel, readonly string[]>> = Object.freeze({
  source: ["来源", "Source"],
  generated: ["生成时间", "Generated"],
  transcript: ["转录文件", "Transcript"],
});

export function extractMetadata(markdown: string, label: MarkdownMetadataLabel): string {
  const labels = METADATA_LABELS[label].join("|");
  const match = markdown.match(new RegExp(`^\\s*-?\\s*(?:${labels})[:：]\\s*(.+)$`, "m"));
  return match?.[1]?.trim() ?? "";
}

export function extractHeadings(markdown: string): ReaderHeading[] {
  const headings: ReaderHeading[] = [];
  let index = 0;
  for (const line of markdown.split(/\r?\n/)) {
    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (!heading) continue;
    index += 1;
    const level = heading[1].length;
    if (level > 3) continue;
    headings.push({id: `section-${index}`, level, title: stripMarkdown(heading[2])});
  }
  return headings;
}

export function countMatches(content: string, query: string): number {
  const needle = query.trim().toLocaleLowerCase();
  if (!content || !needle) return 0;
  const haystack = content.toLocaleLowerCase();
  let count = 0;
  let position = 0;
  while ((position = haystack.indexOf(needle, position)) !== -1) {
    count += 1;
    position += needle.length;
  }
  return count;
}

export function extractTitle(markdown: string): string {
  return markdown.match(/^#\s+(.+)$/m)?.[1]?.trim() ?? "";
}

export function fileName(path: string): string {
  return path.split(/[\\/]/).filter(Boolean).pop() || path || "Markdown 笔记";
}

export function readingStats(content: string): string {
  const words = content.trim().split(/\s+/).filter(Boolean).length;
  const cjkChars = content.match(/[\u4e00-\u9fff]/g)?.length ?? 0;
  const units = Math.max(words, Math.ceil(cjkChars / 2));
  return `约 ${Math.max(1, Math.ceil(units / 260))} 分钟读完`;
}

export function renderMarkdown(markdown: string): string {
  const html: string[] = [];
  let inList: "ul" | "ol" | null = null;
  let inCode = false;
  let codeLines: string[] = [];
  let headingIndex = 0;

  const closeList = () => {
    if (!inList) return;
    html.push(`</${inList}>`);
    inList = null;
  };
  const openList = (kind: "ul" | "ol") => {
    if (inList === kind) return;
    closeList();
    html.push(`<${kind}>`);
    inList = kind;
  };
  const closeCode = () => {
    html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
    codeLines = [];
    inCode = false;
  };

  for (const rawLine of markdown.split(/\r?\n/)) {
    const line = rawLine.trimEnd();
    if (line.trim().startsWith("```")) {
      if (inCode) closeCode();
      else {
        closeList();
        inCode = true;
      }
      continue;
    }
    if (inCode) {
      codeLines.push(rawLine);
      continue;
    }
    if (!line.trim()) {
      closeList();
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      closeList();
      headingIndex += 1;
      const level = heading[1].length;
      html.push(`<h${level} id="section-${headingIndex}">${inlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }
    if (/^---+$/.test(line.trim())) {
      closeList();
      html.push("<hr>");
      continue;
    }
    const quote = line.match(/^>\s+(.+)$/);
    if (quote) {
      closeList();
      html.push(`<blockquote>${inlineMarkdown(quote[1])}</blockquote>`);
      continue;
    }
    const bullet = line.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      openList("ul");
      html.push(`<li>${inlineMarkdown(bullet[1])}</li>`);
      continue;
    }
    const numbered = line.match(/^\d+[.)]\s+(.+)$/);
    if (numbered) {
      openList("ol");
      html.push(`<li>${inlineMarkdown(numbered[1])}</li>`);
      continue;
    }
    closeList();
    html.push(`<p>${inlineMarkdown(line)}</p>`);
  }

  closeList();
  if (inCode) closeCode();
  return html.join("");
}

export function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[character] ?? character));
}

function inlineMarkdown(value: string): string {
  return escapeHtml(value)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

function stripMarkdown(value: string): string {
  return value
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .trim();
}
