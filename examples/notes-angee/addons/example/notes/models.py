"""Source models for the notes addon."""

from __future__ import annotations

from django.db import models

from angee.base.computes import compute
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
    versioned through ``revisions`` so edits can be rolled back.
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

    title = models.CharField(max_length=160)
    body = models.TextField(blank=True, default="")
    word_count = models.PositiveIntegerField(default=0, db_index=True, editable=False)
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

    @staticmethod
    def count_words(body: str) -> int:
        """Return the number of whitespace-delimited words in ``body``."""

        return len((body or "").split())

    @compute("word_count", depends=("body",))
    def _compute_word_count(self) -> int:
        """Return the stored word count derived from ``body``."""

        return self.count_words(self.body)
