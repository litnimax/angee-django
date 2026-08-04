"""AppConfig for the stored-compute demo (test-only installed app).

Registered in ``tests.settings`` so pytest-django creates the demo tables that
exercise :mod:`angee.base.computes` — local recompute on save with
``update_fields`` fan-out, cross-model propagation through reverse-FK,
forward-FK, and many-to-many depends paths, ``related()`` copies, delete
propagation, and the bulk repair pass. The app carries no ``addon.toml``; it is
a plain Django app, not an Angee addon, so the composer and schema discovery
ignore it.
"""

from __future__ import annotations

from django.apps import AppConfig


class ComputeDemoConfig(AppConfig):
    """Installed app hosting the stored-compute demo models."""

    name = "tests.computedemo"
    label = "computedemo"
    default_auto_field = "django.db.models.BigAutoField"
