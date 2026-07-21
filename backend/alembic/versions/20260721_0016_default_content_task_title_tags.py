"""Use each content task title as its default publication tag."""

from alembic import op


revision = "20260721_0016"
down_revision = "20260721_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE fan_tasks SET validation_rule = validation_rule::jsonb - 'required_tag' "
        "WHERE id IN ('00000000-0000-0000-0000-000000000023', '00000000-0000-0000-0000-000000000024')"
    )


def downgrade() -> None:
    op.execute("UPDATE fan_tasks SET validation_rule = jsonb_set(validation_rule::jsonb, '{required_tag}', '\"#粉丝故事图文征集\"'::jsonb) WHERE id = '00000000-0000-0000-0000-000000000023'")
    op.execute("UPDATE fan_tasks SET validation_rule = jsonb_set(validation_rule::jsonb, '{required_tag}', '\"#周年祝福共创\"'::jsonb) WHERE id = '00000000-0000-0000-0000-000000000024'")
