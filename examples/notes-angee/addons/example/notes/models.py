"""Source models for the notes addon."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models

from angee.base.fields import StateField
from angee.base.mixins import (
    AuditMixin,
    HistoryMixin,
    RevisionMixin,
    SqidMixin,
)
from angee.base.models import AngeeModel
from angee.messaging.models import ThreadedModelMixin


class Note(SqidMixin, AuditMixin, ThreadedModelMixin, AngeeModel, HistoryMixin, RevisionMixin):
    """A short note used to exercise backend composition.

    Metadata changes are audited through ``history``; the ``body`` field is
    versioned through ``revisions`` so edits can be rolled back. ``parent``
    makes notes a forest — a note may hang under another, and the graph view
    renders those edges. Deleting a parent orphans its children rather than
    taking them with it (``SET_NULL``): a note is content, not a container.
    """

    runtime = True

    revisioned_fields = ("body",)

    sqid_prefix = "nte_"

    class Status(models.TextChoices):
        """Lifecycle states a note moves through."""

        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In Review"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    title = models.CharField(max_length=160)
    body = models.TextField(blank=True, default="")
    word_count = models.PositiveIntegerField(default=0, db_index=True)
    status = StateField(choices_enum=Status, default=Status.DRAFT)
    tags = models.JSONField(blank=True, default=list)
    is_starred = models.BooleanField(default=False, db_index=True)
    reminder_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        """Django model options."""

        abstract = True
        ordering = ("-updated_at", "title", "sqid")
        rebac_resource_type = "notes/note"
        rebac_id_attr = "sqid"

    def __str__(self) -> str:
        """Return the note title for Django displays."""

        return self.title

    def clean(self) -> None:
        """Reject a ``parent`` chain that would make the note its own ancestor.

        Nothing else guards this: the FK happily stores a cycle, and a cycle
        would strand its notes outside every root the graph view walks from.
        """

        super().clean()
        ancestor = self.parent
        while ancestor is not None:
            if ancestor.pk == self.pk:
                raise ValidationError({"parent": "A note cannot be its own ancestor."})
            ancestor = ancestor.parent

    @staticmethod
    def count_words(body: str) -> int:
        """Return the number of whitespace-delimited words in ``body``."""

        return len((body or "").split())

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Persist the current number of whitespace-delimited body words."""

        self.word_count = self.count_words(self.body)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            field_names = set(update_fields)
            if "body" in field_names:
                field_names.add("word_count")
                field_names.add("updated_at")
                kwargs["update_fields"] = field_names
        super().save(*args, **kwargs)
