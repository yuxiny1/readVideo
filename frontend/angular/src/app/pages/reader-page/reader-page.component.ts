import {CommonModule} from "@angular/common";
import {Component, inject, OnInit, signal} from "@angular/core";
import {ActivatedRoute, RouterLink} from "@angular/router";
import {DomSanitizer, SafeHtml} from "@angular/platform-browser";

import {ReadvideoApiService} from "../../services/readvideo-api.service";

@Component({
  selector: "rv-reader-page",
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: "./reader-page.component.html",
})
export class ReaderPageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(ReadvideoApiService);
  private readonly sanitizer = inject(DomSanitizer);

  readonly status = signal("Idle");
  readonly path = signal("");
  readonly html = signal<SafeHtml>("");

  ngOnInit(): void {
    this.route.queryParamMap.subscribe((params) => {
      const path = params.get("path") || "";
      if (path) void this.openPath(path);
    });
  }

  async openPath(path: string): Promise<void> {
    this.status.set("Loading");
    this.path.set(path);
    try {
      const document = await this.api.markdownDocument(path);
      this.path.set(document.path);
      this.html.set(this.sanitizer.bypassSecurityTrustHtml(this.renderMarkdown(document.content)));
      this.status.set("Open");
    } catch (error) {
      this.status.set("Error");
      const message = error instanceof Error ? error.message : String(error);
      this.html.set(this.sanitizer.bypassSecurityTrustHtml(`<div class="empty-state">${this.escapeHtml(message)}</div>`));
    }
  }

  private renderMarkdown(markdown: string): string {
    return markdown
      .split(/\n{2,}/)
      .map((block) => {
        const text = block.trim();
        if (!text) return "";
        const heading = text.match(/^(#{1,3})\s+(.+)$/);
        if (heading) {
          const level = heading[1].length;
          return `<h${level}>${this.escapeHtml(heading[2])}</h${level}>`;
        }
        if (text.startsWith("- ")) {
          const items = text.split(/\r?\n/).map((line) => `<li>${this.escapeHtml(line.replace(/^[-*]\s+/, ""))}</li>`).join("");
          return `<ul>${items}</ul>`;
        }
        return `<p>${this.escapeHtml(text)}</p>`;
      })
      .join("");
  }

  private escapeHtml(value: string): string {
    return value.replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[char] || char));
  }
}
