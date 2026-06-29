import {signal} from "@angular/core";
import {TestBed} from "@angular/core/testing";
import {Router} from "@angular/router";
import {describe, expect, it, vi} from "vitest";

import {LocalModelsService} from "../../data-access/local-models/local-models.service";
import {ProcessFormService, ProcessFormState} from "../../data-access/process-form/process-form.service";
import {TaskWorkflowService} from "../../data-access/task-workflow/task-workflow.service";
import {NewVideoPageComponent} from "./new-video-page.component";

const formState: ProcessFormState = {
  url: "",
  notesDir: "",
  transcriptionBackend: "local",
  transcriptionModel: "",
  localWhisperModel: "model.bin",
  localWhisperLanguage: "auto",
  notesBackend: "ollama",
  noteStyle: "detailed",
  ollamaModel: "qwen:32b",
  deleteVideoAfterCompletion: false,
};

describe("NewVideoPageComponent", () => {
  it("connects form, model, workflow, duplicate, and Reader actions", async () => {
    const form = {form: signal(formState), patch: vi.fn()};
    const models = {
      config: signal(null),
      whisperModels: signal([]),
      transcriptionLanguages: signal([]),
      whisperStatus: signal({text: "Ready", kind: "ok"}),
      ollamaModelOptions: signal([]),
      ollamaStatus: signal({text: "Ready", kind: "ok"}),
      validateWhisperSelection: vi.fn(),
      validateOllamaSelection: vi.fn(),
    };
    const workflow = {
      taskIdLabel: signal(""),
      notice: signal({text: "Idle", kind: "muted"}),
      duplicate: signal(null),
      latestTask: signal(null),
      phaseTitle: signal("idle"),
      phaseDetail: signal("No active task"),
      progressPercent: signal(0),
      logs: signal([]),
      latestSummary: signal(""),
      recentTasks: signal([]),
      canCopyLatestOutput: signal(false),
      initialize: vi.fn(),
      useExistingDuplicateOutput: vi.fn(),
      regenerateDuplicateSummary: vi.fn(),
      forceDuplicateRedownload: vi.fn(),
    };
    const router = {navigate: vi.fn(() => Promise.resolve(true))};

    await TestBed.configureTestingModule({
      imports: [NewVideoPageComponent],
      providers: [{provide: Router, useValue: router}],
    }).overrideComponent(NewVideoPageComponent, {
      set: {template: "", providers: [
        {provide: ProcessFormService, useValue: form},
        {provide: LocalModelsService, useValue: models},
        {provide: TaskWorkflowService, useValue: workflow},
      ]},
    }).compileComponents();
    const fixture = TestBed.createComponent(NewVideoPageComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();

    expect(workflow.initialize).toHaveBeenCalledOnce();
    expect(component.processPanelVm().form).toEqual(formState);
    component.patchForm({localWhisperModel: "large.bin", ollamaModel: "strong:32b"});
    expect(form.patch).toHaveBeenCalled();
    expect(models.validateWhisperSelection).toHaveBeenCalledOnce();
    expect(models.validateOllamaSelection).toHaveBeenCalledOnce();

    component.handleDuplicateAction("use");
    component.handleDuplicateAction("regenerate");
    component.handleDuplicateAction("redownload");
    expect(workflow.useExistingDuplicateOutput).toHaveBeenCalledOnce();
    expect(workflow.regenerateDuplicateSummary).toHaveBeenCalledOnce();
    expect(workflow.forceDuplicateRedownload).toHaveBeenCalledOnce();

    component.openReader("/notes/a.md");
    expect(router.navigate).toHaveBeenCalledWith(["/reader"], {queryParams: {path: "/notes/a.md"}});
  });
});
