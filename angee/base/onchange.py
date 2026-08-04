"""Live recompute declarations for model-backed forms.

API contract:

``@onchange("field_a", "field_b")`` declares a model method as a recompute
handler: when a form edit changes one of the named trigger fields, the handler
runs on an unsaved instance carrying the current draft values and mutates
``self`` to adjust dependent fields. The runtime consumer (the GraphQL data
layer) diffs the instance around the triggered handlers and returns only the
values they changed; nothing is persisted, and ``save()`` remains the
authoritative place to recompute persisted derivations. A handler may return an
:class:`OnchangeWarning` to surface a non-blocking message on the form, and may
raise ``ValidationError`` to surface field-keyed errors instead. Handlers take
no arguments beyond ``self``; reads of related rows go through managers, so
actor scoping applies as it does everywhere else.

``onchange_specs(model)`` returns the effective handler declarations for a
model class — first-in-MRO per method name (standard inheritance: redefining a
handler name replaces it), sorted by method name, cached on the class.

Declarations are validated by Angee's model checks: ``angee.E015`` names an
unknown trigger field, and ``angee.E016`` flags a decorated handler shadowed by
an undecorated method earlier in the MRO — a materialized child is emitted
parent-first, so without the check a child handler reusing a parent method name
would be dropped silently. The vocabulary is inert by design: ``angee.base``
declares, ``angee.graphql`` interprets, keeping the one-way package layering.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from django.db import models

_MethodT = TypeVar("_MethodT", bound=Callable[..., Any])

ONCHANGE_FIELDS_ATTR = "_angee_onchange_fields"
"""Function attribute the decorator sets: the declared trigger-field tuple."""

_ONCHANGE_SPECS_CACHE = "_angee_onchange_specs"
"""Class attribute caching the harvested spec tuple, read non-inherited."""


@dataclass(frozen=True, slots=True)
class OnchangeWarning:
    """Non-blocking message a handler returns for the form to surface."""

    message: str
    title: str = ""


@dataclass(frozen=True, slots=True)
class OnchangeSpec:
    """One effective recompute handler: its method name and trigger fields."""

    name: str
    fields: tuple[str, ...]


def onchange(*fields: str) -> Callable[[_MethodT], _MethodT]:
    """Declare a model method as a recompute handler for ``fields``.

    The decorator only marks the method (the module docstring carries the
    handler contract); the method stays an ordinary model method and remains
    directly callable. Trigger field names are validated against ``_meta`` by
    the model checks, not here, because the model class does not exist yet at
    decoration time.
    """

    if not fields:
        raise TypeError("onchange() requires at least one trigger field name.")
    for name in fields:
        if not isinstance(name, str) or not name:
            raise TypeError(f"onchange() trigger field names must be non-empty strings; got {name!r}.")

    def decorate(method: _MethodT) -> _MethodT:
        setattr(method, ONCHANGE_FIELDS_ATTR, tuple(fields))
        return method

    return decorate


def onchange_specs(model: type[models.Model]) -> tuple[OnchangeSpec, ...]:
    """Return the effective handler declarations for ``model``, sorted by name.

    Effective means first-in-MRO: a subclass redefining a handler name replaces
    the inherited declaration, and a name whose effective attribute lost its
    marker (shadowed by an undecorated method) is excluded here and reported by
    the ``angee.E016`` model check. The harvest is cached on the class, so the
    per-request consumers read one class attribute.
    """

    cached = model.__dict__.get(_ONCHANGE_SPECS_CACHE)
    if cached is not None:
        return cached
    specs = tuple(
        sorted(
            (
                OnchangeSpec(name=name, fields=fields)
                for name, fields in _effective_handler_fields(model).items()
            ),
            key=lambda spec: spec.name,
        )
    )
    setattr(model, _ONCHANGE_SPECS_CACHE, specs)
    return specs


def onchange_check_messages(model: type[models.Model]) -> list[checks.CheckMessage]:
    """Return model-check errors for ``model``'s onchange declarations."""

    messages: list[checks.CheckMessage] = []
    for spec in onchange_specs(model):
        for field_name in spec.fields:
            try:
                model._meta.get_field(field_name)
            except FieldDoesNotExist:
                messages.append(
                    checks.Error(
                        f"{model._meta.label}.{spec.name} declares onchange on unknown field {field_name!r}.",
                        obj=model,
                        id="angee.E015",
                    )
                )
    effective = _effective_handler_fields(model)
    for name in sorted(_declared_handler_names(model) - set(effective)):
        messages.append(
            checks.Error(
                f"{model._meta.label}.{name} carries an onchange declaration that an undecorated "
                "method earlier in the MRO shadows, so the handler would never run. Rename the "
                "handler, or decorate the overriding method to replace it deliberately.",
                obj=model,
                id="angee.E016",
            )
        )
    return messages


def _effective_handler_fields(model: type[models.Model]) -> dict[str, tuple[str, ...]]:
    """Return declared handler names whose effective attribute carries the marker."""

    effective: dict[str, tuple[str, ...]] = {}
    for name in _declared_handler_names(model):
        fields = getattr(getattr(model, name, None), ONCHANGE_FIELDS_ATTR, None)
        if fields is not None:
            effective[name] = fields
    return effective


def _declared_handler_names(model: type[models.Model]) -> set[str]:
    """Return every method name any MRO class declares as a handler."""

    return {
        name
        for klass in model.__mro__
        for name, value in vars(klass).items()
        if getattr(value, ONCHANGE_FIELDS_ATTR, None) is not None
    }
