"""Draft-value codec and server recompute engine for model form surfaces.

A form draft is the client's in-progress record: field values keyed by wire
name in write shape — choices columns as stored values (the member name is
tolerated, mirroring the write inputs), to-one relations as flat public ids,
temporal values as ISO strings. The generated ``<resource>_defaults`` and
``<resource>_onchange`` query roots (attached by
:mod:`angee.graphql.data.hasura`) exchange drafts with the form; this module
owns the two boundary directions — decoding a draft onto model-native values
and encoding computed values back to draft shape — plus the recompute engine
that runs a model's ``@onchange`` handlers over an unsaved instance and diffs
what they changed. Nothing here persists; ``save()`` and ``full_clean`` remain
the authoritative write-path owners, and reads inside handlers stay
actor-scoped through the managers they use. Many-to-many draft values are not
carried (the write path owns them; a handler cannot see or set them here).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, cast

import strawberry
from django.core.exceptions import NON_FIELD_ERRORS, FieldDoesNotExist, ValidationError
from django.db import models
from strawberry.scalars import JSON

from angee.base.models import instance_from_public_id, public_id_for, public_id_of
from angee.base.onchange import OnchangeWarning as BaseOnchangeWarning
from angee.base.onchange import onchange_specs
from angee.base.serialization import json_safe
from angee.graphql.actions import ActionResult
from angee.graphql.data.resource_fields import (
    resource_wire_field_name,
    resource_wire_field_names,
)
from angee.graphql.introspection import is_to_one_relation


@strawberry.type
class OnchangeWarning:
    """Non-blocking recompute message the form surfaces as a notification."""

    message: str
    title: str = ""


@strawberry.type
class OnchangePayload:
    """Recomputed draft values plus optional in-band handler outcomes.

    ``values`` carries only the fields the triggered handlers changed, in draft
    shape, so the form applies them without disturbing the rest of the draft.
    A domain failure (a handler's ``ValidationError``, a guarded-state write)
    rides ``validation_errors`` — a field → messages map keyed by wire field
    name (``__all__`` for non-field messages) — with empty ``values``.
    """

    values: JSON
    warning: OnchangeWarning | None = None
    validation_errors: JSON | None = None


def choices_stored_value(owner_model: type[models.Model], name: str, value: Any) -> Any:
    """Translate a read-side enum member name onto the choices value it stores.

    Hasura insert/patch inputs and form drafts carry choices columns as
    ``String`` while the read surface projects the ``TextChoices`` enum
    serialized by member name, so a console read→write round-trip posts the
    NAME (``"PYDANTIC"``) where the column stores the value (``"pydantic"``).
    Accept the member name alongside the stored value; a string that is neither
    passes through for ``full_clean`` to reject. A value that is itself a valid
    stored value is never remapped, even when it collides with another member's
    name.
    """

    if not isinstance(value, str):
        return value
    try:
        field = owner_model._meta.get_field(name)
    except FieldDoesNotExist:
        return value
    enum = getattr(field, "choices_enum", None)
    if enum is None:
        return value
    member = enum.__members__.get(value)
    if member is None or value in enum._value2member_map_:
        return value
    return member.value


def decode_draft_values(
    model: type[models.Model],
    values: Mapping[str, Any],
    *,
    allowed: Iterable[str] | None = None,
    skip_unresolved_relations: bool = False,
) -> dict[str, Any]:
    """Decode wire draft values onto model-native values, keyed by field name.

    Unknown keys and many-to-many columns are skipped (a draft may carry
    UI-only fields), ``allowed`` optionally restricts the accepted field names,
    to-one relations resolve their public id through the actor-scoped default
    manager (an unreachable row decodes to ``None``, never an existence
    oracle), and every other value coerces through its field's ``to_python`` —
    the field owns the coercion, and a malformed value raises the
    ``ValidationError`` the callers map in-band.

    ``skip_unresolved_relations`` drops a to-one key whose id resolved to
    nothing instead of decoding it to ``None``. An onchange draft wants the
    default: a blank relation there is the user clearing the field, and the
    overlay must carry it. A defaults seed wants the opposite — an explicit
    ``None`` reads as "the caller pinned no relation", which lets a
    ``get_create_defaults`` override substitute a *different* row for the one
    the caller asked for, so an unusable seed must fall through to the model
    rule rather than pose as an answer.
    """

    allowed_names = set(allowed) if allowed is not None else None
    decoded: dict[str, Any] = {}
    for wire_name, raw in values.items():
        try:
            field = model._meta.get_field(wire_name)
        except FieldDoesNotExist:
            continue
        if not isinstance(field, models.Field) or field.many_to_many:
            continue
        if allowed_names is not None and field.name not in allowed_names:
            continue
        if is_to_one_relation(field):
            related_model = cast(type[models.Model], field.related_model)
            related = None if raw in (None, "") else instance_from_public_id(related_model, str(raw))
            if related is None and raw not in (None, "") and skip_unresolved_relations:
                continue
            decoded[field.name] = related
            continue
        decoded[field.name] = field.to_python(choices_stored_value(model, field.name, raw))
    return decoded


def encode_draft_values(
    model: type[models.Model],
    node: type | None,
    values: Mapping[str, Any],
    *,
    allowed_wire: Iterable[str] | None = None,
) -> JSON:
    """Encode model-native values into wire draft shape, keyed by wire name.

    ``allowed_wire`` restricts the emitted keys to a surface's declared wire
    names (a resource's creatable set, a node's readable projection) so a
    computed value the surface does not expose never leaks onto the wire.
    """

    allowed = set(allowed_wire) if allowed_wire is not None else None
    encoded: dict[str, Any] = {}
    for name, value in values.items():
        try:
            field = model._meta.get_field(name)
        except FieldDoesNotExist:
            continue
        if not isinstance(field, models.Field):
            continue
        wire_name = resource_wire_field_name(node, field.name) or field.name
        if allowed is not None and wire_name not in allowed:
            continue
        encoded[wire_name] = encode_draft_value(field, value)
    return cast(JSON, encoded)


def encode_draft_value(field: models.Field[Any, Any], value: Any) -> Any:
    """Encode one model-native value into its wire draft shape."""

    if value is None:
        return None
    if is_to_one_relation(field):
        if isinstance(value, models.Model):
            return public_id_of(value) or None
        related_model = cast(type[models.Model], field.related_model)
        return public_id_for(related_model, value) or None
    return json_safe(value)


def run_onchange(
    model: type[models.Model],
    *,
    node: type | None,
    values: Mapping[str, Any],
    changed: Iterable[str],
    instance: models.Model | None = None,
) -> OnchangePayload:
    """Run the handlers ``changed`` triggers over a draft and diff the result.

    A create draft builds an unsaved instance from the decoded values (absent
    columns take their field defaults); an edit draft overlays them onto the
    caller-authorized ``instance``. Triggered handlers run in declaration order
    (sorted by method name), mutate the instance, and the concrete-field diff
    around them becomes the returned values — restricted to the node's readable
    projection so a computed column the resource does not expose never leaks.
    The first warning a handler returns is surfaced; domain failures are the
    callers' to map in-band (see :func:`onchange_error_payload`).
    """

    decoded = decode_draft_values(model, values)
    if instance is None:
        draft = model(**decoded)
    else:
        draft = instance
        for name, value in decoded.items():
            setattr(draft, name, value)
    changed_names = draft_field_names(model, changed)
    before = _snapshot(model, draft)
    warning: BaseOnchangeWarning | None = None
    for spec in onchange_specs(model):
        if not set(spec.fields) & changed_names:
            continue
        result = getattr(draft, spec.name)()
        if warning is None and isinstance(result, BaseOnchangeWarning):
            warning = result
    after = _snapshot(model, draft)
    recomputed = {name: after[name] for name in after if before[name] != after[name]}
    return OnchangePayload(
        values=encode_draft_values(
            model,
            node,
            recomputed,
            allowed_wire=_node_wire_names(node),
        ),
        warning=OnchangeWarning(message=warning.message, title=warning.title) if warning is not None else None,
    )


def onchange_error_payload(error: Exception) -> OnchangePayload:
    """Map a caught domain error onto an in-band recompute payload.

    Keys stay the wire field names (no camel-casing — the form binds them
    verbatim, unlike a typed-args action form binding GraphQL argument names);
    ``__all__`` carries the non-field messages.
    """

    validation_errors = (
        ActionResult.validation_error_map(error, camel_case_keys=False)
        if isinstance(error, ValidationError)
        else None
    )
    if validation_errors is None:
        validation_errors = cast(JSON, {NON_FIELD_ERRORS: [str(error)]})
    return OnchangePayload(values=cast(JSON, {}), validation_errors=validation_errors)


def _snapshot(model: type[models.Model], instance: models.Model) -> dict[str, Any]:
    """Return the instance's concrete field values, keyed by field name.

    ``Field.value_from_object`` is the owner of reading a field off an instance
    (a to-one relation snapshots as its stored id), so the recompute diff
    compares exactly what the row would persist.
    """

    return {field.name: field.value_from_object(instance) for field in model._meta.concrete_fields}


def draft_field_names(model: type[models.Model], wire_names: Iterable[str]) -> set[str]:
    """Return the model field names addressed by wire names, unknowns skipped."""

    names: set[str] = set()
    for wire_name in wire_names:
        try:
            names.add(model._meta.get_field(wire_name).name)
        except FieldDoesNotExist:
            continue
    return names


def _node_wire_names(node: type | None) -> tuple[str, ...] | None:
    """Return the node's readable wire names, or ``None`` when it has none."""

    if node is None:
        return None
    names = resource_wire_field_names(node)
    return names or None
