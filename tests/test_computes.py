"""Behaviour of :mod:`angee.base.computes` — stored computed columns.

The demo shape (``tests.computedemo``) is a miniature order: ``ComputeOrder``
aggregates its ``lines`` (reverse FK) and ``tags`` (many-to-many) and chains a
local compute off another; ``ComputeLine`` stores ``related()`` copies through
forward FKs. These cover the maintenance contract end to end: recompute on
create/save with ``update_fields`` fan-out, cross-model propagation through
every hop kind, delete propagation, defer-safety, the idempotent repair pass,
the ``recompute`` command, and the ``angee.E015``–``E019`` declaration checks.
"""

from __future__ import annotations

from io import StringIO
from typing import Any

import pytest
from django.core.management import CommandError, call_command
from django.db import models
from django.db.models.signals import post_save
from rebac import system_context

from angee.base.computes import compute, compute_check_messages, compute_specs
from angee.base.models import AngeeModel
from tests.computedemo.models import ComputeLine, ComputeOrder, ComputeProduct, ComputeTag


def _order_with_lines(amounts: tuple[int, ...] = (3, 7), discount: int = 0) -> ComputeOrder:
    """Create one order with lines carrying the given amounts."""

    order = ComputeOrder.objects.create(discount=discount)
    for amount in amounts:
        ComputeLine.objects.create(order=order, amount=amount)
    order.refresh_from_db()
    return order


@pytest.mark.django_db
def test_create_computes_local_and_deferred_columns() -> None:
    """An insert computes relation-free columns pre-insert and aggregates after."""

    with system_context(reason="test computes create"):
        order = ComputeOrder.objects.create(discount=5)
    assert order.total == -5
    assert order.grand_total == -10
    assert order.line_count == 0


@pytest.mark.django_db
def test_line_create_recomputes_order_aggregates() -> None:
    """Creating a child row fires the reverse-FK membership and value edges."""

    with system_context(reason="test computes line create"):
        order = _order_with_lines((3, 7))
    assert order.total == 10
    assert order.line_count == 2
    assert order.grand_total == 20


@pytest.mark.django_db
def test_local_dependency_recomputes_on_full_save() -> None:
    """A full save recomputes every local compute, chained in order."""

    with system_context(reason="test computes local"):
        order = _order_with_lines((3, 7))
        order.discount = 4
        order.save()
        order.refresh_from_db()
    assert order.total == 6
    assert order.grand_total == 12


@pytest.mark.django_db
def test_partial_save_folds_computed_columns_into_update_fields() -> None:
    """A partial save writes the recomputed columns and reports them to signals."""

    captured: list[set[str]] = []

    def _capture(sender: Any, instance: Any, update_fields: Any, **kwargs: Any) -> None:
        del sender, instance, kwargs
        if update_fields is not None:
            captured.append(set(update_fields))

    post_save.connect(_capture, sender=ComputeOrder, dispatch_uid="test.computes.capture")
    try:
        with system_context(reason="test computes partial"):
            order = _order_with_lines((3, 7))
            order.discount = 1
            order.save(update_fields={"discount"})
            order.refresh_from_db()
    finally:
        post_save.disconnect(dispatch_uid="test.computes.capture", sender=ComputeOrder)

    assert order.total == 9
    assert order.grand_total == 18
    assert captured
    assert {"discount", "total", "grand_total", "updated_at"} <= captured[-1]


@pytest.mark.django_db
def test_child_amount_change_propagates_to_parent() -> None:
    """A write to a depended-on child column recomputes the parent rows."""

    with system_context(reason="test computes propagate"):
        order = _order_with_lines((3, 7))
        line = order.lines.order_by("pk").first()
        assert line is not None
        line.amount = 13
        line.save(update_fields={"amount"})
        order.refresh_from_db()
    assert order.total == 20
    assert order.grand_total == 40


@pytest.mark.django_db
def test_reparented_child_recomputes_both_parents() -> None:
    """Moving a child's FK recomputes the old and the new parent."""

    with system_context(reason="test computes reparent"):
        source = _order_with_lines((3, 7))
        target = ComputeOrder.objects.create()
        line = ComputeLine.objects.get(order=source, amount=7)
        line.order = target
        line.save()
        source.refresh_from_db()
        target.refresh_from_db()
    assert source.total == 3
    assert source.line_count == 1
    assert target.total == 7
    assert target.line_count == 1


@pytest.mark.django_db
def test_deleted_child_recomputes_parent() -> None:
    """Deleting a child row recomputes the rows that aggregated it."""

    with system_context(reason="test computes delete"):
        order = _order_with_lines((3, 7))
        ComputeLine.objects.get(order=order, amount=7).delete()
        order.refresh_from_db()
    assert order.total == 3
    assert order.line_count == 1


@pytest.mark.django_db
def test_related_copies_through_forward_paths() -> None:
    """``related()`` stores the path value on create and tracks its changes."""

    with system_context(reason="test computes related"):
        product = ComputeProduct.objects.create(name="Widget")
        order = ComputeOrder.objects.create(currency_code="EUR")
        line = ComputeLine.objects.create(order=order, product=product)
        assert line.product_name == "Widget"
        assert line.order_currency == "EUR"

        product.name = "Gadget"
        product.save(update_fields={"name"})
        line.refresh_from_db()
        assert line.product_name == "Gadget"

        order.currency_code = "GBP"
        order.save(update_fields={"currency_code"})
        line.refresh_from_db()
        assert line.order_currency == "GBP"


@pytest.mark.django_db
def test_related_falls_back_to_default_when_target_deleted() -> None:
    """A broken hop (SET_NULL cascade) resets the related copy to its default."""

    with system_context(reason="test computes related delete"):
        product = ComputeProduct.objects.create(name="Widget")
        order = ComputeOrder.objects.create()
        line = ComputeLine.objects.create(order=order, product=product)
        product.delete()
        line.refresh_from_db()
    assert line.product_id is None
    assert line.product_name == ""


@pytest.mark.django_db
def test_m2m_membership_and_far_column_propagate() -> None:
    """Tag adds/removes/renames all reach the aggregating column."""

    with system_context(reason="test computes m2m"):
        order = ComputeOrder.objects.create()
        urgent = ComputeTag.objects.create(name="urgent")
        vip = ComputeTag.objects.create(name="vip")

        order.tags.add(urgent, vip)
        order.refresh_from_db()
        assert order.tag_names == "urgent, vip"

        urgent.name = "later"
        urgent.save(update_fields={"name"})
        order.refresh_from_db()
        assert order.tag_names == "later, vip"

        order.tags.remove(vip)
        order.refresh_from_db()
        assert order.tag_names == "later"

        order.tags.clear()
        order.refresh_from_db()
        assert order.tag_names == ""


@pytest.mark.django_db
def test_deferred_dependency_load_stays_safe() -> None:
    """A value edge resolves through the join, so a deferred FK stays lazy."""

    with system_context(reason="test computes defer"):
        order = _order_with_lines((3,))
        line = ComputeLine.objects.only("id", "amount").get(order=order)
        line.amount = 11
        line.save(update_fields={"amount"})
        order.refresh_from_db()
    assert order.total == 11


@pytest.mark.django_db
def test_bulk_update_drift_is_repaired_by_queryset_recompute() -> None:
    """``QuerySet.update`` skips signals; ``.recompute()`` is the repair owner."""

    with system_context(reason="test computes repair"):
        order = _order_with_lines((3, 7))
        ComputeLine.objects.filter(order=order).update(amount=10)
        order.refresh_from_db()
        assert order.total == 10  # stale: bulk paths skip signals by design

        written = ComputeOrder.objects.recompute("total")
        order.refresh_from_db()
    assert written == 1
    assert order.total == 20
    assert order.grand_total == 40  # the chained compute rides the repair save


@pytest.mark.django_db
def test_recompute_is_idempotent() -> None:
    """A repair pass over clean rows writes nothing."""

    with system_context(reason="test computes idempotent"):
        _order_with_lines((3, 7))
        assert ComputeOrder.objects.recompute() == 0


@pytest.mark.django_db
def test_recompute_command_repairs_and_reports() -> None:
    """The management command backfills named models and validates its input."""

    with system_context(reason="test computes command"):
        order = _order_with_lines((3, 7))
        ComputeLine.objects.filter(order=order).update(amount=1)

    out = StringIO()
    call_command("recompute", "computedemo.ComputeOrder", stdout=out)
    assert "computedemo.ComputeOrder: 1 row(s) updated" in out.getvalue()
    with system_context(reason="test computes command read"):
        order.refresh_from_db()
    assert order.total == 2

    with pytest.raises(CommandError, match="does not compute"):
        call_command("recompute", "computedemo.ComputeOrder", "--field", "nope")
    with pytest.raises(CommandError, match="declares no stored computed columns"):
        call_command("recompute", "computedemo.ComputeProduct")


def test_check_rejects_unknown_target_field() -> None:
    """angee.E015 — the computed column must exist."""

    class MissingTarget(AngeeModel):
        class Meta:
            abstract = True
            app_label = "computedemo"

        @compute("missing")
        def _compute_missing(self) -> int:
            return 0

    assert [error.id for error in compute_check_messages(MissingTarget)] == ["angee.E015"]


def test_check_rejects_editable_target_field() -> None:
    """angee.E016 — a computed column must declare editable=False."""

    class EditableTarget(AngeeModel):
        amount = models.IntegerField(default=0)

        class Meta:
            abstract = True
            app_label = "computedemo"

        @compute("amount")
        def _compute_amount(self) -> int:
            return 0

    assert [error.id for error in compute_check_messages(EditableTarget)] == ["angee.E016"]


def test_check_rejects_unresolvable_depends_path() -> None:
    """angee.E017 — every depends path must resolve hop by hop."""

    class BadPath(AngeeModel):
        amount = models.IntegerField(default=0)
        derived = models.IntegerField(default=0, editable=False)

        class Meta:
            abstract = True
            app_label = "computedemo"

        @compute("derived", depends=("amount.x",))
        def _compute_derived(self) -> int:
            return 0

    ids = [error.id for error in compute_check_messages(BadPath)]
    assert ids == ["angee.E017"]


def test_check_rejects_local_dependency_cycle() -> None:
    """angee.E018 — local compute chains must be acyclic."""

    class Cycle(AngeeModel):
        a = models.IntegerField(default=0, editable=False)
        b = models.IntegerField(default=0, editable=False)

        class Meta:
            abstract = True
            app_label = "computedemo"

        @compute("a", depends=("b",))
        def _compute_a(self) -> int:
            return 0

        @compute("b", depends=("a",))
        def _compute_b(self) -> int:
            return 0

    assert [error.id for error in compute_check_messages(Cycle)] == ["angee.E018"]


def test_check_rejects_two_computes_for_one_column() -> None:
    """angee.E019 — one column has exactly one compute method."""

    class Twice(AngeeModel):
        value = models.IntegerField(default=0, editable=False)

        class Meta:
            abstract = True
            app_label = "computedemo"

        @compute("value")
        def _compute_value(self) -> int:
            return 0

        @compute("value")
        def _compute_value_again(self) -> int:
            return 1

    assert [error.id for error in compute_check_messages(Twice)] == ["angee.E019"]


def test_subclass_overrides_parent_compute_by_method_name() -> None:
    """Redefining the same-named method replaces the parent's spec, Python-style."""

    class Parent(AngeeModel):
        value = models.IntegerField(default=0, editable=False)
        source = models.IntegerField(default=0)

        class Meta:
            abstract = True
            app_label = "computedemo"

        @compute("value", depends=("source",))
        def _compute_value(self) -> int:
            return self.source

    class Child(Parent):
        other = models.IntegerField(default=0)

        class Meta:
            abstract = True
            app_label = "computedemo"

        @compute("value", depends=("other",))
        def _compute_value(self) -> int:
            return self.other * 2

    specs = compute_specs(Child)
    assert len(specs) == 1
    assert specs[0].depends == ("other",)
    assert not compute_check_messages(Child)
