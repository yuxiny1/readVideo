import {CommonModule} from "@angular/common";
import {Component, inject} from "@angular/core";

import {LatestOutputComponent} from "../../components/latest-output/latest-output.component";
import {ProcessPanelComponent} from "../../components/process-panel/process-panel.component";
import {SavedSourcesComponent} from "../../components/saved-sources/saved-sources.component";
import {TaskWorkflowService} from "../../services/task-workflow.service";

@Component({
  selector: "rv-new-video-page",
  standalone: true,
  imports: [CommonModule, ProcessPanelComponent, LatestOutputComponent, SavedSourcesComponent],
  templateUrl: "./new-video-page.component.html",
})
export class NewVideoPageComponent {
  readonly workflow = inject(TaskWorkflowService);
}
