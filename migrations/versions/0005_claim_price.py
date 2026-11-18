"""Private per-giver price on a claim: what I'm spending, visible only to me.

Revision ID: 0005_claim_price
Revises: 0004_usability
Create Date: 2026-11-17

Nullable on purpose: NULL means the giver has not said, and Gifts I'm Giving then falls back to the price on the
item itself, which is what every existing row does today.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0005_claim_price"
down_revision = "0004_usability"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("purchases", schema=None) as batch_op:
        batch_op.add_column(sa.Column("price", sa.Float(), nullable=True))


def downgrade():
    with op.batch_alter_table("purchases", schema=None) as batch_op:
        batch_op.drop_column("price")
