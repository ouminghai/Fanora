"""Separate spendable FAN balance from lifetime membership progress."""

import sqlalchemy as sa

from alembic import op

revision = "20260722_0021"
down_revision = "20260721_0020"
branch_labels = None
depends_on = None


def _create_lifetime_level_trigger() -> None:
    op.execute(
        """
        CREATE FUNCTION fanora_sync_membership_level() RETURNS trigger AS $$
        DECLARE
            computed_level varchar(30);
            computed_rank integer;
            current_rank integer;
        BEGIN
            IF NEW.level = '神经领袖' THEN
                RETURN NEW;
            END IF;

            SELECT membership_levels.name, membership_levels.rank
            INTO computed_level, computed_rank
            FROM membership_levels
            WHERE membership_levels.is_active = true
              AND membership_levels.is_management = false
              AND NEW.fan_token_lifetime_earned >= membership_levels.min_token_balance
              AND (
                    membership_levels.max_token_balance IS NULL
                    OR NEW.fan_token_lifetime_earned <= membership_levels.max_token_balance
                  )
            ORDER BY membership_levels.rank DESC
            LIMIT 1;

            SELECT membership_levels.rank
            INTO current_rank
            FROM membership_levels
            WHERE membership_levels.name = NEW.level;

            IF computed_level IS NOT NULL
               AND (current_rank IS NULL OR computed_rank > current_rank) THEN
                NEW.level := computed_level;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_user_profiles_sync_membership_level
        BEFORE INSERT OR UPDATE OF fan_token_lifetime_earned ON user_profiles
        FOR EACH ROW
        EXECUTE FUNCTION fanora_sync_membership_level();
        """
    )


def _create_balance_level_trigger() -> None:
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


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column(
            "fan_token_lifetime_earned",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_user_profiles_fan_token_lifetime_earned_nonnegative",
        "user_profiles",
        "fan_token_lifetime_earned >= 0",
    )
    op.execute(
        "UPDATE user_profiles "
        "SET fan_token_lifetime_earned = fan_token_balance"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_user_profiles_sync_membership_level ON user_profiles"
    )
    op.execute("DROP FUNCTION IF EXISTS fanora_sync_membership_level()")
    _create_lifetime_level_trigger()


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_user_profiles_sync_membership_level ON user_profiles"
    )
    op.execute("DROP FUNCTION IF EXISTS fanora_sync_membership_level()")
    op.drop_constraint(
        "ck_user_profiles_fan_token_lifetime_earned_nonnegative",
        "user_profiles",
        type_="check",
    )
    op.drop_column("user_profiles", "fan_token_lifetime_earned")
    _create_balance_level_trigger()
