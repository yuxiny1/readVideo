export interface TaggedItem {
  tags?: string[];
}

export type TagToneClass =
  | "tag-tone-1"
  | "tag-tone-2"
  | "tag-tone-3"
  | "tag-tone-4"
  | "tag-tone-5"
  | "tag-tone-6"
  | "tag-tone-7"
  | "tag-tone-8";

const TAG_TONE_COUNT = 8;

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

export function tagToneClass(tag: string): TagToneClass {
  let hash = 0;
  for (const character of tag.trim().toLocaleLowerCase()) {
    hash = (Math.imul(hash, 31) + (character.codePointAt(0) ?? 0)) >>> 0;
  }
  return `tag-tone-${(hash % TAG_TONE_COUNT) + 1}` as TagToneClass;
}
