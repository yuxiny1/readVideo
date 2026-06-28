import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, computed, inject, OnInit} from "@angular/core";
import {Router} from "@angular/router";

import {LatestOutputComponent, LatestOutputViewModel} from "../../components/latest-output/latest-output.component";
import {
  DuplicateAction,
  ProcessPanelComponent,
  ProcessPanelViewModel,
} from "../../components/process-panel/process-panel.component";
import {SavedSourcesComponent} from "../../components/saved-sources/saved-sources.component";
import {LocalModelsService} from "../../services/local-models.service";
import {ProcessFormService, ProcessFormState} from "../../services/process-form.service";
import {TaskWorkflowService} from "../../services/task-workflow.service";

@Component({
  selector: "rv-new-video-page",
  standalone: true,
  imports: [CommonModule, ProcessPanelComponent, LatestOutputComponent, SavedSourcesComponent],
  templateUrl: "./new-video-page.component.html",
  providers: [ProcessFormService, LocalModelsService, TaskWorkflowService],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NewVideoPageComponent implements OnInit {
  private readonly router = inject(Router);
  readonly form = inject(ProcessFormService);
  readonly models = inject(LocalModelsService);
  readonly workflow = inject(TaskWorkflowService);
  readonly processPanelVm = computed<ProcessPanelViewModel>(() => ({
    form: this.form.form(),
    taskIdLabel: this.workflow.taskIdLabel(),
    config: this.models.config(),
    whisperModels: this.models.whisperModels(),
    transcriptionLanguages: this.models.transcriptionLanguages(),
    whisperStatus: this.models.whisperStatus(),
    ollamaModels: this.models.ollamaModelOptions(),
    ollamaStatus: this.models.ollamaStatus(),
    notice: this.workflow.notice(),
    duplicate: this.workflow.duplicate(),
    latestTask: this.workflow.latestTask(),
    phaseTitle: this.workflow.phaseTitle(),
    phaseDetail: this.workflow.phaseDetail(),
    progressPercent: this.workflow.progressPercent(),
    logs: this.workflow.logs(),
  }));
  readonly latestOutputVm = computed<LatestOutputViewModel>(() => ({
    task: this.workflow.latestTask(),
    summary: this.workflow.latestSummary(),
    recentTasks: this.workflow.recentTasks(),
    canCopy: this.workflow.canCopyLatestOutput(),
  }));

  ngOnInit(): void {
    this.workflow.initialize();
  }

  patchForm(update: Partial<ProcessFormState>): void {
    this.form.patch(update);
    if (update.localWhisperModel !== undefined) this.models.validateWhisperSelection();
    if (update.ollamaModel !== undefined) this.models.validateOllamaSelection();
  }

  handleDuplicateAction(action: DuplicateAction): void {
    if (action === "use") this.workflow.useExistingDuplicateOutput();
    if (action === "regenerate") this.workflow.regenerateDuplicateSummary();
    if (action === "redownload") this.workflow.forceDuplicateRedownload();
  }

  openReader(path: string): void {
    void this.router.navigate(["/reader"], {queryParams: {path}});
  }
}
