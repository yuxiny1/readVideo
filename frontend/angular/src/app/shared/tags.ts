export interface TaggedItem {
  tags?: string[];
}

export function tagsFor(item: TaggedItem): string[] {
  return item.tags ?? [];
}

export function hasTag(tags: readonly string[], tag: string): boolean {
  const needle = tag.toLocaleLowerCase();
  return tags.some((item) => item.toLocaleLowerCase() === needle);
}

export function parseTags(value: string): string[] {
  return [...new Set(
    value
      .replace(/(^|\s)#/g, "$1,")
      .split(/[,;\n]+/)
      .map((tag) => tag.trim().replace(/^#/, ""))
      .filter(Boolean),
  )];
}
