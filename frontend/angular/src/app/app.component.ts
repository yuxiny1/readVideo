import {CommonModule} from "@angular/common";
import {Component, inject, OnInit} from "@angular/core";
import {RouterLink, RouterLinkActive, RouterOutlet} from "@angular/router";

import {TaskWorkflowService} from "./services/task-workflow.service";

@Component({
  selector: "rv-root",
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: "./app.component.html",
})
export class AppComponent implements OnInit {
  readonly workflow = inject(TaskWorkflowService);

  ngOnInit(): void {
    void this.workflow.initialize();
  }
}
