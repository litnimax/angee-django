"""Tests for the companies addon — what the composition adds over its mixins.

Tree mechanics (padded paths, cycle rejection, reparent cascades) are
:class:`~angee.base.mixins.HierarchyMixin` property and covered by
``test_hierarchy``; archive semantics are covered by the archive suite. Here we
cover the composition itself: the subtree scope reading on ``Company``, the
explicit (never implicit) archive scopes, the ``PROTECT`` organization link,
and the inherited prefix-serving path index. Rows are created under
``system_context`` because the write surface is admin-only (strict REBAC),
mirroring the uom tests.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from django.core.management import call_command
from django.db import connection, transaction
from django.db.models import ProtectedError
from rebac import PermissionDenied, actor_context, system_context

from angee.base.indexes import PatternOpsIndex
from angee.companies.models import Company as AbstractCompany
from angee.companies.models import CompanyMember as AbstractCompanyMember
from tests.conftest import _clear_model_tables, _create_missing_tables, create_user
from tests.test_messaging import Organization, Party


class Company(AbstractCompany):
    """Concrete company used by companies tests."""

    class Meta(AbstractCompany.Meta):
        """Django model options for the canonical test company."""

        abstract = False
        app_label = "companies"
        db_table = "test_companies_company"
        rebac_resource_type = "companies/company"
        rebac_id_attr = "sqid"


class CompanyMember(AbstractCompanyMember):
    """Concrete company membership edge used by companies tests."""

    class Meta(AbstractCompanyMember.Meta):
        """Django model options for the canonical test membership."""

        abstract = False
        app_label = "companies"
        db_table = "test_companies_companymember"
        rebac_resource_type = "companies/membership"
        rebac_id_attr = "sqid"


COMPANIES_TEST_MODELS = (Party, Organization, Company, CompanyMember)
"""Concrete models created on demand by companies test fixtures."""


@pytest.fixture()
def companies_tables(transactional_db: Any) -> Iterator[None]:
    """Create the concrete companies (and parties) tables for one test.

    ``rebac sync`` loads the revision-2 schema into the engine — without it the
    membership/arrow read paths below would deny everything and every authz
    assertion would pass for the wrong reason.
    """

    del transactional_db
    created_models = _create_missing_tables(COMPANIES_TEST_MODELS)
    call_command("rebac", "sync", verbosity=0)
    try:
        yield
    finally:
        _clear_model_tables(COMPANIES_TEST_MODELS)
        if created_models:
            with connection.schema_editor() as schema_editor:
                for model in reversed(created_models):
                    schema_editor.delete_model(model)


def _make_company(**fields: Any) -> Any:
    """Create one Company under system_context (admin-only surface)."""

    with system_context(reason="companies tests setup"):
        return Company.objects.create(**fields)


def test_subtree_scope_reads_the_company_tree(companies_tables: None) -> None:
    """``subtree_of`` composes onto Company: a holding spans its subsidiaries."""

    holding = _make_company(name="Holding")
    subsidiary = _make_company(name="Subsidiary", parent=holding)
    grandchild = _make_company(name="Grandchild", parent=subsidiary)
    unrelated = _make_company(name="Unrelated")

    with system_context(reason="companies tests read"):
        subtree = set(Company.objects.subtree_of(holding))
        ancestors = set(Company.objects.ancestors_of(grandchild))

    assert subtree == {holding, subsidiary, grandchild}
    assert unrelated not in subtree
    assert ancestors == {holding, subsidiary}


def test_archive_scopes_are_explicit_not_implicit(companies_tables: None) -> None:
    """The default queryset sees archived rows; hiding them is an explicit scope."""

    active = _make_company(name="Active")
    archived = _make_company(name="Wound down", is_archived=True)

    with system_context(reason="companies tests read"):
        assert set(Company.objects.all()) == {active, archived}
        assert set(Company.objects.unarchived()) == {active}
        assert set(Company.objects.archived()) == {archived}


def test_organization_link_is_protected(companies_tables: None) -> None:
    """Deleting a linked organization requires unlinking it first — never SET_NULL."""

    with system_context(reason="companies tests setup"):
        organization = Organization.objects.create(
            display_name="Acme Holding",
            legal_name="Acme Holding LLC",
        )
        company = Company.objects.create(name="Acme", organization=organization)

        with pytest.raises(ProtectedError), transaction.atomic():
            organization.delete()

        company.organization = None
        company.save(update_fields=["organization"])
        organization.delete()
        company.refresh_from_db()

    assert company.organization is None


def test_meta_carries_the_prefix_serving_path_index() -> None:
    """The concrete model keeps HierarchyMixin's pattern-ops index via Meta inheritance."""

    assert any(
        isinstance(index, PatternOpsIndex) for index in Company._meta.indexes
    )


def _grant(company: Any, user: Any) -> Any:
    """Create one membership edge under system_context (admin-only surface)."""

    with system_context(reason="companies tests setup"):
        return CompanyMember.objects.create(company=company, user=user)


def _visible_companies(user: Any) -> set[Any]:
    """Return the companies the actor's REBAC-scoped default queryset reads."""

    with actor_context(user):
        return set(Company.objects.all())


def test_membership_grants_and_revokes_company_read(companies_tables: None) -> None:
    """Revision 2: a plain authenticated actor reads only companies they belong to."""

    company = _make_company(name="Acme")
    outsider = create_user("outsider")
    member = create_user("member")

    assert _visible_companies(outsider) == set()
    assert _visible_companies(member) == set()

    membership = _grant(company, member)
    assert _visible_companies(member) == {company}
    assert _visible_companies(outsider) == set()

    with system_context(reason="companies tests teardown"):
        membership.delete()
    assert _visible_companies(member) == set()


def test_parent_arrow_carries_read_down_the_subtree(companies_tables: None) -> None:
    """A holding's member reads grandchildren too; the arrow never climbs up."""

    holding = _make_company(name="Holding")
    subsidiary = _make_company(name="Subsidiary", parent=holding)
    grandchild = _make_company(name="Grandchild", parent=subsidiary)

    holding_member = create_user("holding_member")
    grandchild_member = create_user("grandchild_member")
    _grant(holding, holding_member)
    _grant(grandchild, grandchild_member)

    # Two parent hops: the recursive `parent->read` reaches the grandchild —
    # a one-level formulation (`parent->member`) would fail exactly here.
    assert _visible_companies(holding_member) == {holding, subsidiary, grandchild}
    # The arrow points up the tree for the reader, never down: a subsidiary
    # member gains nothing above their company.
    assert _visible_companies(grandchild_member) == {grandchild}


def test_cascade_delete_revokes_member_tuples(companies_tables: None) -> None:
    """Deleting a company cascades its memberships and their tuples with it."""

    holding = _make_company(name="Holding")
    subsidiary = _make_company(name="Subsidiary", parent=holding)
    member = create_user("cascade_member")
    _grant(subsidiary, member)
    assert _visible_companies(member) == {subsidiary}

    with system_context(reason="companies tests teardown"):
        Company.objects.get(pk=subsidiary.pk).delete()
    assert _visible_companies(member) == set()


def test_membership_edge_is_immutable(companies_tables: None) -> None:
    """Rewiring an existing membership row is rejected — revoke and grant instead."""

    company = _make_company(name="Acme")
    other = _make_company(name="Globex")
    member = create_user("immutable_member")
    _grant(company, member)

    with system_context(reason="companies tests read"):
        edge = CompanyMember.objects.get(user=member)
    edge.company = other
    with system_context(reason="companies tests write"), pytest.raises(ValueError):
        edge.save()


def test_plain_member_cannot_edit_the_roster(companies_tables: None) -> None:
    """Membership is configuration: a member reads the roster but cannot grow it."""

    company = _make_company(name="Acme")
    member = create_user("roster_member")
    stranger = create_user("roster_stranger")
    _grant(company, member)

    with actor_context(member), pytest.raises(PermissionDenied):
        CompanyMember.objects.create(company=company, user=stranger)
