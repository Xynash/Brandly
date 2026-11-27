"""Add compliance preset selections to brand hubs."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b03da8293d1f"
down_revision = "7db9ba0954c0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "brand_hubs",
        sa.Column("preset_ids", postgresql.JSONB(), server_default="[]", nullable=False),
    )


def downgrade():
    op.drop_column("brand_hubs", "preset_ids")
