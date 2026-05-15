import "zone.js";

import {bootstrapApplication} from "@angular/platform-browser";
import {FormsModule} from "@angular/forms";
import {importProvidersFrom} from "@angular/core";
import {provideRouter} from "@angular/router";

import {AppComponent} from "./app/app.component";
import {routes} from "./app/app.routes";

bootstrapApplication(AppComponent, {
  providers: [importProvidersFrom(FormsModule), provideRouter(routes)],
}).catch((error) => console.error(error));
