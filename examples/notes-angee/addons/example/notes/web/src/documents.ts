// Console-schema operations for the notes surfaces that read something other
// than the standard resource list: the calendar's per-window fetch, the parent
// graph, and the overview aggregates. The routed list, the record form and the
// timeline kind need none of these — they ride the generated resource roots.
// Globbed against the `console` runtime schema by the per-schema codegen.

import { graphql } from "@angee/gql/console";

/**
 * One visible calendar window. `reminder_at` is the note's only event-shaped
 * field, so the window filter is a half-open range over it — start inclusive,
 * end exclusive, matching the calendar window contract.
 */
export const NotesCalendarWindow = graphql(`
  query NotesCalendarWindow($window_start: DateTime!, $window_end: DateTime!) {
    notes(
      where: { reminder_at: { _gte: $window_start, _lt: $window_end } }
      order_by: [{ reminder_at: asc }]
    ) {
      id
      title
      status
      reminder_at
    }
  }
`);

/**
 * Move one note's reminder — the calendar's drag/resize write. The grid awaits
 * this before it settles, so a rejected write reverts the optimistic move.
 */
export const NotesReschedule = graphql(`
  mutation NotesReschedule($id: String!, $reminder_at: DateTime) {
    update_notes_by_pk(pk_columns: { id: $id }, _set: { reminder_at: $reminder_at }) {
      id
      reminder_at
    }
  }
`);

/**
 * Every note with the edge that links it to its parent. The graph is built
 * client-side from this one flat read: nodes are the rows, edges are the rows
 * that carry a `parent`.
 */
export const NotesGraph = graphql(`
  query NotesGraph($limit: Int = 200) {
    notes(limit: $limit, order_by: [{ title: asc }]) {
      id
      title
      status
      parent
    }
  }
`);

/** The overview metric band: totals plus the per-status split. */
export const NotesOverview = graphql(`
  query NotesOverview {
    notes_aggregate {
      aggregate {
        count
        sum {
          word_count
        }
        avg {
          word_count
        }
      }
    }
    starred: notes_aggregate(where: { is_starred: { _eq: true } }) {
      aggregate {
        count
      }
    }
    notes_groups(group_by: [{ field: STATUS }]) {
      key {
        status
      }
      aggregate {
        count
        sum {
          word_count
        }
      }
    }
  }
`);
