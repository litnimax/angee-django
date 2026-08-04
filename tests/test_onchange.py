"""Tests for the ``@onchange`` declaration vocabulary and create defaults."""

from __future__ import annotations

import datetime

import pytest
from django.db import models
from django.utils import timezone

from angee.base.models import AngeeModel
from angee.base.onchange import (
    OnchangeSpec,
    onchange,
    onchange_check_messages,
    onchange_specs,
)


class Draft(models.Model):
    """Concrete throwaway model with two recompute handlers."""

    title = models.CharField(max_length=64, default="")
    body = models.TextField(default="")
    word_count = models.IntegerField(default=0)
    slug = models.SlugField(default="")

    class Meta:
        """Model options for the handler-harvest test model."""

        app_label = "tests"

    @onchange("body")
    def recount_words(self) -> None:
        """Derive the word count from the draft body."""

        self.word_count = len(self.body.split())

    @onchange("title", "body")
    def derive_slug(self) -> None:
        """Derive the slug from the draft title."""

        self.slug = self.title.lower().replace(" ", "-")


class HandlerBase(models.Model):
    """Abstract donor declaring one recompute handler."""

    title = models.CharField(max_length=64, default="")
    subtitle = models.CharField(max_length=64, default="")

    class Meta:
        """Model options for the abstract handler donor."""

        abstract = True

    @onchange("title")
    def sync_title(self) -> None:
        """Mirror the title into the subtitle."""

        self.subtitle = self.title


class ReplacingChild(HandlerBase):
    """Concrete child replacing the inherited handler with wider triggers."""

    class Meta:
        """Model options for the replacing child."""

        app_label = "tests"

    @onchange("title", "subtitle")
    def sync_title(self) -> None:
        """Replace the inherited handler deliberately."""

        self.subtitle = self.title.upper()


class ShadowingChild(HandlerBase):
    """Concrete child shadowing the inherited handler with a plain method."""

    class Meta:
        """Model options for the shadowing child."""

        app_label = "tests"

    def sync_title(self) -> None:
        """Shadow the inherited handler without declaring triggers."""

        self.subtitle = self.title


class UnknownFieldModel(AngeeModel):
    """Concrete Angee model declaring a handler on an unknown field."""

    class Meta:
        """Model options for the unknown-trigger test model."""

        app_label = "tests"

    @onchange("missing")
    def touch(self) -> None:
        """Handler whose trigger field does not exist."""


class DefaultedDoc(AngeeModel):
    """Concrete Angee model exercising the base create-defaults harvest."""

    title = models.CharField(max_length=64, default="untitled")
    count = models.PositiveIntegerField(default=0)
    stamp = models.DateTimeField(default=timezone.now)
    note = models.CharField(max_length=64, blank=True)
    flag = models.BooleanField(default=True)

    class Meta:
        """Model options for the create-defaults test model."""

        app_label = "tests"


def test_onchange_requires_field_names() -> None:
    with pytest.raises(TypeError):
        onchange()
    with pytest.raises(TypeError):
        onchange("")
    with pytest.raises(TypeError):
        onchange(123)  # type: ignore[arg-type]


def test_onchange_specs_are_sorted_and_carry_triggers() -> None:
    assert onchange_specs(Draft) == (
        OnchangeSpec(name="derive_slug", fields=("title", "body")),
        OnchangeSpec(name="recount_words", fields=("body",)),
    )


def test_onchange_specs_are_cached_per_class() -> None:
    first = onchange_specs(Draft)
    assert onchange_specs(Draft) is first
    assert onchange_specs(ReplacingChild) is not first


def test_decorated_method_stays_directly_callable() -> None:
    draft = Draft(body="one two three")
    draft.recount_words()
    assert draft.word_count == 3


def test_subclass_replaces_inherited_handler() -> None:
    assert onchange_specs(ReplacingChild) == (
        OnchangeSpec(name="sync_title", fields=("title", "subtitle")),
    )
    assert onchange_check_messages(ReplacingChild) == []


def test_shadowed_handler_is_excluded_and_reported() -> None:
    assert onchange_specs(ShadowingChild) == ()
    messages = onchange_check_messages(ShadowingChild)
    assert [message.id for message in messages] == ["angee.E016"]
    assert "sync_title" in messages[0].msg


def test_unknown_trigger_field_is_reported_through_model_check() -> None:
    errors = [error for error in UnknownFieldModel.check() if error.id == "angee.E015"]
    assert len(errors) == 1
    assert "missing" in errors[0].msg


def test_get_create_defaults_evaluates_field_defaults() -> None:
    values = DefaultedDoc.get_create_defaults()
    assert values["title"] == "untitled"
    assert values["count"] == 0
    assert values["flag"] is True
    assert isinstance(values["stamp"], datetime.datetime)
    assert "note" not in values
    assert "id" not in values
    assert "created_at" not in values


def test_get_create_defaults_folds_caller_seeds_on_top() -> None:
    values = DefaultedDoc.get_create_defaults(defaults={"title": "seeded", "count": 7})
    assert values["title"] == "seeded"
    assert values["count"] == 7
    assert values["flag"] is True
