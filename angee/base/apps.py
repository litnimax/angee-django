"""AppConfig for the Angee model foundation."""

from __future__ import annotations

from django.apps import AppConfig


class BaseConfig(AppConfig):
    """Installed app config owning the model toolkit's runtime seams."""

    default = True
    name = "angee.base"

    def ready(self) -> None:
        """Warm the computed-field dependency index over the loaded app registry.

        Building the index binds the per-sender propagation receivers, so it
        must happen before the first delete in the process — a fresh process
        deciding fast-delete for a dependency source would otherwise skip the
        signals the engine listens on.
        """

        super().ready()
        # Deferred: an AppConfig module is imported in app-populate phase 1,
        # before the model registry is ready, so the model-importing seam loads here.
        from angee.base import computes

        computes.compute_registry.ensure()
