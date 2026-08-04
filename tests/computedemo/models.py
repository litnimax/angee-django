"""Concrete demo models exercising :mod:`angee.base.computes`.

The shape is a miniature order: ``ComputeOrder`` aggregates its ``lines``
(reverse FK) and ``tags`` (many-to-many) and chains one local compute off
another; ``ComputeLine`` stores ``related()`` copies through a forward FK and a
two-hop path. All models are REBAC-untyped so the compute behaviour reads
without actor scaffolding; the engine's ``system_context`` writes are covered by
the REBAC-typed models in the wider suite.
"""

from __future__ import annotations

from django.db import models

from angee.base.computes import compute, related
from angee.base.models import AngeeDataModel


class ComputeTag(AngeeDataModel):
    """A taggable label whose ``name`` feeds a many-to-many depends path."""

    sqid_prefix = "ctg_"

    name = models.CharField(max_length=50)

    class Meta:
        """Concrete demo tag."""

        abstract = False
        app_label = "computedemo"
        ordering = ("name",)


class ComputeProduct(AngeeDataModel):
    """A catalogue row reached through a forward FK from lines."""

    sqid_prefix = "cpr_"

    name = models.CharField(max_length=100)

    class Meta:
        """Concrete demo product."""

        abstract = False
        app_label = "computedemo"


class ComputeOrder(AngeeDataModel):
    """An order aggregating its lines and tags into stored computed columns."""

    sqid_prefix = "cor_"

    reference = models.CharField(max_length=50, blank=True, default="")
    discount = models.IntegerField(default=0)
    currency_code = models.CharField(max_length=3, default="USD")
    tags = models.ManyToManyField(ComputeTag, blank=True, related_name="orders")

    total = models.IntegerField(default=0, editable=False)
    line_count = models.IntegerField(default=0, editable=False)
    grand_total = models.IntegerField(default=0, editable=False)
    tag_names = models.CharField(max_length=200, blank=True, default="", editable=False)

    class Meta:
        """Concrete demo order."""

        abstract = False
        app_label = "computedemo"

    @compute("total", depends=("discount", "lines.amount"))
    def _compute_total(self) -> int:
        return sum(self.lines.values_list("amount", flat=True)) - self.discount

    @compute("line_count", depends=("lines",))
    def _compute_line_count(self) -> int:
        return self.lines.count()

    @compute("grand_total", depends=("total",))
    def _compute_grand_total(self) -> int:
        return self.total * 2

    @compute("tag_names", depends=("tags.name",))
    def _compute_tag_names(self) -> str:
        return ", ".join(self.tags.order_by("name").values_list("name", flat=True))


class ComputeLine(AngeeDataModel):
    """An order line storing ``related()`` copies through its forward FKs."""

    sqid_prefix = "cln_"

    order = models.ForeignKey(ComputeOrder, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(ComputeProduct, null=True, blank=True, on_delete=models.SET_NULL, related_name="lines")
    amount = models.IntegerField(default=0)

    product_name = models.CharField(max_length=100, blank=True, default="", editable=False)
    order_currency = models.CharField(max_length=3, blank=True, default="", editable=False)

    _related_product_name = related("product_name", "product.name")
    _related_order_currency = related("order_currency", "order.currency_code")

    class Meta:
        """Concrete demo line."""

        abstract = False
        app_label = "computedemo"
