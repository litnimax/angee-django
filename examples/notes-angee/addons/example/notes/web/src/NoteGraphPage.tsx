import * as React from "react";
import { useNavigate } from "@tanstack/react-router";
import { useAuthoredQuery } from "@angee/refine";
import {
  EmptyState,
  ErrorBanner,
  GraphView,
  LoadingPanel,
  errorMessage,
  type GraphViewEdge,
  type GraphViewNode,
  type GraphViewNodeStyle,
} from "@angee/ui";

import { NotesGraph } from "./documents";
import { NOTES_BASE_PATH } from "./note-calendar";

const MODEL = "notes.Note";
const GRAPH_LIMIT = 200;

/** A note with no parent is a root; the distinction is the only thing the graph
 * styles differently, so it doubles as the node kind. */
type NoteNodeKind = "root" | "child";

const NODE_STYLES: Record<NoteNodeKind, GraphViewNodeStyle> = {
  root: {
    width: 208,
    height: 64,
    borderColor: "var(--border-strong)",
    badgeTone: "info",
  },
  child: {
    width: 208,
    height: 64,
    borderColor: "var(--border-subtle)",
    badgeTone: "neutral",
  },
};

/**
 * The notes forest — one node per note, one edge per `parent` link. The graph is
 * derived from a single flat read: the rows are the nodes, and the rows that
 * carry a `parent` are the edges. An edge whose parent fell outside the fetched
 * page is dropped, so the graph never references a node it does not render.
 */
export function NoteGraphPage(): React.ReactElement {
  const navigate = useNavigate();
  const variables = React.useMemo(() => ({ limit: GRAPH_LIMIT }), []);
  const query = useAuthoredQuery(NotesGraph, variables, { models: [MODEL] });
  const notes = query.data?.notes;

  const nodes = React.useMemo<readonly GraphViewNode<NoteNodeKind>[]>(
    () =>
      (notes ?? []).map((note) => ({
        id: note.id,
        kind: note.parent ? "child" : "root",
        title: note.title,
        code: String(note.status),
      })),
    [notes],
  );

  const edges = React.useMemo<readonly GraphViewEdge<"parent">[]>(() => {
    const present = new Set((notes ?? []).map((note) => note.id));
    return (notes ?? [])
      .filter((note) => note.parent != null && present.has(String(note.parent)))
      .map((note) => ({
        id: `${String(note.parent)}->${note.id}`,
        source: String(note.parent),
        target: note.id,
        kind: "parent" as const,
      }));
  }, [notes]);

  if (query.error) {
    return <ErrorBanner description={errorMessage(query.error, "The note graph failed to load.")} />;
  }
  if (query.fetching && nodes.length === 0) {
    return <LoadingPanel message="Loading the note graph…" />;
  }
  if (nodes.length === 0) {
    return (
      <EmptyState
        fill
        icon="notes"
        title="No notes to graph"
        description="Create a note, then give it a parent to see the tree take shape."
      />
    );
  }

  return (
    <div className="console-route-viewport bg-sheet">
      <GraphView<NoteNodeKind, "parent">
        nodes={nodes}
        edges={edges}
        nodeStyles={NODE_STYLES}
        layout={{ rankdir: "TB" }}
        className="console-route-canvas"
        onNodeClick={(node) =>
          navigate({ to: `${NOTES_BASE_PATH}/$id`, params: { id: node.id } })
        }
      />
    </div>
  );
}
