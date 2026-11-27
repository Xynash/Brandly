"""Store encrypted provider keys and attribute generations to users."""

import sqlalchemy as sa
from alembic import op

revision = "68f36018cd61"
down_revision = "b03da8293d1f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "provider_keys",
        sa.Column("agency_id", sa.Uuid(), sa.ForeignKey("agencies.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("provider", sa.String(20), primary_key=True),
        sa.Column("encrypted_key", sa.Text(), nullable=False),
    )
    op.add_column("generations", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_generations_user_id", "generations", "users", ["user_id"], ["id"], ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("fk_generations_user_id", "generations", type_="foreignkey")
    op.drop_column("generations", "user_id")
    op.drop_table("provider_keys")
