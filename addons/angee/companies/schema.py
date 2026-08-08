"""GraphQL schema contributions for Angee companies.

The company tree is exposed on the admin console. Reads are open to any
authenticated actor for this slice (see ``permissions.zed`` — the actor-context
slice narrows them to members); writes are admin-gated by ``permissions.zed``
and the resource write backend. ``parent`` and ``organization`` project as
public-id scalars (the knowledge page pattern for nullable FKs) and accept the
related row's public id on write.
"""

from __future__ import annotations

from typing import Any, cast

import strawberry
import strawberry_django
from django.apps import apps
from strawberry import auto

from angee.graphql.data import AngeeHasuraWriteBackend, hasura_model_resource, public_pk_decoder
from angee.graphql.ids import to_public_id
from angee.graphql.node import AngeeNode

Company = apps.get_model("companies", "Company")
Organization = apps.get_model("parties", "Organization")


@strawberry_django.type(Company)
class CompanyType(AngeeNode):
    """Admin projection of one company in the tree."""

    name: auto
    is_archived: auto
    created_at: auto
    updated_at: auto

    @strawberry_django.field(only=["parent_id"])
    def parent(self) -> strawberry.ID | None:
        """Return the parent company's public id, if the company has one."""

        return to_public_id(Company, cast(Any, self).parent_id)

    @strawberry_django.field(only=["organization_id"])
    def organization(self) -> strawberry.ID | None:
        """Return the linked organization's public id, if the company has one."""

        return to_public_id(Organization, cast(Any, self).organization_id)


_COMPANY_RESOURCE = hasura_model_resource(
    CompanyType,
    model=Company,
    name="companies",
    filterable=["id", "name", "parent", "is_archived"],
    sortable=["name", "created_at", "updated_at"],
    aggregatable=["id"],
    groupable=["parent", "is_archived"],
    writable=["name", "parent", "organization", "is_archived"],
    field_id_decode={
        "parent": public_pk_decoder(Company),
        "organization": public_pk_decoder(Organization),
    },
    write_backend=AngeeHasuraWriteBackend(Company, public_id_fields=("parent", "organization")),
    id_column="sqid",
)


schemas = {
    "console": {
        "query": [_COMPANY_RESOURCE.query],
        "mutation": [_COMPANY_RESOURCE.mutation],
        "types": [CompanyType, *_COMPANY_RESOURCE.types],
    },
}
