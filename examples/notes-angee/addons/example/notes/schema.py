"""Strawberry-Django schema contributions for notes."""

from __future__ import annotations

from typing import Any, cast

import strawberry
import strawberry_django
from django.apps import apps
from django.db import models
from strawberry import auto

from angee.graphql.data import AngeeHasuraWriteBackend, hasura_model_resource, public_pk_decoder
from angee.graphql.deletion import DeletePreview, attach_delete_preview_metadata, delete_by_public_id
from angee.graphql.ids import PublicID, to_public_id
from angee.graphql.node import AngeeNode
from angee.graphql.revisions import revisions
from angee.graphql.subscriptions import changes
from angee.graphql.writes import write_queryset
from angee.iam.audit import AuthoredRefMixin

Note = apps.get_model("notes", "Note")


@strawberry_django.type(Note)
class NoteType(AuthoredRefMixin, AngeeNode):
    """GraphQL projection of a note."""

    title: auto
    body: auto
    status: auto
    tags: auto
    is_starred: auto
    reminder_at: auto
    created_at: auto
    updated_at: auto
    word_count: auto

    @strawberry_django.field(only=["parent_id"])
    def parent(self) -> strawberry.ID | None:
        """Return the parent note's public id, if the note hangs under one."""

        return to_public_id(Note, cast(Any, self).parent_id)


def _note_queryset(info: strawberry.Info) -> models.QuerySet[Note]:
    """Return the actor-scoped note queryset for row reads."""

    del info
    return Note.objects.all()


def _note_aggregate_queryset(info: strawberry.Info) -> models.QuerySet[Note]:
    """Return the row-scoped queryset safe for aggregate/group math."""

    del info
    return Note.objects.all().scoped_for_aggregate()


@strawberry.type
class NoteDeletePreviewMutation:
    """Authored delete-preview operation for notes."""

    @strawberry.mutation(name="delete_note")
    def delete_note(self, id: PublicID, confirm: bool = False) -> DeletePreview:
        """Preview or confirm deletion of one note by public id."""

        return delete_by_public_id(
            Note,
            str(id),
            confirm=confirm,
            queryset=write_queryset(Note),
        )


NoteDeletePreviewMutation = attach_delete_preview_metadata(
    NoteDeletePreviewMutation,
    model=Note,
    node=NoteType,
    field="delete_note",
)


_NOTE_RESOURCE = hasura_model_resource(
    NoteType,
    model=Note,
    name="notes",
    # `reminder_at` is filterable so the calendar can ask for one visible window;
    # `parent` so the graph view can pull a subtree and the form can pick a parent.
    filterable=["id", "title", "status", "tags", "is_starred", "updated_at", "reminder_at", "parent"],
    sortable=["title", "status", "updated_at", "created_at", "word_count", "reminder_at"],
    aggregatable=["id", "word_count"],
    groupable=["status", "tags", "updated_at"],
    writable=["title", "body", "status", "tags", "is_starred", "reminder_at", "parent"],
    field_id_decode={"parent": public_pk_decoder(Note)},
    # A writable relation is addressed by the related row's public id, so the
    # write backend has to decode `parent` back to a pk before it saves.
    write_backend=AngeeHasuraWriteBackend(Note, public_id_fields=("parent",)),
    get_queryset=_note_queryset,
    get_aggregate_queryset=_note_aggregate_queryset,
    id_column="sqid",
)


_NOTE_SCHEMA_BUCKET = {
    "query": [_NOTE_RESOURCE.query, revisions(NoteType)],
    "mutation": [_NOTE_RESOURCE.mutation, NoteDeletePreviewMutation],
    "types": [NoteType, *_NOTE_RESOURCE.types],
}


schemas = {
    "public": {
        **_NOTE_SCHEMA_BUCKET,
    },
    "console": {
        **_NOTE_SCHEMA_BUCKET,
        "subscription": [changes(Note, field="noteChanged")],
    },
}
