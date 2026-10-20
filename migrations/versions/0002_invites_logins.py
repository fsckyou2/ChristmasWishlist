"""Invites, single-use magic links, and the one-owner check on wishlist items.

Revision ID: 0002_invites_logins
Revises: 0001_baseline
Create Date: 2026-10-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_invites_logins"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

OWNER_CHECK = "ck_wishlist_items_exactly_one_owner"


def upgrade():
    op.create_table(
        "invites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("used_by_id", sa.Integer(), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["used_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("invites") as batch_op:
        batch_op.create_index(batch_op.f("ix_invites_token_hash"), ["token_hash"], unique=True)

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("last_login_at", sa.DateTime(), nullable=True))

    # Pre-Alembic databases named these indexes idx_users_*; match what the models (and fresh databases) use
    existing = {ix["name"] for ix in sa.inspect(op.get_bind()).get_indexes("users")}
    for column in ("email", "username"):
        if f"idx_users_{column}" in existing:
            op.drop_index(f"idx_users_{column}", table_name="users")
        if f"ix_users_{column}" not in existing:
            op.create_index(f"ix_users_{column}", "users", [column], unique=True)

    # Every item belongs to exactly one list. Refuse to continue (rather than silently drop rows) if not.
    bad = (
        op.get_bind()
        .execute(sa.text("SELECT COUNT(*) FROM wishlist_items WHERE (user_id IS NULL) = (proxy_wishlist_id IS NULL)"))
        .scalar()
    )
    if bad:
        raise RuntimeError(
            f"{bad} wishlist_items row(s) have neither or both of user_id/proxy_wishlist_id; fix them before upgrading"
        )
    with op.batch_alter_table("wishlist_items", recreate="always", table_kwargs={"sqlite_autoincrement": True}) as b:
        b.create_check_constraint(OWNER_CHECK, "(user_id IS NULL) <> (proxy_wishlist_id IS NULL)")


def downgrade():
    with op.batch_alter_table("wishlist_items", recreate="always", table_kwargs={"sqlite_autoincrement": True}) as b:
        b.drop_constraint(OWNER_CHECK, type_="check")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("last_login_at")

    with op.batch_alter_table("invites") as batch_op:
        batch_op.drop_index(batch_op.f("ix_invites_token_hash"))
    op.drop_table("invites")
