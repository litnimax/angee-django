import * as React from "react";
import { useAuthoredQuery } from "@angee/refine";
import {
  DashboardView,
  ErrorBanner,
  InlineEmpty,
  Metric,
  MiniCard,
  RailPanel,
  errorMessage,
} from "@angee/ui";

import { NotesOverview } from "./documents";

const MODEL = "notes.Note";

/** Render a metric value, or a placeholder while the aggregate is in flight.
 * A `BigInt` sum arrives as a string, so the value stays unparsed. */
function metricValue(
  value: number | string | null | undefined,
  fetching: boolean,
): string {
  if (fetching && value == null) return "—";
  return String(value ?? 0);
}

/**
 * The notes overview — the aggregate face of the same collection the list
 * renders. Every number comes from one authored aggregate read, so the page
 * never counts rows client-side.
 */
export function NoteOverviewPage(): React.ReactElement {
  const query = useAuthoredQuery(NotesOverview, {}, { models: [MODEL] });
  const aggregate = query.data?.notes_aggregate.aggregate;
  const starred = query.data?.starred.aggregate.count;
  const groups = query.data?.notes_groups ?? [];
  const averageWords = aggregate?.avg?.word_count;

  if (query.error) {
    return <ErrorBanner description={errorMessage(query.error, "The overview failed to load.")} />;
  }

  return (
    <DashboardView>
      <Metric
        label="Notes"
        value={metricValue(aggregate?.count, query.fetching)}
        icon="notes"
      />
      <Metric
        label="Words"
        value={metricValue(aggregate?.sum?.word_count, query.fetching)}
        icon="file"
        detail={
          averageWords == null ? undefined : `${Math.round(averageWords)} per note on average`
        }
      />
      <Metric
        label="Starred"
        value={metricValue(starred, query.fetching)}
        icon="star"
        tone="warning"
      />
      <Metric
        label="Statuses"
        value={metricValue(groups.length, query.fetching)}
        icon="activity"
      />
      <RailPanel title="By status" count={groups.length} fetching={query.fetching}>
        {groups.length > 0 ? (
          <div className="grid gap-2">
            {groups.map((group) => (
              <MiniCard
                key={String(group.key.status)}
                title={String(group.key.status)}
                meta={`${group.aggregate.sum?.word_count ?? 0} words`}
                primaryTag={{ label: String(group.aggregate.count), tone: "neutral" }}
              />
            ))}
          </div>
        ) : (
          <InlineEmpty label="No notes yet" />
        )}
      </RailPanel>
    </DashboardView>
  );
}
