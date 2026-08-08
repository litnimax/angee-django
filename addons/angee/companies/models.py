"""The operational company tree of a multi-company deployment.

A :class:`Company` is the scoping anchor multi-company data hangs from: company-
scoped rows will carry a company FK (``NULL`` = shared across companies), and a
holding's members will see subsidiary data through the tree. This addon owns the
tree itself; the actor context (current/allowed companies), the record-scoping
mixin, and the per-company value primitive are the next slices, per the transfer
decisions recorded in the Odee build state.

A company is an *operational* object — settings, scoping, the visibility
anchor — not a contact-directory entry. Its legal face is the optional
:attr:`Company.organization` link into the parties directory, deliberately
``PROTECT`` on delete: an organization a company points at is removed by first
unlinking it, never by silently blanking the company's legal identity.
"""

from __future__ import annotations

from typing import Any, cast

from django.conf import settings
from django.db import models, transaction
from rebac import (
    RelationshipTuple,
    delete_relationship,
    to_object_ref,
    to_subject_ref,
    write_relationships,
)

from angee.base.mixins import (
    ArchiveMixin,
    ArchiveQuerySet,
    HierarchyMixin,
    HierarchyQuerySet,
)
from angee.base.models import AngeeDataModel, AngeeManager, AngeeQuerySet, role_anchor


class CompanyQuerySet(
    HierarchyQuerySet["Company"],
    ArchiveQuerySet["Company"],
    AngeeQuerySet["Company"],
):
    """Subtree and archive read scopes over the REBAC-scoped company queryset."""


CompanyManager = AngeeManager.from_queryset(CompanyQuerySet)


class Company(HierarchyMixin, ArchiveMixin, AngeeDataModel):
    """One operational company in the deployment's company tree.

    The tree is the mixin's materialized path (``parent`` self-FK + prefix-served
    ``path``); ``hierarchy_scope_fields`` stays empty deliberately — the company
    tree is not scoped by anything, it *is* the scope other trees will name. An
    archived company drops off default pickers and lists (the archive facet) but
    keeps its historical references, matching the transfer decision for Odoo's
    ``active``.
    """

    runtime = True
    sqid_prefix = "cmp_"

    name = models.CharField(max_length=255)
    organization = models.ForeignKey(
        "parties.Organization",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="companies",
    )
    """The company's legal face in the parties directory, when it has one."""

    objects = CompanyManager()

    class Meta(HierarchyMixin.Meta):
        """Django model options carrying the inherited prefix-serving index."""

        abstract = True
        ordering = ("path", "sqid")
        rebac_resource_type = "companies/company"
        rebac_id_attr = "sqid"

    def __str__(self) -> str:
        """Return the company name for Django displays."""

        return self.name


_MEMBER_RELATION = "member"
"""The ``companies/company`` relation a membership row mirrors as a tuple."""


class CompanyMember(AngeeDataModel):
    """One user's membership edge in a company — an immutable grant.

    Membership is an edge, not a document: a row is created and deleted, never
    edited — rewiring a grant is revoke + grant, so the REBAC tuple mirror can
    never drift from a half-updated row (:meth:`save` rejects an edge change).
    Saving a new row writes the company's ``member`` tuple; deletion — including
    the CASCADE from a deleted company — revokes it through the ``post_delete``
    receiver in :mod:`angee.companies.signals`. Unlike the spaces roster, which
    resolves its subject through Party identity and stores a derived
    ``granted_user``, the subject here is the direct ``user`` FK, so no derived
    grantee is needed.
    """

    runtime = True
    sqid_prefix = "cmm_"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_memberships",
    )

    objects = AngeeManager()

    class Meta:
        """Django model options for the canonical company membership edge."""

        abstract = True
        ordering = ("company", "sqid")
        rebac_resource_type = "companies/membership"
        rebac_id_attr = "sqid"
        constraints = (
            models.UniqueConstraint(
                fields=("company", "user"),
                name="uq_%(app_label)s_companymember_company_user",
            ),
        )

    def __str__(self) -> str:
        """Return a readable membership description for Django displays."""

        return f"{self.user_id}∈{self.company_id}"

    @classmethod
    def from_db(cls, db: Any, field_names: Any, values: Any) -> CompanyMember:
        """Snapshot the loaded edge so :meth:`save` can reject a rewire."""

        instance = super().from_db(db, field_names, values)
        if "company_id" in field_names and "user_id" in field_names:
            instance._loaded_edge = (instance.company_id, instance.user_id)
        return cast(CompanyMember, instance)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Persist the row and write its ``member`` tuple atomically on create."""

        if not self._state.adding:
            loaded = getattr(self, "_loaded_edge", None)
            if loaded is not None and loaded != (self.company_id, self.user_id):
                raise ValueError(
                    "CompanyMember is an immutable edge: revoke and grant a new "
                    "membership instead of editing this one."
                )
            super().save(*args, **kwargs)
            return
        with transaction.atomic():
            super().save(*args, **kwargs)
            write_relationships(
                [
                    RelationshipTuple(
                        resource=to_object_ref(self.company),
                        relation=_MEMBER_RELATION,
                        subject=to_subject_ref(self.user),
                    )
                ]
            )
        self._loaded_edge = (self.company_id, self.user_id)

    def revoke_member_relationship(self) -> None:
        """Revoke this row's ``member`` tuple (the ``post_delete`` receiver's body)."""

        delete_relationship(
            RelationshipTuple(
                resource=to_object_ref(self.company),
                relation=_MEMBER_RELATION,
                subject=to_subject_ref(self.user),
            )
        )


CompaniesRole = role_anchor("companies/role")
"""The ``companies/role`` anchor: its const ``admin`` arm resolves a platform
admin as an effective company manager. See :func:`angee.base.models.role_anchor`.
"""
