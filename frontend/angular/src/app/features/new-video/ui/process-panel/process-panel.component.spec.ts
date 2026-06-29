import {TestBed} from "@angular/core/testing";
import {beforeEach, describe, expect, it, vi} from "vitest";

import {OllamaModel, WhisperModelOption} from "../../../../shared/models/readvideo-types/readvideo.types";
import {ProcessFormState} from "../../data-access/process-form/process-form.service";
import {ProcessPanelComponent, ProcessPanelViewModel} from "./process-panel.component";

const form: ProcessFormState = {
  url: "",
  notesDir: "",
  transcriptionBackend: "local",
  transcriptionModel: "",
  localWhisperModel: "models/large.bin",
  localWhisperLanguage: "auto",
  notesBackend: "ollama",
  noteStyle: "detailed",
  ollamaModel: "qwen:32b",
  deleteVideoAfterCompletion: false,
};

const whisper: WhisperModelOption = {
  name: "large",
  label: "Large",
  size: "3 GB",
  path: "models/large.bin",
  url: "u",
  notes: "",
  installed: true,
  recommended: true,
};

const ollama: OllamaModel = {
  name: "qwen:32b",
  size: 32,
  size_label: "20 GB",
  modified_at: "",
  family: "qwen",
  parameter_size: "32B",
  quantization_level: "Q4",
};

describe("ProcessPanelComponent", () => {
  let component: ProcessPanelComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({imports: [ProcessPanelComponent]})
      .overrideComponent(ProcessPanelComponent, {set: {template: ""}})
      .compileComponents();
    const fixture = TestBed.createComponent(ProcessPanelComponent);
    const vm: ProcessPanelViewModel = {
      form,
      taskIdLabel: "Task 1",
      config: null,
      whisperModels: [whisper],
      transcriptionLanguages: [{code: "auto", label: "Auto"}],
      whisperStatus: {text: "Ready", kind: "ok"},
      ollamaModels: [ollama],
      ollamaStatus: {text: "Ready", kind: "ok"},
      notice: {text: "Working", kind: "pending"},
      duplicate: null,
      latestTask: {task_id: "1", status: "transcribing"},
      phaseTitle: "transcribing",
      phaseDetail: "Working",
      progressPercent: 50,
      logs: [],
    };
    fixture.componentRef.setInput("vm", vm);
    fixture.detectChanges();
    component = fixture.componentInstance;
  });

  it("marks current, previous, future, and failed steps", () => {
    expect(component.stepClass("queued")).toBe("active");
    expect(component.stepClass("transcribing")).toBe("pending");
    expect(component.stepClass("completed")).toBe("");
  });

  it("emits form patches", () => {
    const patched = vi.fn();
    component.formPatched.subscribe(patched);
    component.patchForm({notesDir: "/notes"});
    expect(patched).toHaveBeenCalledWith({notesDir: "/notes"});
  });

  it("resolves and labels local models", () => {
    expect(component.resolveWhisperModel("large")).toBe(whisper);
    expect(component.resolveOllamaModel("qwen:32b")).toBe(ollama);
    expect(component.whisperModelLabel(whisper)).toBe("Recommended · 3 GB · installed");
    expect(component.modelLabel(ollama)).toBe("20 GB · 32B · Q4");
  });
});
