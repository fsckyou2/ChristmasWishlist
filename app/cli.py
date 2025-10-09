"""
Flask CLI commands for administrative tasks
"""

import click
from flask.cli import with_appcontext


@click.command("send-digest")
@with_appcontext
def send_digest_command():
    """Manually trigger the daily wishlist digest email"""
    from app.email import send_daily_wishlist_digest

    click.echo("Sending daily wishlist digest emails...")
    try:
        send_daily_wishlist_digest()
        click.echo("Daily digest emails sent successfully!")
    except Exception as e:
        click.echo(f"Error sending digest emails: {str(e)}", err=True)


@click.command("migrate-db")
@with_appcontext
def migrate_db_command():
    """Add new columns to existing database"""
    from app import db

    click.echo("Migrating database...")
    try:
        # Add acquired and wrapped columns if they don't exist
        with db.engine.connect() as conn:
            # Check if columns exist
            result = conn.execute(db.text("PRAGMA table_info(purchases)"))
            columns = [row[1] for row in result]

            if "acquired" not in columns:
                click.echo("Adding acquired column...")
                conn.execute(db.text("ALTER TABLE purchases ADD COLUMN acquired BOOLEAN DEFAULT 0"))
                conn.commit()

            if "wrapped" not in columns:
                click.echo("Adding wrapped column...")
                conn.execute(db.text("ALTER TABLE purchases ADD COLUMN wrapped BOOLEAN DEFAULT 0"))
                conn.commit()

            if "updated_at" not in columns:
                click.echo("Adding updated_at column...")
                conn.execute(db.text("ALTER TABLE purchases ADD COLUMN updated_at DATETIME"))
                conn.commit()

        click.echo("Database migration completed successfully!")
    except Exception as e:
        click.echo(f"Error migrating database: {str(e)}", err=True)


def init_cli(app):
    """Register CLI commands with the Flask app"""
    app.cli.add_command(send_digest_command)
    app.cli.add_command(migrate_db_command)
