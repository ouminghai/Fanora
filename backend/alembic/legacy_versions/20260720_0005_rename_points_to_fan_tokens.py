"""Rename persisted point fields to Fan Token terminology."""

from alembic import op
import sqlalchemy as sa


revision = "20260720_0005"
down_revision = "20260720_0004"
branch_labels = None
depends_on = None


def _create_fan_token_level_trigger() -> None:
    op.execute(
        """
        CREATE FUNCTION fanora_sync_membership_level() RETURNS trigger AS $$
        DECLARE
            computed_level varchar(30);
        BEGIN
            IF NEW.level = '神经领袖' THEN
                RETURN NEW;
            END IF;

            SELECT membership_levels.name
            INTO computed_level
            FROM membership_levels
            WHERE membership_levels.is_active = true
              AND membership_levels.is_management = false
              AND NEW.fan_token_balance >= membership_levels.min_token_balance
              AND (
                    membership_levels.max_token_balance IS NULL
                    OR NEW.fan_token_balance <= membership_levels.max_token_balance
                  )
            ORDER BY membership_levels.rank DESC
            LIMIT 1;

            NEW.level := COALESCE(computed_level, '新生儿');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_user_profiles_sync_membership_level
        BEFORE INSERT OR UPDATE OF fan_token_balance ON user_profiles
        FOR EACH ROW
        EXECUTE FUNCTION fanora_sync_membership_level();
        """
    )


def _create_legacy_point_level_trigger() -> None:
    op.execute(
        """
        CREATE FUNCTION fanora_sync_membership_level() RETURNS trigger AS $$
        DECLARE
            computed_level varchar(30);
        BEGIN
            IF NEW.level = '神经领袖' THEN
                RETURN NEW;
            END IF;

            SELECT membership_levels.name
            INTO computed_level
            FROM membership_levels
            WHERE membership_levels.is_active = true
              AND membership_levels.is_management = false
              AND NEW.points >= membership_levels.min_points
              AND (membership_levels.max_points IS NULL OR NEW.points <= membership_levels.max_points)
            ORDER BY membership_levels.rank DESC
            LIMIT 1;

            NEW.level := COALESCE(computed_level, '新生儿');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_user_profiles_sync_membership_level
        BEFORE INSERT OR UPDATE OF points ON user_profiles
        FOR EACH ROW
        EXECUTE FUNCTION fanora_sync_membership_level();
        """
    )


def upgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_user_profiles_sync_membership_level ON user_profiles")
    op.execute("DROP FUNCTION IF EXISTS fanora_sync_membership_level()")

    op.alter_column(
        "user_profiles",
        "points",
        new_column_name="fan_token_balance",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "membership_levels",
        "min_points",
        new_column_name="min_token_balance",
        existing_type=sa.Integer(),
        existing_nullable=True,
    )
    op.alter_column(
        "membership_levels",
        "max_points",
        new_column_name="max_token_balance",
        existing_type=sa.Integer(),
        existing_nullable=True,
    )
    op.rename_table("point_rules", "fan_token_rules")
    op.alter_column(
        "fan_token_rules",
        "points_delta",
        new_column_name="token_delta",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )

    op.execute(
        "ALTER TABLE user_profiles RENAME CONSTRAINT ck_user_profiles_points_nonnegative "
        "TO ck_user_profiles_fan_token_balance_nonnegative"
    )
    op.execute(
        "ALTER TABLE membership_levels RENAME CONSTRAINT ck_membership_level_point_range "
        "TO ck_membership_level_token_range"
    )
    op.execute(
        "ALTER TABLE membership_levels RENAME CONSTRAINT ck_membership_level_max_points "
        "TO ck_membership_level_max_token_balance"
    )
    op.execute("ALTER INDEX ix_membership_levels_min_points RENAME TO ix_membership_levels_min_token_balance")
    op.execute("ALTER TABLE fan_token_rules RENAME CONSTRAINT point_rules_pkey TO fan_token_rules_pkey")
    op.execute(
        "ALTER TABLE fan_token_rules RENAME CONSTRAINT ck_point_rule_nonzero_delta "
        "TO ck_fan_token_rule_nonzero_delta"
    )
    op.execute(
        "ALTER TABLE fan_token_rules RENAME CONSTRAINT ck_point_rule_daily_limit "
        "TO ck_fan_token_rule_daily_limit"
    )
    op.execute(
        "ALTER TABLE fan_token_rules RENAME CONSTRAINT ck_point_rule_monthly_limit "
        "TO ck_fan_token_rule_monthly_limit"
    )
    op.execute(
        "ALTER TABLE fan_token_rules RENAME CONSTRAINT uq_point_rule_sort_order "
        "TO uq_fan_token_rule_sort_order"
    )
    op.execute("ALTER INDEX ix_point_rules_category RENAME TO ix_fan_token_rules_category")
    op.execute("ALTER INDEX ix_point_rules_is_active RENAME TO ix_fan_token_rules_is_active")
    op.execute("ALTER INDEX ix_point_rules_name RENAME TO ix_fan_token_rules_name")
    op.execute(
        "ALTER INDEX ix_point_rules_requires_review RENAME TO ix_fan_token_rules_requires_review"
    )
    op.execute("ALTER INDEX ix_point_rules_sort_order RENAME TO ix_fan_token_rules_sort_order")

    _create_fan_token_level_trigger()


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_user_profiles_sync_membership_level ON user_profiles")
    op.execute("DROP FUNCTION IF EXISTS fanora_sync_membership_level()")

    op.execute("ALTER INDEX ix_fan_token_rules_sort_order RENAME TO ix_point_rules_sort_order")
    op.execute(
        "ALTER INDEX ix_fan_token_rules_requires_review RENAME TO ix_point_rules_requires_review"
    )
    op.execute("ALTER INDEX ix_fan_token_rules_name RENAME TO ix_point_rules_name")
    op.execute("ALTER INDEX ix_fan_token_rules_is_active RENAME TO ix_point_rules_is_active")
    op.execute("ALTER INDEX ix_fan_token_rules_category RENAME TO ix_point_rules_category")
    op.execute(
        "ALTER TABLE fan_token_rules RENAME CONSTRAINT uq_fan_token_rule_sort_order "
        "TO uq_point_rule_sort_order"
    )
    op.execute(
        "ALTER TABLE fan_token_rules RENAME CONSTRAINT ck_fan_token_rule_monthly_limit "
        "TO ck_point_rule_monthly_limit"
    )
    op.execute(
        "ALTER TABLE fan_token_rules RENAME CONSTRAINT ck_fan_token_rule_daily_limit "
        "TO ck_point_rule_daily_limit"
    )
    op.execute(
        "ALTER TABLE fan_token_rules RENAME CONSTRAINT ck_fan_token_rule_nonzero_delta "
        "TO ck_point_rule_nonzero_delta"
    )
    op.execute("ALTER TABLE fan_token_rules RENAME CONSTRAINT fan_token_rules_pkey TO point_rules_pkey")
    op.execute("ALTER INDEX ix_membership_levels_min_token_balance RENAME TO ix_membership_levels_min_points")
    op.execute(
        "ALTER TABLE membership_levels RENAME CONSTRAINT ck_membership_level_max_token_balance "
        "TO ck_membership_level_max_points"
    )
    op.execute(
        "ALTER TABLE membership_levels RENAME CONSTRAINT ck_membership_level_token_range "
        "TO ck_membership_level_point_range"
    )
    op.execute(
        "ALTER TABLE user_profiles RENAME CONSTRAINT ck_user_profiles_fan_token_balance_nonnegative "
        "TO ck_user_profiles_points_nonnegative"
    )

    op.alter_column(
        "fan_token_rules",
        "token_delta",
        new_column_name="points_delta",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
    op.rename_table("fan_token_rules", "point_rules")
    op.alter_column(
        "membership_levels",
        "max_token_balance",
        new_column_name="max_points",
        existing_type=sa.Integer(),
        existing_nullable=True,
    )
    op.alter_column(
        "membership_levels",
        "min_token_balance",
        new_column_name="min_points",
        existing_type=sa.Integer(),
        existing_nullable=True,
    )
    op.alter_column(
        "user_profiles",
        "fan_token_balance",
        new_column_name="points",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )

    _create_legacy_point_level_trigger()
