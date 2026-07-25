"""Store community media attachments and require task publication tags."""

from alembic import op


revision = "20260721_0015"
down_revision = "20260721_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS image_urls JSON NOT NULL DEFAULT '[]'::json")
    op.execute("ALTER TABLE community_replies ADD COLUMN IF NOT EXISTS image_urls JSON NOT NULL DEFAULT '[]'::json")
    op.execute("ALTER TABLE task_participations ADD COLUMN IF NOT EXISTS submission JSON NOT NULL DEFAULT '{}'::json")
    op.execute("UPDATE fan_tasks SET validation_rule = jsonb_set(validation_rule::jsonb, '{required_tag}', '\"#Fanora故事\"'::jsonb) WHERE id = '00000000-0000-0000-0000-000000000023' AND NOT validation_rule::jsonb ? 'required_tag'")
    op.execute("UPDATE fan_tasks SET validation_rule = jsonb_set(validation_rule::jsonb, '{required_tag}', '\"#Fanora周年\"'::jsonb) WHERE id = '00000000-0000-0000-0000-000000000024' AND NOT validation_rule::jsonb ? 'required_tag'")


def downgrade() -> None:
    op.execute("ALTER TABLE task_participations DROP COLUMN IF EXISTS submission")
    op.execute("ALTER TABLE community_replies DROP COLUMN IF EXISTS image_urls")
    op.execute("ALTER TABLE community_posts DROP COLUMN IF EXISTS image_urls")
