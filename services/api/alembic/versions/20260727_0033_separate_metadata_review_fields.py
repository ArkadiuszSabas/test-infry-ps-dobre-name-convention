"""Create metadata-free current Review versions for historical documents.

Revision ID: 20260727_0033
Revises: 20260724_0033
Create Date: 2026-07-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260727_0033"
down_revision: str | Sequence[str] | None = "20260724_0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Append a metadata-free snapshot and reset only active approval workflows."""

    op.execute(
        sa.text(
            """
            with metadata_attributes as (
                select attribute.id::text as id
                from attribute_definitions attribute
                join attribute_categories category on category.id = attribute.category_id
                where category.status = 'active'
                  and category.flags ->> 'isMetadata' = 'true'
            ), candidates as (
                select
                    review.id as review_id,
                    review.document_id,
                    review.current_version,
                    version.data_source,
                    version.source_pipeline_run_id,
                    version.created_by_actor_id,
                    coalesce(
                        jsonb_agg(field.value order by field.ordinality)
                            filter (
                                where not exists (
                                    select 1
                                    from metadata_attributes metadata_attribute
                                    where metadata_attribute.id = field.value ->> 'attribute_id'
                                )
                            ),
                        '[]'::jsonb
                    ) as attributes
                from document_reviews review
                join document_review_versions version
                  on version.review_id = review.id
                 and version.version = review.current_version
                cross join lateral jsonb_array_elements(version.attributes)
                    with ordinality as field(value, ordinality)
                where exists (
                    select 1
                    from jsonb_array_elements(version.attributes) as candidate_field(value)
                    where candidate_field.value ->> 'attribute_id' in (
                        select id from metadata_attributes
                    )
                )
                group by
                    review.id,
                    review.document_id,
                    review.current_version,
                    version.data_source,
                    version.source_pipeline_run_id,
                    version.created_by_actor_id
            ), inserted_versions as (
                insert into document_review_versions (
                    review_id,
                    version,
                    data_source,
                    is_reprocessing,
                    source_pipeline_run_id,
                    attributes,
                    validations,
                    quality_score,
                    created_by_actor_id,
                    created_at
                )
                select
                    review_id,
                    current_version + 1,
                    data_source,
                    false,
                    source_pipeline_run_id,
                    attributes,
                    '[]'::jsonb,
                    null,
                    created_by_actor_id,
                    now()
                from candidates
                returning review_id, version
            ), advanced_reviews as (
                update document_reviews review
                set current_version = inserted.version, updated_at = now()
                from inserted_versions inserted
                where review.id = inserted.review_id
                returning review.document_id, inserted.version
            ), reset_workflows as (
                update document_approval_workflows workflow
                set
                    current_run = workflow.current_run + 1,
                    review_version = advanced.version,
                    status = 'waiting_for_review',
                    updated_at = now()
                from advanced_reviews advanced
                where workflow.document_id = advanced.document_id
                returning workflow.document_id
            )
            update documents document
            set status = 'waiting_for_review', updated_at = now()
            from reset_workflows workflow
            where document.id = workflow.document_id
            """
        )
    )


def downgrade() -> None:
    raise RuntimeError(
        "Cannot safely remove metadata-separation Review versions after they are created."
    )
