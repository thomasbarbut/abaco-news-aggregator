"""Initial migration – create all tables.

Revision ID: 001
Revises:
Create Date: 2026-05-15 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ENUM types ────────────────────────────────────────────────────────────
    userrole = postgresql.ENUM("admin", "user", name="userrole", create_type=False)
    userrole.create(op.get_bind(), checkfirst=True)

    sourcetype = postgresql.ENUM("rss", "playwright", name="sourcetype", create_type=False)
    sourcetype.create(op.get_bind(), checkfirst=True)

    source_syncstatus = postgresql.ENUM(
        "ok", "error", "pending", name="source_syncstatus", create_type=False
    )
    source_syncstatus.create(op.get_bind(), checkfirst=True)

    synclogstatus = postgresql.ENUM(
        "success", "error", "partial", name="synclogstatus", create_type=False
    )
    synclogstatus.create(op.get_bind(), checkfirst=True)

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("microsoft_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column(
            "role",
            sa.Enum("admin", "user", name="userrole"),
            nullable=False,
            server_default="user",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_microsoft_id", "users", ["microsoft_id"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── news_sources ──────────────────────────────────────────────────────────
    op.create_table(
        "news_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("rss_url", sa.String(2048), nullable=True),
        sa.Column(
            "source_type",
            sa.Enum("rss", "playwright", name="sourcetype"),
            nullable=False,
            server_default="rss",
        ),
        sa.Column(
            "enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "sync_status",
            sa.Enum("ok", "error", "pending", name="source_syncstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_news_sources_url", "news_sources", ["url"], unique=True)

    # ── articles ──────────────────────────────────────────────────────────────
    op.create_table(
        "articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("news_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("slug", sa.String(512), nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("original_url", sa.String(2048), nullable=False),
        sa.Column("image_url", sa.String(2048), nullable=True),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column(
            "tags",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "language",
            sa.String(10),
            nullable=False,
            server_default="ro",
        ),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # Standard B-tree indexes
    op.create_index("ix_articles_slug", "articles", ["slug"], unique=True)
    op.create_index("ix_articles_original_url", "articles", ["original_url"], unique=True)
    op.create_index("ix_articles_checksum", "articles", ["checksum"], unique=True)
    op.create_index("ix_articles_published_at", "articles", ["published_at"])
    op.create_index("ix_articles_source_id", "articles", ["source_id"])
    op.create_index(
        "ix_articles_source_published",
        "articles",
        ["source_id", "published_at"],
    )
    # GIN full-text search index
    op.execute(
        """
        CREATE INDEX ix_articles_fts ON articles
        USING gin (
            to_tsvector('simple',
                title || ' ' ||
                coalesce(summary, '') || ' ' ||
                coalesce(content, '')
            )
        )
        """
    )

    # ── article_reads ─────────────────────────────────────────────────────────
    op.create_table(
        "article_reads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "read_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("user_id", "article_id", name="uq_article_reads_user_article"),
    )
    op.create_index("ix_article_reads_user_id", "article_reads", ["user_id"])
    op.create_index("ix_article_reads_article_id", "article_reads", ["article_id"])

    # ── sync_logs ─────────────────────────────────────────────────────────────
    op.create_table(
        "sync_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("news_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("success", "error", "partial", name="synclogstatus"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "articles_added",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
    )
    op.create_index("ix_sync_logs_source_id", "sync_logs", ["source_id"])


def downgrade() -> None:
    # Drop tables in reverse order (FK dependencies)
    op.drop_table("sync_logs")
    op.drop_table("article_reads")
    op.drop_table("articles")
    op.drop_table("news_sources")
    op.drop_table("users")

    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS synclogstatus")
    op.execute("DROP TYPE IF EXISTS source_syncstatus")
    op.execute("DROP TYPE IF EXISTS sourcetype")
    op.execute("DROP TYPE IF EXISTS userrole")
