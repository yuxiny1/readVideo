import {CommonModule} from "@angular/common";
import {Component, inject} from "@angular/core";
import {FormsModule} from "@angular/forms";

import {ProcessFormService} from "../../services/process-form.service";
import {TaskWorkflowService} from "../../services/task-workflow.service";
import {OllamaModel} from "../../types/readvideo.types";

@Component({
  selector: "rv-process-panel",
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: "./process-panel.component.html",
})
export class ProcessPanelComponent {
  readonly form = inject(ProcessFormService);
  readonly workflow = inject(TaskWorkflowService);
  readonly steps = ["queued", "downloading", "transcribing", "organizing_notes", "completed"];

  submit(): void {
    void this.workflow.startFromForm();
  }

  stepClass(step: string): string {
    const status = this.workflow.latestTask()?.status || "";
    const currentIndex = this.steps.indexOf(status);
    const stepIndex = this.steps.indexOf(step);
    if (status === "failed") return "failed";
    if (currentIndex >= 0 && stepIndex <= currentIndex) {
      return status === "completed" || step !== status ? "active" : "pending";
    }
    return "";
  }

  setUrl(url: string): void {
    this.form.patch({url});
  }

  setNotesDir(notesDir: string): void {
    this.form.patch({notesDir});
  }

  setNotesBackend(notesBackend: "extractive" | "ollama"): void {
    this.form.patch({notesBackend});
    this.workflow.validateOllamaSelection();
  }

  setTranscriptionBackend(transcriptionBackend: "local" | "openai"): void {
    this.form.patch({transcriptionBackend});
  }

  setTranscriptionModel(transcriptionModel: string): void {
    this.form.patch({transcriptionModel});
  }

  setLocalWhisperModel(localWhisperModel: string): void {
    this.form.patch({localWhisperModel});
  }

  setLocalWhisperLanguage(localWhisperLanguage: string): void {
    this.form.patch({localWhisperLanguage});
  }

  setOllamaModel(ollamaModel: string): void {
    this.form.patch({ollamaModel});
    this.workflow.validateOllamaSelection();
  }

  setDeleteVideoAfterCompletion(deleteVideoAfterCompletion: boolean): void {
    this.form.patch({deleteVideoAfterCompletion});
  }

  modelLabel(model: OllamaModel): string {
    return [model.size_label, model.parameter_size, model.quantization_level].filter(Boolean).join(" · ");
  }
}
