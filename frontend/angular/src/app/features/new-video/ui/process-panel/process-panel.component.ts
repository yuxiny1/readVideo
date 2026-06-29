import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, input, output} from "@angular/core";
import {FormsModule} from "@angular/forms";

import {ProcessFormState} from "../../data-access/process-form/process-form.service";
import {statusLabel} from "../../../../shared/utils/format/format";
import {
  AppConfig,
  DuplicateLookup,
  NoticeState,
  OllamaModel,
  TaskLog,
  TaskRecord,
  TranscriptionLanguageOption,
  WhisperModelOption,
} from "../../../../shared/models/readvideo-types/readvideo.types";

export interface ProcessPanelViewModel {
  form: ProcessFormState;
  taskIdLabel: string;
  config: AppConfig | null;
  whisperModels: WhisperModelOption[];
  transcriptionLanguages: TranscriptionLanguageOption[];
  whisperStatus: NoticeState;
  ollamaModels: OllamaModel[];
  ollamaStatus: NoticeState;
  notice: NoticeState;
  duplicate: DuplicateLookup | null;
  latestTask: TaskRecord | null;
  phaseTitle: string;
  phaseDetail: string;
  progressPercent: number;
  logs: TaskLog[];
}

export type DuplicateAction = "use" | "regenerate" | "redownload";

@Component({
  selector: "rv-process-panel",
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: "./process-panel.component.html",
  styleUrl: "./process-panel.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProcessPanelComponent {
  readonly vm = input.required<ProcessPanelViewModel>();
  readonly formPatched = output<Partial<ProcessFormState>>();
  readonly submitRequested = output<void>();
  readonly whisperDownloadRequested = output<string>();
  readonly strongestModelRequested = output<void>();
  readonly duplicateAction = output<DuplicateAction>();
  readonly steps = ["queued", "downloading", "transcribing", "organizing_notes", "completed"];

  stepClass(step: string): string {
    const status = this.vm().latestTask?.status || "";
    const currentIndex = this.steps.indexOf(status);
    const stepIndex = this.steps.indexOf(step);
    if (status === "failed") return "failed";
    if (currentIndex >= 0 && stepIndex <= currentIndex) {
      return status === "completed" || step !== status ? "active" : "pending";
    }
    return "";
  }

  patchForm(update: Partial<ProcessFormState>): void {
    this.formPatched.emit(update);
  }

  resolveWhisperModel(pathOrName: string): WhisperModelOption | null {
    return this.vm().whisperModels.find((model) => (
      model.path === pathOrName || model.name === pathOrName
    )) ?? null;
  }

  resolveOllamaModel(name: string): OllamaModel | null {
    return this.vm().ollamaModels.find((model) => model.name === name) ?? null;
  }

  modelLabel(model: OllamaModel): string {
    return [model.size_label, model.parameter_size, model.quantization_level].filter(Boolean).join(" · ");
  }

  whisperModelLabel(model: WhisperModelOption): string {
    return [
      model.recommended ? "Recommended" : "",
      model.size,
      model.installed ? "installed" : "download",
    ].filter(Boolean).join(" · ");
  }

  statusLabel(status: string): string {
    return statusLabel(status);
  }
}
