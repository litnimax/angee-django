import { defineBaseAddon } from "@angee/app";
import { FORM_VIEW_RECORD_CHROME_SLOT } from "@angee/ui";
import { lazyRouteComponent } from "@tanstack/react-router";

import { RecordChrome } from "./RecordChrome";

/** The notes addon: the routed collection surface plus the two views that are
 * not collection kinds — the aggregate overview and the parent graph — each on
 * its own route. The record route nests under the list route; `NotePage` reads
 * its `$id` param. The calendar and timeline need no route of their own: both
 * are collection kinds, so they ride the list's view switcher. */
const notes = defineBaseAddon({
  id: "notes",
  routes: [
    {
      name: "notes.home",
      path: "/notes",
      layout: "console",
      resource: "notes.Note",
      component: lazyRouteComponent(() => import("./NotePage"), "NotePage"),
    },
    {
      name: "notes.overview",
      path: "/notes/overview",
      layout: "console",
      component: lazyRouteComponent(
        () => import("./NoteOverviewPage"),
        "NoteOverviewPage",
      ),
    },
    {
      name: "notes.graph",
      path: "/notes/graph",
      layout: "console",
      component: lazyRouteComponent(() => import("./NoteGraphPage"), "NoteGraphPage"),
    },
    {
      name: "notes.record",
      path: "/notes/$id",
      layout: "console",
      parent: "notes.home",
    },
  ],
  menus: [
    { id: "notes", label: "Notes", route: "notes.home", icon: "notes" },
    { id: "notes.overview", label: "Overview", route: "notes.overview", icon: "layout-dashboard" },
    { id: "notes.graph", label: "Graph", route: "notes.graph", icon: "versions" },
  ],
  // The record-form star/share chrome is host-provided, not baked into base.
  slots: [
    {
      slot: FORM_VIEW_RECORD_CHROME_SLOT,
      id: "notes.record-chrome",
      content: <RecordChrome />,
    },
  ],
});

export default notes;
