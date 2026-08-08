"""Companies-owned lifecycle receivers for membership tuple revocation."""

from __future__ import annotations

from typing import Any

from django.apps import apps
from django.db.models.signals import class_prepared, post_delete
from rebac import system_context

from angee.companies.models import CompanyMember

_DISPATCH_PREFIX = "companies.membership_tuples"


def connect() -> None:
    """Bind tuple revocation to every concrete CompanyMember model."""

    for model in apps.get_models():
        _bind(model)
    class_prepared.connect(
        _on_class_prepared,
        dispatch_uid=f"{_DISPATCH_PREFIX}.class_prepared",
    )


def _on_class_prepared(sender: Any, **kwargs: Any) -> None:
    """Bind a newly prepared concrete CompanyMember model."""

    del kwargs
    _bind(sender)


def _bind(model: Any) -> None:
    """Connect the membership delete hook to one concrete model."""

    if model._meta.abstract or not issubclass(model, CompanyMember):
        return
    post_delete.connect(
        revoke_member_tuple,
        sender=model,
        dispatch_uid=f"{_DISPATCH_PREFIX}.delete.{model._meta.label_lower}",
    )


def revoke_member_tuple(sender: Any, instance: Any, **kwargs: Any) -> None:
    """Revoke the deleted membership row's ``member`` tuple.

    Fires for direct deletes and for the CASCADE of a deleted company — the
    collector deletes membership rows (and signals them) before the company row,
    so the related company is still readable here.
    """

    del sender, kwargs
    with system_context(reason="companies.membership.delete"):
        instance.revoke_member_relationship()
