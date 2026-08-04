"""URL routes contributed by the integrate addon."""

from __future__ import annotations

from django.urls import path

from angee.integrate import appearance

urlpatterns = [
    path("appearance/extract", appearance.extract, name="appearance_extract"),
]
"""The appearance wizard's brand-extraction endpoint. It lives here because this
addon owns outbound HTTP — the fetch runs through the SSRF-pinned client."""
