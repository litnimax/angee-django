import { calendarWindowBounds, calendarWindowSource, recordPath } from "@angee/ui";
import type { AnyCalendarWindowSource, Occurrence } from "@angee/ui";

import { NotesCalendarWindow } from "./documents";

export const NOTES_BASE_PATH = "/notes";

/**
 * The note calendar's one occurrence source.
 *
 * A note carries `reminder_at` — a moment, not an interval — so an occurrence
 * spans zero time (`end === start`) rather than inventing a duration the model
 * does not store. Nothing here expands a recurrence: a note has none, so every
 * row maps to at most one editable occurrence and drag/resize writes straight
 * back to `reminder_at`.
 *
 * A row can arrive with `reminder_at: null` even though the window filter
 * matched it: `read__reminder_at = owner` in the REBAC schema masks the field
 * for everyone but the note's owner, and the filter runs against the stored
 * value while the projection is actor-scoped. Such a row is dropped — a note
 * whose reminder the actor may not read has no place on their grid, and
 * substituting any other instant would invent an event.
 */
export const noteCalendarSource: AnyCalendarWindowSource = calendarWindowSource({
  document: NotesCalendarWindow,
  variables: (window) => calendarWindowBounds(window),
  select: (data) =>
    data?.notes.flatMap((note): Occurrence[] =>
      note.reminder_at == null
        ? []
        : [
            {
              occurrence_id: note.id,
              event_sqid: note.id,
              title: note.title,
              start: note.reminder_at,
              end: note.reminder_at,
              all_day: false,
              editable: true,
              to: recordPath(NOTES_BASE_PATH, note.id),
            },
          ],
    ),
  models: ["notes.Note"],
});
