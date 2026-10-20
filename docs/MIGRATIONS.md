# Database migrations

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/) via Flask-Migrate. Migrations live in
`migrations/versions/`. SQLite batch mode is on, so `ALTER TABLE` limitations are handled for you.

## Applying migrations

`flask init-db` brings any database up to date and is safe to run repeatedly. The container runs it on every start
(see `docker-entrypoint.sh`).

- **Empty database**: creates the schema from the migrations.
- **Pre-Alembic database (v3.5.2 or older)**: checks that the database has the v3.5.2 schema, stamps it at
  `0001_baseline`, then upgrades. Older databases are refused with a message: run the v3.5.2 image once first, since
  it still contains the legacy migration scripts.
- **Alembic-managed database**: `flask db upgrade`.

Back up the database file before upgrading. It is a single SQLite file in the instance directory.

## Making a schema change

```bash
# 1. Edit app/models.py
# 2. Generate a migration against a database that is at head
APP_ENV=development DATABASE_URL=sqlite:////tmp/dev.db flask --app run:app init-db
APP_ENV=development DATABASE_URL=sqlite:////tmp/dev.db flask --app run:app db migrate -m "describe the change"
# 3. Review the generated file in migrations/versions/ (autogenerate does not detect everything,
#    e.g. CHECK constraints or renames), then test it on a copy of a real database:
APP_ENV=development DATABASE_URL=sqlite:////tmp/prod-copy.db flask --app run:app init-db
```

CI fails if the migrations and the models disagree (`flask db check` and
`tests/test_security.py::test_migrations_build_the_model_schema`).

## History

| Revision | Change |
|---|---|
| `0001_baseline` | Schema of v3.5.2 (the last release that used hand-written migration scripts) |
| `0002_invites_logins` | `invites` table, `users.last_login_at` (single-use magic links), one-owner CHECK on `wishlist_items`, index names normalised |

Note: the `purchases` table and its `purchased_by_id` column keep their historical names; in code they are the
`Claim` model and `Claim.claimed_by_id`.
