import {Injectable, inject} from "@angular/core";
import {Observable, defer, map, of, switchMap} from "rxjs";

import {ReadvideoApiService} from "../../../../core/api/readvideo-api/readvideo-api.service";
import {TaskRecord} from "../../../../shared/models/readvideo-types/readvideo.types";
import {copyTextToClipboard} from "../../../../shared/utils/clipboard/clipboard";

@Injectable()
export class TaskOutputService {
  private readonly api = inject(ReadvideoApiService);

  favorite(taskId: string): Observable<string> {
    return this.api.favoriteTask(taskId).pipe(map(() => "总结已保存到收藏。"));
  }

  copy(task: TaskRecord): Observable<string> {
    const content$ = task.markdown_path
      ? this.api.markdownDocument(task.markdown_path).pipe(
        map((document) => ({content: document.content, notice: "已复制完整 Markdown 笔记。"})),
      )
      : of({content: task.summary ?? "", notice: "已复制总结。"});
    return content$.pipe(
      switchMap(({content, notice}) => defer(() => copyTextToClipboard(content)).pipe(map(() => notice))),
    );
  }
}
