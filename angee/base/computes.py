"""Stored computed columns with declared dependencies (Odoo-style ``compute``).

API contract:

``@compute("field", depends=("dep", "relation.dep"))`` decorates a model method
as the stored compute for one concrete, ``editable=False`` column. The method
takes only ``self`` and returns the derived value; the framework owns the
assignment and the write. ``depends`` entries are Django query-lookup paths from
the declaring model: a plain name is a local column (an FK name means its stored
id), and a dotted path walks relations — forward FK/one-to-one, reverse FK, and
many-to-many hops — ending on a column of the reached model, or on a relation to
depend on membership alone.

``related("field", "relation.column")`` returns a generated compute method that
stores a copy of the value at the end of the path (Odoo's ``related=``); bind it
to any model-body attribute (conventionally ``_related_<field>``). A broken hop
(``None`` anywhere along the path) stores the column's default.

Maintenance has the two owners the derived-column doctrine names
(``docs/backend/guidelines.md``):

- **Instance saves and deletes** are automatic. ``AngeeModel.save()`` recomputes
  local specs and folds recomputed columns into a partial ``update_fields`` (so
  ``changes`` subscribers, history, and audit stamping observe them), and this
  module's signal receivers propagate cross-model dependencies: a write to a
  depended-on column recomputes the dependent rows resolved through the inverted
  path, under ``system_context`` with the base manager — computed maintenance is
  a system write, never actor-attributed.
- **Bulk paths** (``bulk_create``, ``QuerySet.update``) skip signals by design;
  the idempotent repair pass is ``AngeeQuerySet.recompute()`` and the
  ``manage.py recompute`` backfill.

Validation is a Django system check (``angee.E015``–``angee.E019``) run through
``AngeeModel.check()``: the target column must exist, be concrete,
non-relational, and ``editable=False``; every depends path must resolve; local
compute chains must be acyclic; and one column has exactly one compute.
"""

from __future__ import annotations

import contextvars
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from typing import Any, cast

from django.apps import apps
from django.core import checks
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.db import models
from django.db.models.fields.reverse_related import ForeignObjectRel
from django.db.models.signals import class_prepared, m2m_changed, post_delete, post_save, pre_delete
from rebac import system_context

from angee.base.mixins import system_writer, update_fields_with_auto_now

ComputeMethod = Callable[..., Any]

RECOMPUTE_REASON = "angee.base.computes.recompute"
"""The ``system_context`` reason every framework-owned recompute write carries."""

_UNKNOWN = object()
"""Sentinel for a dependency column whose loaded (old) value is not known."""

_SPEC_ATTR = "_angee_compute_spec"
"""Attribute name a decorated compute method carries its spec under."""


@dataclass(frozen=True, slots=True)
class ComputeSpec:
    """One declared stored compute: a model method deriving one column."""

    field_name: str
    depends: tuple[str, ...]
    method_name: str = ""
    related_path: str | None = None


def compute(field_name: str, *, depends: Sequence[str] = ()) -> Callable[[ComputeMethod], ComputeMethod]:
    """Declare a model method as the stored compute for ``field_name``.

    The method body takes ``self`` and returns the value; the framework assigns
    it and owns every write path (see the module docstring). ``depends`` lists
    the query-lookup paths whose changes invalidate the stored value.
    """

    spec = ComputeSpec(field_name=field_name, depends=tuple(depends))

    def decorate(method: ComputeMethod) -> ComputeMethod:
        setattr(method, _SPEC_ATTR, spec)
        return method

    return decorate


def related(field_name: str, path: str) -> ComputeMethod:
    """Return a generated compute storing a copy of the value at ``path``.

    ``path`` walks to-one relations from the declaring model and must end on a
    column (``"order.currency.code"``). A ``None`` anywhere along the path
    stores the target column's default. Bind the result to a model-body
    attribute, conventionally ``_related_<field>``.
    """

    hops = tuple(part for part in path.split(".") if part)

    def _compute_related(self: models.Model) -> Any:
        value: Any = self
        for hop in hops:
            value = getattr(value, hop)
            if value is None:
                return self._meta.get_field(field_name).get_default()
        return value

    _compute_related.__name__ = f"_related_{field_name}"
    _compute_related.__qualname__ = _compute_related.__name__
    _compute_related.__doc__ = f"Return the related ``{path}`` value stored on ``{field_name}``."
    setattr(_compute_related, _SPEC_ATTR, ComputeSpec(field_name=field_name, depends=(path,), related_path=path))
    return _compute_related


@dataclass(frozen=True, slots=True)
class BoundCompute:
    """A compute spec resolved against one concrete model class."""

    spec: ComputeSpec
    local_names: frozenset[str]
    """Local column names/attnames whose presence in ``update_fields`` (or whose
    change on a full save) requires re-running this compute on the saved row."""

    requires_pk: frozenset[str] = frozenset()
    """Depends paths whose first hop is a reverse or many-to-many relation.

    Such a path cannot be read on an unsaved row (Django requires a primary key
    to use the relation), so the insert path defers this compute to the
    post-insert finalize pass (:func:`finalize_created_computes`)."""


@dataclass(frozen=True, slots=True)
class ComputeTrigger:
    """One inverted cross-model dependency edge.

    A write to ``column`` on a ``source`` row invalidates ``field_name`` on the
    ``dependent`` rows reached by filtering ``lookup`` against the anchor pks.
    For a value edge the anchor is the source row itself; for a ``membership``
    edge the anchors are the watched FK's old and new values (the two parents a
    reparent affects). ``column=None`` marks a membership edge that only a
    delete can fire (a many-to-many far side collected without ``m2m_changed``).
    """

    dependent: type[models.Model]
    field_name: str
    source: type[models.Model]
    column: str | None
    written_names: frozenset[str]
    lookup: str
    membership: bool


@dataclass(frozen=True, slots=True)
class M2MComputeTrigger:
    """One inverted many-to-many membership edge, fired by ``m2m_changed``."""

    dependent: type[models.Model]
    field_name: str
    through: type[models.Model]
    anchor_model: type[models.Model]
    lookup: str


@dataclass(frozen=True, slots=True)
class _ResolvedPath:
    """The local and cross-model consequences of one depends path."""

    local_names: frozenset[str]
    triggers: tuple[ComputeTrigger, ...]
    m2m_triggers: tuple[M2MComputeTrigger, ...]


class ComputePathError(FieldDoesNotExist):
    """A depends path that does not resolve against the declaring model."""


def compute_specs(model: type[models.Model]) -> tuple[ComputeSpec, ...]:
    """Return ``model``'s compute specs in method-resolution order, unresolved.

    The first class in the MRO that defines a given method name owns it, so a
    subclass overrides a parent's compute by redefining the same-named method —
    plain Python override semantics. Distinct method names targeting the same
    column are left in place for :func:`compute_check_messages` to reject.
    """

    found: dict[str, ComputeSpec] = {}
    for klass in model.__mro__:
        for name, value in vars(klass).items():
            spec = cast(ComputeSpec | None, getattr(value, _SPEC_ATTR, None))
            if spec is None or name in found:
                continue
            found[name] = replace(spec, method_name=name)
    return tuple(sorted(found.values(), key=lambda spec: (spec.field_name, spec.method_name)))


_BOUND_CACHE: dict[type[models.Model], tuple[BoundCompute, ...]] = {}
"""Per-class resolved computes; class declarations are static, so never stale."""


def bound_computes(model: type[models.Model]) -> tuple[BoundCompute, ...]:
    """Return ``model``'s computes resolved and ordered for local evaluation.

    Specs are ordered topologically over local compute-to-compute dependencies
    (a compute reading another stored computed column runs after it), ties
    broken by column name. Raises :class:`ComputePathError` on an unresolvable
    depends path and ``ValueError`` on a local dependency cycle; the same
    defects surface as system checks through :func:`compute_check_messages`.
    """

    cached = _BOUND_CACHE.get(model)
    if cached is not None:
        return cached
    bound = []
    for spec in compute_specs(model):
        resolved = _resolve_path_set(model, spec)
        bound.append(
            BoundCompute(
                spec=spec,
                local_names=resolved.local_names,
                requires_pk=frozenset(path for path in spec.depends if _path_requires_pk(model, path)),
            )
        )
    ordered = _ordered_locally(model, bound)
    _BOUND_CACHE[model] = ordered
    return ordered


def _path_requires_pk(model: type[models.Model], path: str) -> bool:
    """Return whether ``path`` starts with a relation an unsaved row cannot read."""

    hop = path.split(".", 1)[0]
    field = model._meta.get_field(hop)
    return isinstance(field, ForeignObjectRel) or bool(getattr(field, "many_to_many", False))


def stored_compute_field_names(model: type[models.Model]) -> frozenset[str]:
    """Return the column names on ``model`` maintained by declared computes."""

    return frozenset(spec.field_name for spec in compute_specs(model))


def compute_check_messages(model: type[models.Model]) -> list[checks.CheckMessage]:
    """Return system-check errors for ``model``'s compute declarations."""

    errors: list[checks.CheckMessage] = []
    specs = compute_specs(model)
    by_field: dict[str, list[ComputeSpec]] = {}
    for spec in specs:
        by_field.setdefault(spec.field_name, []).append(spec)

    for field_name, owners in by_field.items():
        if len(owners) > 1:
            names = ", ".join(spec.method_name for spec in owners)
            errors.append(
                checks.Error(
                    f"{model._meta.label}.{field_name} is computed by more than one method ({names}); "
                    "override a compute by redefining the same-named method.",
                    obj=model,
                    id="angee.E019",
                )
            )

    for spec in specs:
        errors.extend(_check_target_field(model, spec))
        for path in spec.depends:
            try:
                resolved_final_is_column = _resolve_path(model, spec, path, collect=None)
            except ComputePathError as error:
                errors.append(checks.Error(str(error), obj=model, id="angee.E017"))
                continue
            if spec.related_path is not None and not resolved_final_is_column:
                errors.append(
                    checks.Error(
                        f"{model._meta.label}.{spec.method_name} related path {path!r} must end on a column.",
                        obj=model,
                        id="angee.E017",
                    )
                )

    if not any(error.id == "angee.E017" for error in errors):
        resolvable = [
            BoundCompute(spec=spec, local_names=_resolve_path_set(model, spec).local_names) for spec in specs
        ]
        try:
            _ordered_locally(model, resolvable)
        except ValueError as error:
            errors.append(checks.Error(str(error), obj=model, id="angee.E018"))
    return errors


def _check_target_field(model: type[models.Model], spec: ComputeSpec) -> list[checks.CheckMessage]:
    """Return errors for one compute's target column declaration."""

    try:
        target = model._meta.get_field(spec.field_name)
    except FieldDoesNotExist:
        return [
            checks.Error(
                f"{model._meta.label}.{spec.method_name} computes unknown field {spec.field_name!r}.",
                obj=model,
                id="angee.E015",
            )
        ]
    field = cast(models.Field, target)
    if not getattr(field, "concrete", False) or field.is_relation:
        return [
            checks.Error(
                f"{model._meta.label}.{spec.field_name} must be a concrete non-relation column to be computed.",
                obj=model,
                id="angee.E015",
            )
        ]
    if field.editable:
        return [
            checks.Error(
                f"{model._meta.label}.{spec.field_name} is computed and must declare editable=False; "
                "the compute engine is its only writer.",
                obj=model,
                id="angee.E016",
            )
        ]
    return []


def _ordered_locally(model: type[models.Model], bound: Iterable[BoundCompute]) -> tuple[BoundCompute, ...]:
    """Return computes topologically ordered over local computed-column reads."""

    remaining = {item.spec.field_name: item for item in bound}
    ordered: list[BoundCompute] = []
    while remaining:
        ready = sorted(
            name
            for name, item in remaining.items()
            if not any(dep in remaining for dep in item.local_names if dep != name)
        )
        if not ready:
            cycle = ", ".join(sorted(remaining))
            raise ValueError(f"{model._meta.label} computed fields form a local dependency cycle: {cycle}.")
        for name in ready:
            ordered.append(remaining.pop(name))
    return tuple(ordered)


def _resolve_path_set(model: type[models.Model], spec: ComputeSpec) -> _ResolvedPath:
    """Return the merged local and trigger consequences of one spec's paths."""

    local: set[str] = set()
    triggers: list[ComputeTrigger] = []
    m2m_triggers: list[M2MComputeTrigger] = []
    for path in spec.depends:
        _resolve_path(model, spec, path, collect=(local, triggers, m2m_triggers))
    # A delete-only far-side edge (``column=None``) resolves its dependents with
    # the same pre-delete query a value edge on that model and lookup already
    # runs, so keep only the one that also covers writes.
    covered = {(edge.source, edge.lookup) for edge in triggers if edge.column is not None}
    return _ResolvedPath(
        local_names=frozenset(local),
        triggers=tuple(
            edge for edge in triggers if edge.column is not None or (edge.source, edge.lookup) not in covered
        ),
        m2m_triggers=tuple(m2m_triggers),
    )


def _resolve_path(
    model: type[models.Model],
    spec: ComputeSpec,
    path: str,
    *,
    collect: tuple[set[str], list[ComputeTrigger], list[M2MComputeTrigger]] | None,
) -> bool:
    """Resolve one depends path, optionally collecting its consequences.

    Returns whether the path ends on a column (vs a membership-only relation).
    Raises :class:`ComputePathError` when a hop does not resolve. ``collect``
    receives ``(local_names, triggers, m2m_triggers)`` when the caller wants the
    inverted edges; validation passes ``None`` to only prove resolvability.
    """

    hops = tuple(part for part in path.split(".") if part)
    if not hops:
        raise ComputePathError(f"{model._meta.label}.{spec.method_name} declares an empty depends path.")

    current: type[models.Model] = model
    lookup_parts: list[str] = []
    for index, hop in enumerate(hops):
        try:
            field = current._meta.get_field(hop)
        except FieldDoesNotExist as error:
            raise ComputePathError(
                f"{model._meta.label}.{spec.method_name} depends on {path!r}, but "
                f"{current._meta.label} has no field {hop!r}."
            ) from error
        is_last = index == len(hops) - 1

        if not field.is_relation:
            if not is_last:
                raise ComputePathError(
                    f"{model._meta.label}.{spec.method_name} depends on {path!r}, but "
                    f"{current._meta.label}.{hop} is not a relation and cannot be traversed."
                )
            concrete = cast(models.Field, field)
            if collect is not None:
                local, triggers, _ = collect
                if index == 0:
                    local.update({concrete.name, concrete.attname})
                else:
                    triggers.append(
                        _trigger(spec, model, source=current, field=concrete, lookup=lookup_parts, membership=False)
                    )
            return True

        if spec.related_path is not None and (isinstance(field, ForeignObjectRel) or field.many_to_many):
            raise ComputePathError(
                f"{model._meta.label}.{spec.method_name} related path {path!r} must walk to-one relations, "
                f"but {current._meta.label}.{hop} is to-many; a copy has one source row."
            )

        if isinstance(field, ForeignObjectRel):
            if field.many_to_many:
                _collect_m2m(collect, spec, model, current, field, lookup_parts, hop)
            else:
                remote_fk = cast(models.Field, field.field)
                if collect is not None:
                    _, triggers, _ = collect
                    triggers.append(
                        _trigger(
                            spec,
                            model,
                            source=field.related_model,
                            field=remote_fk,
                            lookup=lookup_parts,
                            membership=True,
                        )
                    )
            next_model = field.related_model
        else:
            forward = cast(models.Field, field)
            if forward.many_to_many:
                _collect_m2m(collect, spec, model, current, forward, lookup_parts, hop)
            else:
                if collect is not None:
                    local, triggers, _ = collect
                    if index == 0:
                        local.update({forward.name, forward.attname})
                    else:
                        triggers.append(
                            _trigger(spec, model, source=current, field=forward, lookup=lookup_parts, membership=False)
                        )
            next_model = forward.related_model
        if next_model is None:
            raise ComputePathError(
                f"{model._meta.label}.{spec.method_name} depends on {path!r}, but "
                f"{current._meta.label}.{hop} has no related model."
            )
        lookup_parts.append(hop)
        current = next_model
    return False


def _trigger(
    spec: ComputeSpec,
    dependent: type[models.Model],
    *,
    source: type[models.Model],
    field: models.Field,
    lookup: list[str],
    membership: bool,
) -> ComputeTrigger:
    """Build one inverted edge watching ``field`` on ``source``."""

    return ComputeTrigger(
        dependent=dependent,
        field_name=spec.field_name,
        source=cast(type[models.Model], source._meta.concrete_model),
        column=field.attname,
        written_names=frozenset({field.name, field.attname}),
        lookup="__".join(lookup),
        membership=membership,
    )


def _collect_m2m(
    collect: tuple[set[str], list[ComputeTrigger], list[M2MComputeTrigger]] | None,
    spec: ComputeSpec,
    dependent: type[models.Model],
    anchor: type[models.Model],
    field: Any,
    lookup_parts: list[str],
    hop: str,
) -> None:
    """Collect the membership edges for one many-to-many hop.

    Two edges, because ``m2m_changed`` does not cover every membership change:
    the through edge fires on add/remove/clear, and the far-side edge fires on
    delete — deleting the far row drops its through rows by cascade *without*
    firing ``m2m_changed``, so membership would otherwise change with no signal
    the engine hears. The far-side edge carries no ``column``: only a delete can
    fire it, and :func:`_resolve_path_set` drops it when a value edge on the same
    far model already resolves the same dependents.
    """

    if collect is None:
        return
    _, triggers, m2m_triggers = collect
    through = field.through if isinstance(field, ForeignObjectRel) else field.remote_field.through
    m2m_triggers.append(
        M2MComputeTrigger(
            dependent=dependent,
            field_name=spec.field_name,
            through=cast(type[models.Model], through._meta.concrete_model),
            anchor_model=cast(type[models.Model], anchor._meta.concrete_model),
            lookup="__".join(lookup_parts),
        )
    )
    triggers.append(
        ComputeTrigger(
            dependent=dependent,
            field_name=spec.field_name,
            source=cast(type[models.Model], field.related_model._meta.concrete_model),
            column=None,
            written_names=frozenset(),
            lookup="__".join([*lookup_parts, hop]),
            membership=True,
        )
    )


class ComputeRegistry:
    """Process-wide inverted dependency index over the installed concrete models.

    Built from every concrete model's compute specs by ``angee.base``'s
    ``ready()`` seam, and invalidated by ``class_prepared`` so late test models
    join on the next :meth:`ensure`. Building binds the propagation signal
    receivers **per sender** — only dependency-source models get ``post_save`` /
    ``pre_delete`` / ``post_delete`` receivers (and only through models get
    ``m2m_changed``), so unrelated models keep Django's fast-delete path.
    """

    def __init__(self) -> None:
        self._built = False
        self._triggers: dict[type[models.Model], tuple[ComputeTrigger, ...]] = {}
        self._m2m_triggers: dict[type[models.Model], tuple[M2MComputeTrigger, ...]] = {}
        self._watched: dict[type[models.Model], frozenset[str]] = {}

    def invalidate(self) -> None:
        """Drop the built index so the next :meth:`ensure` rebuilds over current models."""

        self._built = False

    def ensure(self) -> None:
        """Build the index and bind per-sender receivers when stale; cheap when warm."""

        if self._built:
            return
        triggers: dict[type[models.Model], list[ComputeTrigger]] = {}
        m2m_triggers: dict[type[models.Model], list[M2MComputeTrigger]] = {}
        watched: dict[type[models.Model], set[str]] = {}
        for model in apps.get_models():
            specs = compute_specs(model)
            if specs and not getattr(model, "_angee_computes_integrated", False):
                raise ImproperlyConfigured(
                    f"{model._meta.label} declares @compute methods but is not an AngeeModel; "
                    "the engine's save/load integration only covers AngeeModel rows."
                )
            for spec in specs:
                resolved = _resolve_path_set(model, spec)
                for trigger in resolved.triggers:
                    triggers.setdefault(trigger.source, []).append(trigger)
                    if trigger.column is not None:
                        watched.setdefault(trigger.source, set()).add(trigger.column)
                for m2m_trigger in resolved.m2m_triggers:
                    m2m_triggers.setdefault(m2m_trigger.through, []).append(m2m_trigger)
        self._triggers = {
            model: tuple(sorted(edges, key=lambda t: (t.dependent._meta.label_lower, t.field_name, t.lookup)))
            for model, edges in triggers.items()
        }
        self._m2m_triggers = {
            model: tuple(sorted(edges, key=lambda t: (t.dependent._meta.label_lower, t.field_name, t.lookup)))
            for model, edges in m2m_triggers.items()
        }
        self._watched = {model: frozenset(columns) for model, columns in watched.items()}
        self._bind_receivers()
        self._built = True

    def triggers_for(self, model: type[models.Model]) -> tuple[ComputeTrigger, ...]:
        """Return the edges fired by writes/deletes of ``model`` rows."""

        self.ensure()
        return self._triggers.get(cast(type[models.Model], model._meta.concrete_model), ())

    def m2m_triggers_for(self, through: type[models.Model]) -> tuple[M2MComputeTrigger, ...]:
        """Return the membership edges fired by ``through`` m2m changes."""

        self.ensure()
        return self._m2m_triggers.get(cast(type[models.Model], through._meta.concrete_model), ())

    def watched_columns(self, model: type[models.Model]) -> frozenset[str]:
        """Return the attnames on ``model`` whose old values loads must snapshot."""

        self.ensure()
        return self._watched.get(cast(type[models.Model], model._meta.concrete_model), frozenset())

    def _bind_receivers(self) -> None:
        """Connect propagation receivers to exactly the trigger senders.

        ``dispatch_uid`` keeps rebinding after an invalidation idempotent; a
        receiver left on a model that stopped being a source is a harmless dict
        miss on the next fire.
        """

        for model in self._triggers:
            label = model._meta.label_lower
            post_save.connect(_on_post_save, sender=model, dispatch_uid=f"{_DISPATCH_PREFIX}.post_save.{label}")
            pre_delete.connect(_on_pre_delete, sender=model, dispatch_uid=f"{_DISPATCH_PREFIX}.pre_delete.{label}")
            post_delete.connect(_on_post_delete, sender=model, dispatch_uid=f"{_DISPATCH_PREFIX}.post_delete.{label}")
        for through in self._m2m_triggers:
            label = through._meta.label_lower
            m2m_changed.connect(_on_m2m_changed, sender=through, dispatch_uid=f"{_DISPATCH_PREFIX}.m2m.{label}")


_DISPATCH_PREFIX = "angee.base.computes"
"""Dispatch-uid prefix for the registry's per-sender signal receivers."""

compute_registry = ComputeRegistry()
"""The process-wide compute dependency index."""


def snapshot_watched(instance: models.Model, field_names: Iterable[str]) -> None:
    """Record loaded old values of watched columns on a freshly loaded row.

    Only columns actually loaded are recorded (a deferred load stays lazy); an
    absent old value makes a later membership edge fire for the new value only,
    the drift the repair pass owns.
    """

    watched = compute_registry.watched_columns(type(instance))
    if not watched:
        return
    loaded = watched.intersection(field_names)
    if loaded:
        snapshot = cast(dict[str, Any], instance.__dict__.setdefault("_angee_compute_snapshot", {}))
        snapshot.update({name: getattr(instance, name) for name in loaded})


def apply_local_computes(instance: models.Model, update_fields: Any, *, adding: bool = False) -> set[str] | None:
    """Recompute the row's local specs for one ``save()``; return the fan-out.

    On a full save (``update_fields is None``) every compute runs and is
    assigned; the return is ``None`` (nothing to fold). On a partial save only
    computes whose local dependencies intersect the written names run, and the
    changed computed columns are returned (with ``auto_now`` columns folded) for
    the caller to merge into ``update_fields`` — the contract that keeps
    ``ChangePayload.changed_fields``, history, and audit stamping honest.

    ``adding`` marks an insert: computes reading a reverse or many-to-many
    relation cannot run on an unsaved row and are deferred to
    :func:`finalize_created_computes` after the insert.
    """

    specs = bound_computes(type(instance))
    if not specs:
        return None
    if update_fields is None:
        # A stored computed value is one shared column, so it must not depend on
        # the saving actor's REBAC scope: computes always evaluate elevated.
        with system_context(reason=RECOMPUTE_REASON):
            for item in specs:
                if adding and item.requires_pk:
                    continue
                setattr(instance, item.spec.field_name, _run_compute(instance, item.spec))
        return None
    written = set(update_fields)
    if not written:
        return None
    changed: set[str] = set()
    with system_context(reason=RECOMPUTE_REASON):
        for item in specs:
            if not item.local_names.intersection(written):
                continue
            value = _run_compute(instance, item.spec)
            if value != getattr(instance, item.spec.field_name):
                setattr(instance, item.spec.field_name, value)
            # A dependency was written, so the stored value must ride this save even
            # when the in-memory value already matched (it may differ from the DB).
            changed.add(item.spec.field_name)
            written.add(item.spec.field_name)
    if not changed:
        return None
    return update_fields_with_auto_now(instance, written)


def finalize_created_computes(instance: models.Model) -> None:
    """Run the relation-reading computes an insert had to defer; write once.

    Called by ``AngeeModel.save()`` after an insert completes. Nothing can point
    at a brand-new row yet, so most deferred computes match their column default
    and no second write happens; a compute deriving from local state too (a
    total that subtracts a discount over zero lines) issues one targeted
    ``UPDATE``, the ``HierarchyMixin._save_created`` shape.
    """

    specs = [item for item in bound_computes(type(instance)) if item.requires_pk]
    if not specs:
        return
    changed: set[str] = set()
    with system_context(reason=RECOMPUTE_REASON):
        for item in specs:
            if _assign_if_changed(instance, item.spec):
                changed.add(item.spec.field_name)
    if changed:
        instance.save(update_fields=update_fields_with_auto_now(instance, changed))


def recompute_queryset(queryset: models.QuerySet[Any], field_names: Iterable[str] | None = None) -> int:
    """Recompute stored computes for the rows a queryset addresses; return rows written.

    Materializes the pks with the default ordering cleared (``Meta.ordering`` may
    name alias fields a values read cannot resolve) and hands them to
    :func:`recompute_rows`; the queryset methods on ``AngeeQuerySet`` /
    ``AngeeUnscopedQuerySet`` are one-line dispatches to this owner.
    """

    pks = list(queryset.order_by().values_list("pk", flat=True))
    return recompute_rows(queryset.model, pks, field_names)


def recompute_rows(
    model: type[models.Model],
    pks: Iterable[Any],
    field_names: Iterable[str] | None = None,
) -> int:
    """Recompute stored computed columns on the addressed rows; return rows written.

    The idempotent repair-pass owner for computed drift: rows are re-read and
    re-saved (``update_fields`` of only the changed columns) under
    ``system_context`` through the base manager, so REBAC scope never hides a
    dependent row and the write is system-attributed. Saving through ``save()``
    keeps ``post_save`` receivers, history, and ``changes`` publishers honest,
    and lets a recompute cascade to further dependents.
    """

    pk_list = [pk for pk in pks if not _in_flight(model, pk)]
    if not pk_list:
        return 0
    wanted = set(field_names) if field_names is not None else None
    specs = [item for item in bound_computes(model) if wanted is None or item.spec.field_name in wanted]
    if not specs:
        return 0
    written_rows = 0
    with system_context(reason=RECOMPUTE_REASON):
        writer = system_writer(model)
        for row in writer.filter(pk__in=pk_list).order_by("pk"):
            changed = [
                item.spec.field_name
                for item in specs
                if _assign_if_changed(row, item.spec)
            ]
            if not changed:
                continue
            token = _mark_in_flight(model, row.pk)
            try:
                row.save(update_fields=update_fields_with_auto_now(row, set(changed)))
            finally:
                _clear_in_flight(token)
            written_rows += 1
    return written_rows


def recompute_model(
    model: type[models.Model],
    field_names: Iterable[str] | None = None,
    *,
    batch_size: int = 1000,
) -> int:
    """Recompute stored computes for every row of ``model``; return rows written.

    The whole-table repair/backfill pass behind ``manage.py recompute`` — run it
    after adding a stored compute to an existing model, or to repair bulk-path
    drift at scale.
    """

    with system_context(reason=RECOMPUTE_REASON):
        pks = list(system_writer(model).order_by("pk").values_list("pk", flat=True))
    written = 0
    for start in range(0, len(pks), batch_size):
        written += recompute_rows(model, pks[start : start + batch_size], field_names)
    return written


def compute_models() -> tuple[type[models.Model], ...]:
    """Return the installed concrete models that declare stored computes."""

    return tuple(
        model
        for model in apps.get_models()
        if not model._meta.abstract and compute_specs(model)
    )


def _run_compute(instance: models.Model, spec: ComputeSpec) -> Any:
    """Return the value ``spec``'s method derives for ``instance``."""

    method = getattr(instance, spec.method_name)
    return method()


def _assign_if_changed(instance: models.Model, spec: ComputeSpec) -> bool:
    """Recompute one column on ``instance``; assign and report a changed value."""

    value = _run_compute(instance, spec)
    if value == getattr(instance, spec.field_name):
        return False
    setattr(instance, spec.field_name, value)
    return True


_IN_FLIGHT: contextvars.ContextVar[frozenset[tuple[str, Any]]] = contextvars.ContextVar(
    "angee_compute_in_flight", default=frozenset()
)
"""Rows currently being recomputed on this execution context — the cycle breaker.

A recompute save fires the same signal receivers as any save, so a dependency
cycle across models would recurse forever; a row already in flight is skipped
and converges instead."""


def _in_flight(model: type[models.Model], pk: Any) -> bool:
    return (model._meta.label_lower, pk) in _IN_FLIGHT.get()


def _mark_in_flight(model: type[models.Model], pk: Any) -> contextvars.Token[frozenset[tuple[str, Any]]]:
    return _IN_FLIGHT.set(_IN_FLIGHT.get() | {(model._meta.label_lower, pk)})


def _clear_in_flight(token: contextvars.Token[frozenset[tuple[str, Any]]]) -> None:
    _IN_FLIGHT.reset(token)


def _affected_pks(trigger: ComputeTrigger, anchors: set[Any]) -> set[Any]:
    """Resolve the dependent rows one fired edge invalidates."""

    anchors = {anchor for anchor in anchors if anchor is not None}
    if not anchors:
        return set()
    if not trigger.lookup:
        # The anchor model is the dependent itself (a first-hop reverse FK):
        # the anchor pks are the dependent pks.
        return anchors
    queryset = system_writer(trigger.dependent)
    lookup = f"{trigger.lookup}__pk__in"
    return set(queryset.filter(**{lookup: anchors}).order_by().values_list("pk", flat=True))


def _fire(pending: dict[type[models.Model], dict[Any, set[str]]]) -> None:
    """Recompute every collected (dependent, row, columns) group."""

    for dependent, rows in pending.items():
        by_fields: dict[frozenset[str], set[Any]] = {}
        for pk, field_names in rows.items():
            by_fields.setdefault(frozenset(field_names), set()).add(pk)
        for shared_fields, pks in by_fields.items():
            recompute_rows(dependent, pks, shared_fields)


def _collect(
    pending: dict[type[models.Model], dict[Any, set[str]]],
    trigger: ComputeTrigger | M2MComputeTrigger,
    pks: set[Any],
) -> None:
    """Accumulate affected rows for one fired edge into the pending map."""

    if not pks:
        return
    rows = pending.setdefault(trigger.dependent, {})
    for pk in pks:
        rows.setdefault(pk, set()).add(trigger.field_name)


def _on_post_save(
    sender: type[models.Model],
    instance: models.Model,
    created: bool,
    raw: bool = False,
    update_fields: Any = None,
    **kwargs: Any,
) -> None:
    """Propagate a saved row's dependency changes to its dependents."""

    del kwargs
    if raw:
        return
    triggers = compute_registry.triggers_for(sender)
    if not triggers:
        return
    snapshot = cast(dict[str, Any], instance.__dict__.get("_angee_compute_snapshot") or {})
    written = {str(name) for name in update_fields} if update_fields is not None else None
    pending: dict[type[models.Model], dict[Any, set[str]]] = {}
    with system_context(reason=RECOMPUTE_REASON):
        for trigger in triggers:
            if trigger.column is None:
                continue  # delete-only membership edge
            if written is not None and not created and not trigger.written_names.intersection(written):
                continue
            old = snapshot.get(trigger.column, _UNKNOWN) if not created else _UNKNOWN
            new = getattr(instance, trigger.column, None)
            if not created and old is not _UNKNOWN and old == new:
                continue
            if trigger.membership:
                anchors = {new} if old is _UNKNOWN else {old, new}
            else:
                anchors = {instance.pk}
            _collect(pending, trigger, _affected_pks(trigger, anchors))
        _fire(pending)
    # Re-baseline the snapshot to the saved values — but never through a deferred
    # column, whose getattr would issue one hidden query per save.
    watched = compute_registry.watched_columns(sender)
    snapshot_watched(instance, watched - instance.get_deferred_fields())


@dataclass(slots=True)
class _DeleteBatch:
    """Dependents resolved for one sender's rows during a single delete pass."""

    pending: dict[type[models.Model], dict[Any, set[str]]]
    deleted: set[Any]


_DELETE_BATCHES: contextvars.ContextVar[dict[type[models.Model], _DeleteBatch] | None] = contextvars.ContextVar(
    "angee_compute_delete_batches", default=None
)
"""Per-sender delete batches accumulated between ``pre_delete`` and ``post_delete``.

Django's collector sends every ``pre_delete``, then deletes a model's rows as one
batch and only then sends that model's ``post_delete`` signals — so the first
``post_delete`` for a sender already sees the whole batch gone and can recompute
each affected dependent once, instead of once per deleted row."""


def _delete_batch(sender: type[models.Model]) -> _DeleteBatch:
    """Return this execution context's accumulating batch for ``sender``."""

    batches = _DELETE_BATCHES.get()
    if batches is None:
        batches = {}
        _DELETE_BATCHES.set(batches)
    return batches.setdefault(sender, _DeleteBatch(pending={}, deleted=set()))


def _on_pre_delete(sender: type[models.Model], instance: models.Model, **kwargs: Any) -> None:
    """Resolve the dependents a row's disappearance will invalidate, while it exists."""

    del kwargs
    triggers = compute_registry.triggers_for(sender)
    if not triggers:
        return
    batch = _delete_batch(sender)
    batch.deleted.add(instance.pk)
    pending = batch.pending
    with system_context(reason=RECOMPUTE_REASON):
        for trigger in triggers:
            if trigger.membership and trigger.column is not None:
                anchors = {getattr(instance, trigger.column, None)}
                _collect(pending, trigger, _affected_pks(trigger, anchors))
            else:
                queryset = system_writer(trigger.dependent)
                if trigger.lookup:
                    rows = queryset.filter(**{f"{trigger.lookup}__pk": instance.pk}).order_by()
                    pks = set(rows.values_list("pk", flat=True))
                else:
                    pks = {instance.pk}
                _collect(pending, trigger, pks)


def _on_post_delete(sender: type[models.Model], instance: models.Model, **kwargs: Any) -> None:
    """Recompute the dependents resolved before this sender's rows were deleted.

    The whole batch is already gone by the first ``post_delete``, so this drains
    the accumulated batch once; the remaining signals of the same delete find it
    empty and do no work.
    """

    del kwargs
    batches = _DELETE_BATCHES.get()
    batch = batches.pop(sender, None) if batches is not None else None
    if batch is None or not batch.pending:
        return
    # A deleted row can no longer be a dependent of itself (self-referential
    # paths); other dependents keep their pks — they only coincide numerically.
    for dependent, rows in batch.pending.items():
        if isinstance(instance, dependent):
            for pk in batch.deleted:
                rows.pop(pk, None)
    with system_context(reason=RECOMPUTE_REASON):
        _fire(batch.pending)


def _on_m2m_changed(
    sender: type[models.Model],
    instance: models.Model,
    action: str,
    reverse: bool,
    model: type[models.Model],
    pk_set: set[Any] | None,
    **kwargs: Any,
) -> None:
    """Propagate a many-to-many membership change to dependent computed columns.

    ``post_add``/``post_remove`` resolve and fire directly. A clear is split:
    the affected rows are resolved at ``pre_clear`` (membership still exists)
    and recomputed at ``post_clear`` (membership is gone). A clear initiated
    from the far side of a trigger's anchor cannot name the vanishing anchors
    and is repair-pass drift.
    """

    del reverse, kwargs
    if action == "post_clear":
        pending = cast(
            "dict[type[models.Model], dict[Any, set[str]]] | None",
            instance.__dict__.pop("_angee_compute_m2m_pending", None),
        )
        if pending:
            with system_context(reason=RECOMPUTE_REASON):
                _fire(pending)
        return
    if action not in {"post_add", "post_remove", "pre_clear"}:
        return
    triggers = compute_registry.m2m_triggers_for(sender)
    if not triggers:
        return
    pending = {}
    with system_context(reason=RECOMPUTE_REASON):
        for trigger in triggers:
            anchors: set[Any] = set()
            if isinstance(instance, trigger.anchor_model):
                anchors.add(instance.pk)
            elif pk_set and issubclass(trigger.anchor_model, model):
                anchors.update(pk_set)
            if not anchors:
                continue
            if trigger.lookup:
                queryset = system_writer(trigger.dependent)
                pks = set(
                    queryset.filter(**{f"{trigger.lookup}__pk__in": anchors}).order_by().values_list("pk", flat=True)
                )
            else:
                pks = anchors
            _collect(pending, trigger, pks)
        if action == "pre_clear":
            instance.__dict__["_angee_compute_m2m_pending"] = pending
            return
        _fire(pending)


def _on_class_prepared(sender: type[models.Model], **kwargs: Any) -> None:
    """Invalidate the dependency index when a late model class is prepared."""

    del sender, kwargs
    compute_registry.invalidate()


class_prepared.connect(_on_class_prepared, dispatch_uid=f"{_DISPATCH_PREFIX}.class_prepared")
