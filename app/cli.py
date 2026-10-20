"""Flask CLI commands for deploy-time and administrative tasks."""

import os

import click
from flask import current_app
from flask.cli import with_appcontext

# The Alembic revision that matches the schema of v3.5.2, the last release before Alembic.
BASELINE_REVISION = "0001_baseline"

# Columns a pre-Alembic database must already have to be adopted at the baseline.
_LEGACY_REQUIRED_COLUMNS = {
    "users": {"username", "password_hash", "has_seen_tour"},
    "wishlist_items": {"proxy_wishlist_id", "added_by_id", "available_images"},
    "purchases": {"purchased", "received", "wrapped"},
    "wishlist_delegates": {"can_add_items", "can_edit_items", "can_remove_items"},
}


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Create or upgrade the database schema. Safe to run on every start."""
    from flask_migrate import stamp, upgrade
    from sqlalchemy import inspect

    from app import db

    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())

    if tables and "alembic_version" not in tables:
        missing = []
        for table, columns in _LEGACY_REQUIRED_COLUMNS.items():
            if table not in tables:
                missing.append(table)
                continue
            present = {col["name"] for col in inspector.get_columns(table)}
            missing.extend(f"{table}.{col}" for col in sorted(columns - present))
        if missing:
            raise click.ClickException(
                "This database predates v3.5.2 and is missing: "
                + ", ".join(missing)
                + ". Start the v3.5.2 image once to run its legacy migrations, then upgrade."
            )
        click.echo(f"Adopting existing pre-Alembic database at revision {BASELINE_REVISION}")
        stamp(revision=BASELINE_REVISION)

    upgrade()
    click.echo("Database schema is up to date.")


@click.command("bootstrap-admin")
@with_appcontext
def bootstrap_admin_command():
    """Create the ADMIN_EMAIL user as an admin if no such user exists."""
    from app import db
    from app.models import User

    email = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
    if not email:
        click.echo("ADMIN_EMAIL not set; skipping admin bootstrap.")
        return
    if User.query.filter_by(email=email).first():
        click.echo("Admin user already exists.")
        return
    db.session.add(User(email=email, name=os.getenv("ADMIN_NAME") or "Administrator", is_admin=True))
    db.session.commit()
    click.echo(f"Created admin user {email}.")


@click.command("create-invite")
@click.option("--note", default="", help="Who the invite is for (shown in the admin list).")
@click.option("--days", type=int, default=None, help="Days until the invite expires.")
@with_appcontext
def create_invite_command(note, days):
    """Create a single-use registration invite and print its link."""
    from app import db
    from app.models import Invite, User

    admin = User.query.filter_by(is_admin=True).order_by(User.id).first()
    if admin is None:
        raise click.ClickException("No admin user exists yet; run `flask bootstrap-admin` first.")
    invite, token = Invite.create(created_by=admin, note=note, days=days)
    db.session.commit()
    click.echo(f"{current_app.config['APP_URL']}/auth/register?invite={token}")


@click.command("send-digest")
@with_appcontext
def send_digest_command():
    """Manually trigger the daily wishlist digest email"""
    from app.email import send_daily_wishlist_digest

    click.echo("Sending daily wishlist digest emails...")
    send_daily_wishlist_digest()
    click.echo("Daily digest emails sent.")


def init_cli(app):
    """Register CLI commands with the Flask app"""
    for command in (init_db_command, bootstrap_admin_command, create_invite_command, send_digest_command):
        app.cli.add_command(command)
