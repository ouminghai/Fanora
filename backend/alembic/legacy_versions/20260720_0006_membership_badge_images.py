"""Add Badge image URLs to membership levels."""

from alembic import op
import sqlalchemy as sa


revision = "20260720_0006"
down_revision = "20260720_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "membership_levels",
        sa.Column("badge_image_url", sa.String(length=2048), nullable=True),
    )
    badge_images = {
        "newborn": "/img/badges/new.png",
        "mild-neuro": "/img/badges/mild.png",
        "moderate-neuro": "/img/badges/moderate.png",
        "severe-neuro": "/img/badges/severe.png",
        "terminal-neuro": "/img/badges/terminal.png",
        "incurable": "/img/badges/incurable.png",
        "neuro-leader": "/img/badges/leader.png",
    }
    membership_levels = sa.table(
        "membership_levels",
        sa.column("code", sa.String()),
        sa.column("badge_image_url", sa.String()),
    )
    for code, badge_image_url in badge_images.items():
        op.execute(
            membership_levels.update()
            .where(membership_levels.c.code == code)
            .values(badge_image_url=badge_image_url)
        )
    op.execute(
        membership_levels.update()
        .where(membership_levels.c.badge_image_url.is_(None))
        .values(badge_image_url="/img/badges/new.png")
    )
    op.alter_column(
        "membership_levels",
        "badge_image_url",
        existing_type=sa.String(length=2048),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("membership_levels", "badge_image_url")
