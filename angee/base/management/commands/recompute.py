"""Recompute stored computed columns declared by installed models."""

from __future__ import annotations

from typing import Any

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError, CommandParser

from angee.base.computes import compute_models, recompute_model, stored_compute_field_names


class Command(BaseCommand):
    """Idempotent backfill/repair for stored computed columns.

    Instance saves and deletes maintain computed columns automatically; bulk
    paths (``bulk_create``, ``QuerySet.update``) skip signals by design, and a
    newly added stored compute starts with default values on existing rows.
    This command is the whole-table owner for both: it recomputes every row of
    the addressed models and rewrites only rows whose stored value drifted.
    """

    help = "Recompute stored computed columns (backfill new computes, repair bulk-path drift)."

    def add_arguments(self, parser: CommandParser) -> None:
        """Register the model labels, field filter, and batch size."""

        parser.add_argument(
            "labels",
            nargs="*",
            metavar="app_label.ModelName",
            help="Models to recompute; every model declaring computes when omitted.",
        )
        parser.add_argument(
            "--field",
            dest="fields",
            action="append",
            help="Recompute only this computed column (repeatable).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Rows re-read per batch (default 1000).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Dispatch each addressed model to the compute engine's repair pass."""

        del args
        labels: list[str] = options["labels"]
        fields: list[str] | None = options["fields"]
        if labels:
            targets = [apps.get_model(label) for label in labels]
        else:
            targets = list(compute_models())
        for model in targets:
            computed = stored_compute_field_names(model)
            if not computed:
                raise CommandError(f"{model._meta.label} declares no stored computed columns.")
            if fields:
                unknown = sorted(set(fields) - computed)
                if unknown:
                    raise CommandError(f"{model._meta.label} does not compute: {', '.join(unknown)}.")
            written = recompute_model(model, fields, batch_size=options["batch_size"])
            self.stdout.write(f"{model._meta.label}: {written} row(s) updated")
