const WATCH_SORT_LABELS = {
  manual: "Manual order",
  newest: "Newest first",
  oldest: "Oldest first",
  "name-asc": "Name A-Z",
  "name-desc": "Name Z-A",
  "url-asc": "URL A-Z",
};

const WATCH_SORTERS = {
  manual: (a, b) => (a.sort_order || 0) - (b.sort_order || 0) || b.created_at.localeCompare(a.created_at),
  newest: (a, b) => b.created_at.localeCompare(a.created_at),
  oldest: (a, b) => a.created_at.localeCompare(b.created_at),
  "name-asc": (a, b) => a.name.localeCompare(b.name, undefined, {sensitivity: "base"}),
  "name-desc": (a, b) => b.name.localeCompare(a.name, undefined, {sensitivity: "base"}),
  "url-asc": (a, b) => a.url.localeCompare(b.url, undefined, {sensitivity: "base"}),
};

export function sortWatchItems(items, sortMode = "manual") {
  return [...items].sort(WATCH_SORTERS[sortMode] || WATCH_SORTERS.manual);
}

export function watchSortStatus(sortMode = "manual") {
  return WATCH_SORT_LABELS[sortMode] || WATCH_SORT_LABELS.manual;
}

export function buildMovedOrder(items, itemId, direction, sortMode = "manual") {
  const itemIds = sortedIds(items, sortMode);
  const currentIndex = itemIds.indexOf(Number(itemId));
  const nextIndex = currentIndex + direction;
  if (currentIndex === -1 || nextIndex < 0 || nextIndex >= itemIds.length) {
    return null;
  }

  [itemIds[currentIndex], itemIds[nextIndex]] = [itemIds[nextIndex], itemIds[currentIndex]];
  return itemIds;
}

export function buildDroppedOrder(items, draggedId, targetId, dropAfter, sortMode = "manual") {
  const currentIds = sortedIds(items, sortMode);
  const nextIds = [...currentIds];
  const draggedIndex = nextIds.indexOf(Number(draggedId));
  if (draggedIndex === -1 || Number(targetId) === Number(draggedId)) {
    return null;
  }

  nextIds.splice(draggedIndex, 1);
  const targetIndex = nextIds.indexOf(Number(targetId));
  if (targetIndex === -1) {
    return null;
  }

  nextIds.splice(targetIndex + (dropAfter ? 1 : 0), 0, Number(draggedId));
  return arraysEqual(currentIds, nextIds) ? null : nextIds;
}

export function applyLocalSortOrder(items, itemIds) {
  const byId = new Map(items.map((item) => [item.id, item]));
  const seen = new Set();
  const ordered = [];

  itemIds.forEach((id) => {
    const item = byId.get(Number(id));
    if (!item || seen.has(item.id)) return;
    seen.add(item.id);
    ordered.push({...item, sort_order: ordered.length + 1});
  });

  const trailing = sortWatchItems(items, "manual")
    .filter((item) => !seen.has(item.id))
    .map((item, index) => ({...item, sort_order: ordered.length + index + 1}));

  return [...ordered, ...trailing];
}

function sortedIds(items, sortMode) {
  return sortWatchItems(items, sortMode).map((item) => item.id);
}

function arraysEqual(left, right) {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}
