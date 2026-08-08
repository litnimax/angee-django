"""Django config for Angee's companies addon."""

from __future__ import annotations

from django.apps import AppConfig


class CompaniesConfig(AppConfig):
    """Source app manifest for the operational company tree."""

    default = True
    name = "angee.companies"

    def ready(self) -> None:
        """Wire companies-owned lifecycle receivers after app population."""

        super().ready()
        # App population phase 1 imports AppConfig before the models exist; defer.
        from angee.companies import signals

        signals.connect()
