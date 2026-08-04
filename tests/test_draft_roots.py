"""The generated draft roots serve create defaults and live recompute.

``tests.scopedemo.ScopedDoc`` is the fixture: its ``get_create_defaults``
derives ``scope`` from the actor's sole membership and its ``@onchange``
handler recomputes ``title_length`` from ``title``. These drive the generated
``<res>_defaults`` / ``<res>_onchange`` query roots over a built schema:

1. defaults return field defaults plus the membership-derived scope,
   intersected with the creatable set, caller seeds winning — except a relation
   seed that resolves to nothing, which falls through to the model rule;
2. onchange recomputes a create draft, overlays an edit draft resolved through
   the actor's write scope, surfaces handler warnings, and maps domain errors
   in-band;
3. both roots require an authenticated session;
4. the resource metadata advertises the roots, capabilities, and trigger set.
"""

from __future__ import annotations

from typing import Any

import pytest
import strawberry
import strawberry_django
from django.core.management import call_command
from rebac import (
    RelationshipTuple,
    actor_context,
    system_context,
    to_object_ref,
    to_subject_ref,
    write_relationships,
)
from strawberry import auto
from strawberry_django_hasura import hasura_config

from angee.graphql.data.draft import decode_draft_values
from angee.graphql.data.hasura import (
    AngeeHasuraWriteBackend,
    hasura_model_resource,
    public_pk_decoder,
)
from angee.graphql.data.metadata import data_resource_metadata
from angee.graphql.node import AngeeNode
from tests.conftest import create_user, execute_schema, result_data
from tests.scopedemo.models import Scope, ScopedDoc


@strawberry_django.type(ScopedDoc)
class DraftDocType(AngeeNode):
    """GraphQL projection of a locally scoped document with a derived column."""

    title: auto
    title_length: auto


_RESOURCE = hasura_model_resource(
    DraftDocType,
    model=ScopedDoc,
    name="scoped_docs",
    filterable=["id", "title"],
    sortable=["title"],
    aggregatable=["id"],
    insertable=["title", "scope"],
    updatable=["title"],
    field_id_decode={"scope": public_pk_decoder(Scope)},
    write_backend=AngeeHasuraWriteBackend(ScopedDoc, public_id_fields=("scope",)),
    id_column="sqid",
)

_SCHEMA = strawberry.Schema(
    query=_RESOURCE.query,
    mutation=_RESOURCE.mutation,
    types=[DraftDocType, *_RESOURCE.types],
    config=hasura_config(),
)

_DEFAULTS = """
query($defaults: JSON) {
  scoped_docs_defaults(defaults: $defaults)
}
"""

_ONCHANGE = """
query($values: JSON!, $changed: [String!]!, $id: ID) {
  scoped_docs_onchange(values: $values, changed: $changed, id: $id) {
    values
    warning { title message }
    validation_errors
  }
}
"""


def _grant(scope: Any, relation: str, user: Any) -> None:
    """Write one direct relationship tuple for ``user`` on ``scope``."""

    write_relationships(
        [
            RelationshipTuple(
                resource=to_object_ref(scope),
                relation=relation,
                subject=to_subject_ref(user),
            )
        ]
    )


def _sole_member(username: str) -> tuple[Any, Any]:
    """Return a user plus the one scope they are a direct member of."""

    call_command("rebac", "sync", verbosity=0)
    member = create_user(username)
    with system_context(reason="test draft roots setup"):
        scope = Scope.objects.create(name=f"Scope {username}")
    _grant(scope, "direct_member", member)
    return member, scope


def test_schema_exposes_the_draft_roots() -> None:
    sdl = _SCHEMA.as_str()
    assert "scoped_docs_defaults" in sdl
    assert "scoped_docs_onchange" in sdl
    assert "OnchangePayload" in sdl


def test_resource_metadata_advertises_the_draft_surface() -> None:
    (metadata,) = data_resource_metadata(_RESOURCE.query)
    assert metadata.roots.defaults_name == "scoped_docs_defaults"
    assert metadata.roots.onchange_name == "scoped_docs_onchange"
    assert "defaults" in metadata.capabilities
    assert "onchange" in metadata.capabilities
    assert metadata.onchange_fields == ("title",)
    wire = metadata.as_wire(schema_name="console")
    assert wire["roots"]["defaults"] == "scoped_docs_defaults"  # type: ignore[index]
    assert wire["roots"]["onchange"] == "scoped_docs_onchange"  # type: ignore[index]
    assert wire["onchangeFields"] == ["title"]


@pytest.mark.django_db
def test_defaults_return_field_and_membership_defaults() -> None:
    member, scope = _sole_member("draft-defaults")

    result = execute_schema(_SCHEMA, _DEFAULTS, {}, user=member)
    values = result_data(result)["scoped_docs_defaults"]

    assert values == {"title": "", "scope": scope.public_id}


@pytest.mark.django_db
def test_defaults_fold_caller_seeds_and_keep_the_creatable_set() -> None:
    member, scope = _sole_member("draft-seeded")

    result = execute_schema(
        _SCHEMA,
        _DEFAULTS,
        {"defaults": {"title": "Seeded", "title_length": 99, "unknown": 1}},
        user=member,
    )
    values = result_data(result)["scoped_docs_defaults"]

    assert values == {"title": "Seeded", "scope": scope.public_id}


@pytest.mark.django_db
def test_a_defaults_seed_drops_a_relation_it_cannot_resolve() -> None:
    """An unresolvable relation seed is dropped, never decoded to ``None``.

    ``None`` reads as "the caller pinned no relation", which lets a
    ``get_create_defaults`` override answer with a *different* row than the one
    seeded (and, with no override, sends an explicit ``null`` that blanks the
    form's own client default). The seed must fall through to the model rule
    instead. An onchange draft keeps the opposite reading — a blank relation
    there is the user clearing the field — so the default stays ``None``.
    """

    member, _scope = _sole_member("draft-unreachable")
    with system_context(reason="test draft roots setup"):
        unreachable = Scope.objects.create(name="Unreachable")

    with actor_context(member):
        seed = {"scope": unreachable.public_id}
        assert decode_draft_values(ScopedDoc, seed, skip_unresolved_relations=True) == {}
        assert decode_draft_values(ScopedDoc, seed) == {"scope": None}


@pytest.mark.django_db
def test_defaults_require_an_authenticated_session() -> None:
    call_command("rebac", "sync", verbosity=0)

    result = execute_schema(_SCHEMA, _DEFAULTS, {})

    assert result.errors is not None


@pytest.mark.django_db
def test_onchange_recomputes_a_create_draft() -> None:
    member, _scope = _sole_member("draft-recompute")

    result = execute_schema(
        _SCHEMA,
        _ONCHANGE,
        {"values": {"title": "Hello world"}, "changed": ["title"]},
        user=member,
    )
    payload = result_data(result)["scoped_docs_onchange"]

    assert payload["values"] == {"title_length": 11}
    assert payload["warning"] is None
    assert payload["validation_errors"] is None


@pytest.mark.django_db
def test_onchange_surfaces_a_handler_warning() -> None:
    member, _scope = _sole_member("draft-warning")

    result = execute_schema(
        _SCHEMA,
        _ONCHANGE,
        {"values": {"title": "x" * 60}, "changed": ["title"]},
        user=member,
    )
    payload = result_data(result)["scoped_docs_onchange"]

    assert payload["values"] == {"title_length": 60}
    assert payload["warning"] == {"title": "Long title", "message": "That title is getting long."}


@pytest.mark.django_db
def test_onchange_ignores_untriggered_changes() -> None:
    member, _scope = _sole_member("draft-untriggered")

    result = execute_schema(
        _SCHEMA,
        _ONCHANGE,
        {"values": {"title": "Hello"}, "changed": ["scope"]},
        user=member,
    )
    payload = result_data(result)["scoped_docs_onchange"]

    assert payload["values"] == {}


@pytest.mark.django_db
def test_onchange_overlays_an_edit_draft_on_the_stored_row() -> None:
    member, scope = _sole_member("draft-edit")
    with system_context(reason="test draft roots setup"):
        doc = ScopedDoc.objects.create(title="Stored title", scope=scope)

    result = execute_schema(
        _SCHEMA,
        _ONCHANGE,
        {"values": {"title": "New"}, "changed": ["title"], "id": doc.public_id},
        user=member,
    )
    payload = result_data(result)["scoped_docs_onchange"]

    assert payload["values"] == {"title_length": 3}
    with system_context(reason="test draft roots read"):
        doc.refresh_from_db()
    assert doc.title == "Stored title"


@pytest.mark.django_db
def test_onchange_edit_denies_a_row_outside_the_actor_write_scope() -> None:
    member, scope = _sole_member("draft-owner")
    stranger = create_user("draft-stranger")
    with system_context(reason="test draft roots setup"):
        doc = ScopedDoc.objects.create(title="Private", scope=scope)

    result = execute_schema(
        _SCHEMA,
        _ONCHANGE,
        {"values": {"title": "New"}, "changed": ["title"], "id": doc.public_id},
        user=stranger,
    )
    payload = result_data(result)["scoped_docs_onchange"]

    assert payload["values"] == {}
    assert payload["validation_errors"] is not None


@pytest.mark.django_db
def test_onchange_maps_a_malformed_draft_value_in_band() -> None:
    member, _scope = _sole_member("draft-malformed")

    result = execute_schema(
        _SCHEMA,
        _ONCHANGE,
        {"values": {"title": "ok", "title_length": "not a number"}, "changed": ["title"]},
        user=member,
    )
    payload = result_data(result)["scoped_docs_onchange"]

    assert payload["values"] == {}
    assert payload["validation_errors"] is not None
