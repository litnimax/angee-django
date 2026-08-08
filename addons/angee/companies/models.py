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

from django.db import models

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


CompaniesRole = role_anchor("companies/role")
"""The ``companies/role`` anchor: its const ``admin`` arm resolves a platform
admin as an effective company manager. See :func:`angee.base.models.role_anchor`.
"""
