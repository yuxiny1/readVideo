import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, inject, OnInit, signal} from "@angular/core";
import {FormsModule} from "@angular/forms";

import {ProcessFormService} from "../../services/process-form.service";
import {TaskWorkflowService} from "../../services/task-workflow.service";
import {SourceUpdate, WatchItem} from "../../types/readvideo.types";
import {SavedSourcesFacade} from "./saved-sources.facade";

type DropPosition = "before" | "after";

@Component({
  selector: "rv-saved-sources",
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: "./saved-sources.component.html",
  providers: [SavedSourcesFacade],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SavedSourcesComponent implements OnInit {
  private readonly form = inject(ProcessFormService);
  private readonly workflow = inject(TaskWorkflowService);
  readonly sources = inject(SavedSourcesFacade);

  readonly draggedItemId = signal<number | null>(null);
  readonly dropTarget = signal<{id: number; position: DropPosition} | null>(null);
  readonly openActionsId = signal<number | null>(null);
  private orderBeforeDrag: WatchItem[] = [];

  ngOnInit(): void {
    this.sources.loadWatchlist();
  }

  useUrl(url: string): void {
    this.form.patch({url});
  }

  downloadUrl(url: string): void {
    this.form.patch({url});
    this.workflow.startProcessingUrl(url);
  }

  toggleActions(itemId: number): void {
    this.openActionsId.update((openId) => openId === itemId ? null : itemId);
  }

  closeActions(): void {
    this.openActionsId.set(null);
  }

  startDrag(event: DragEvent, item: WatchItem): void {
    const target = event.target as HTMLElement | null;
    if (target?.closest("a, input, textarea, select, button:not(.drag-handle)") || this.sources.orderSaving()) {
      event.preventDefault();
      return;
    }
    this.orderBeforeDrag = [...this.sources.items()];
    this.draggedItemId.set(item.id);
    this.dropTarget.set(null);
    event.dataTransfer?.setData("text/plain", String(item.id));
    if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
  }

  dragOver(event: DragEvent, item: WatchItem): void {
    const draggedId = this.draggedItemId();
    if (!draggedId || draggedId === item.id) return;
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
    const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
    const position: DropPosition = event.clientY > rect.top + rect.height / 2 ? "after" : "before";
    this.dropTarget.set({id: item.id, position});
  }

  dropOn(event: DragEvent, item: WatchItem): void {
    event.preventDefault();
    const draggedId = this.draggedItemId();
    const target = this.dropTarget() ?? {id: item.id, position: "before" as DropPosition};
    if (!draggedId || draggedId === target.id) {
      this.clearDragState();
      return;
    }
    const reordered = reorderItems(this.sources.items(), draggedId, target.id, target.position);
    if (!sameOrder(reordered, this.sources.items())) {
      this.sources.persistOrder(reordered, this.orderBeforeDrag);
    }
    this.clearDragState();
  }

  clearDragState(): void {
    this.draggedItemId.set(null);
    this.dropTarget.set(null);
    this.closeActions();
  }

  isDropTarget(item: WatchItem, position: DropPosition): boolean {
    const target = this.dropTarget();
    return target?.id === item.id && target.position === position;
  }

  updateMeta(update: SourceUpdate): string {
    return [update.uploader, update.upload_date].filter(Boolean).join(" / ");
  }
}

function reorderItems(
  items: WatchItem[],
  draggedId: number,
  targetId: number,
  position: DropPosition,
): WatchItem[] {
  const draggedItem = items.find((item) => item.id === draggedId);
  if (!draggedItem) return items;
  const reordered = items.filter((item) => item.id !== draggedId);
  const targetIndex = reordered.findIndex((item) => item.id === targetId);
  if (targetIndex === -1) return items;
  reordered.splice(position === "after" ? targetIndex + 1 : targetIndex, 0, draggedItem);
  return reordered;
}

function sameOrder(first: WatchItem[], second: WatchItem[]): boolean {
  return first.length === second.length && first.every((item, index) => item.id === second[index]?.id);
}
