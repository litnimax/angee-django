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
from django.db import connection, transaction
from django.db.models import ProtectedError
from rebac import system_context

from angee.base.indexes import PatternOpsIndex
from angee.companies.models import Company as AbstractCompany
from tests.conftest import _clear_model_tables, _create_missing_tables
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


COMPANIES_TEST_MODELS = (Party, Organization, Company)
"""Concrete models created on demand by companies test fixtures."""


@pytest.fixture()
def companies_tables(transactional_db: Any) -> Iterator[None]:
    """Create the concrete companies (and parties) tables for one test."""

    del transactional_db
    created_models = _create_missing_tables(COMPANIES_TEST_MODELS)
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
