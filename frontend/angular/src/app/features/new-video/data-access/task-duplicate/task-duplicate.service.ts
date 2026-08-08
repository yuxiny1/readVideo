import {Injectable, inject, signal} from "@angular/core";
import {Observable, catchError, map, of} from "rxjs";

import {ReadvideoApiService} from "../../../../core/api/readvideo-api/readvideo-api.service";
import {DuplicateLookup, TaskRecord} from "../../../../shared/models/readvideo-types/readvideo.types";
import {errorMessage} from "../../../../shared/utils/errors/errors";

export type DuplicateDecision =
  | {kind: "continue"}
  | {kind: "missing-local"}
  | {kind: "choose"}
  | {kind: "lookup-failed"; message: string};

@Injectable()
export class TaskDuplicateService {
  private readonly api = inject(ReadvideoApiService);
  readonly lookup = signal<DuplicateLookup | null>(null);
  readonly url = signal("");

  inspect(url: string): Observable<DuplicateDecision> {
    this.clear();
    return this.api.lookupHistory(url).pipe(
      map((lookup) => this.applyLookup(url, lookup)),
      catchError((error) => {
        this.clear();
        return of({kind: "lookup-failed", message: errorMessage(error)} as const);
      }),
    );
  }

  reusableRecord(): TaskRecord | null {
    return this.lookup()?.record ?? null;
  }

  clear(): void {
    this.lookup.set(null);
    this.url.set("");
  }

  private applyLookup(url: string, lookup: DuplicateLookup): DuplicateDecision {
    if (!lookup.found) {
      this.clear();
      return {kind: "continue"};
    }
    if (!lookup.can_reuse) {
      this.clear();
      return {kind: "missing-local"};
    }
    this.lookup.set(lookup);
    this.url.set(url);
    return {kind: "choose"};
  }
}
