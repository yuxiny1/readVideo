import "zone.js";

import {provideHttpClient} from "@angular/common/http";
import {bootstrapApplication} from "@angular/platform-browser";
import {provideRouter} from "@angular/router";

import {routes} from "../../app/routing/app-routes/app.routes";
import {AppComponent} from "../../app/shell/app-shell/app.component";

bootstrapApplication(AppComponent, {
  providers: [provideHttpClient(), provideRouter(routes)],
}).catch((error) => console.error(error));
