"""Add configurable membership levels and point rules."""

from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa


revision = "20260720_0003"
down_revision = "20260720_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "membership_levels",
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=30), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("min_points", sa.Integer(), nullable=True),
        sa.Column("max_points", sa.Integer(), nullable=True),
        sa.Column("is_management", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("rank > 0", name="ck_membership_level_rank_positive"),
        sa.CheckConstraint(
            "(is_management AND min_points IS NULL AND max_points IS NULL) OR "
            "(NOT is_management AND min_points IS NOT NULL)",
            name="ck_membership_level_point_range",
        ),
        sa.CheckConstraint(
            "max_points IS NULL OR min_points IS NULL OR max_points >= min_points",
            name="ck_membership_level_max_points",
        ),
        sa.PrimaryKeyConstraint("code"),
        sa.UniqueConstraint("name", name="uq_membership_level_name"),
        sa.UniqueConstraint("rank", name="uq_membership_level_rank"),
    )
    op.create_index("ix_membership_levels_is_active", "membership_levels", ["is_active"])
    op.create_index("ix_membership_levels_is_management", "membership_levels", ["is_management"])
    op.create_index("ix_membership_levels_min_points", "membership_levels", ["min_points"])
    op.create_index("ix_membership_levels_name", "membership_levels", ["name"])
    op.create_index("ix_membership_levels_rank", "membership_levels", ["rank"])

    op.create_table(
        "point_rules",
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("points_delta", sa.Integer(), nullable=False),
        sa.Column("verification_method", sa.String(length=30), nullable=False),
        sa.Column("repeat_policy", sa.String(length=30), nullable=False),
        sa.Column("daily_limit", sa.Integer(), nullable=True),
        sa.Column("monthly_limit", sa.Integer(), nullable=True),
        sa.Column("requires_review", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("points_delta <> 0", name="ck_point_rule_nonzero_delta"),
        sa.CheckConstraint("daily_limit IS NULL OR daily_limit > 0", name="ck_point_rule_daily_limit"),
        sa.CheckConstraint("monthly_limit IS NULL OR monthly_limit > 0", name="ck_point_rule_monthly_limit"),
        sa.PrimaryKeyConstraint("code"),
        sa.UniqueConstraint("sort_order", name="uq_point_rule_sort_order"),
    )
    op.create_index("ix_point_rules_category", "point_rules", ["category"])
    op.create_index("ix_point_rules_is_active", "point_rules", ["is_active"])
    op.create_index("ix_point_rules_name", "point_rules", ["name"])
    op.create_index("ix_point_rules_requires_review", "point_rules", ["requires_review"])
    op.create_index("ix_point_rules_sort_order", "point_rules", ["sort_order"])

    now = datetime.now(UTC)
    membership_levels = sa.table(
        "membership_levels",
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("rank", sa.Integer()),
        sa.column("min_points", sa.Integer()),
        sa.column("max_points", sa.Integer()),
        sa.column("is_management", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        membership_levels,
        [
            {"code": "newborn", "name": "新生儿", "description": "刚注册的新会员", "rank": 1, "min_points": 0, "max_points": 99, "is_management": False, "is_active": True, "created_at": now, "updated_at": now},
            {"code": "mild-neuro", "name": "轻度神经", "description": "初级活跃会员", "rank": 2, "min_points": 100, "max_points": 499, "is_management": False, "is_active": True, "created_at": now, "updated_at": now},
            {"code": "moderate-neuro", "name": "中度神经", "description": "开始活跃发帖、签到", "rank": 3, "min_points": 500, "max_points": 1499, "is_management": False, "is_active": True, "created_at": now, "updated_at": now},
            {"code": "severe-neuro", "name": "重度神经", "description": "持续活跃会员", "rank": 4, "min_points": 1500, "max_points": 3999, "is_management": False, "is_active": True, "created_at": now, "updated_at": now},
            {"code": "terminal-neuro", "name": "病入膏肓", "description": "高等级会员", "rank": 5, "min_points": 4000, "max_points": 9999, "is_management": False, "is_active": True, "created_at": now, "updated_at": now},
            {"code": "incurable", "name": "无药可救", "description": "资深会员", "rank": 6, "min_points": 10000, "max_points": None, "is_management": False, "is_active": True, "created_at": now, "updated_at": now},
            {"code": "neuro-leader", "name": "神经领袖", "description": "管理员或版主管理身份，不通过积分自动获得", "rank": 100, "min_points": None, "max_points": None, "is_management": True, "is_active": True, "created_at": now, "updated_at": now},
        ],
    )

    point_rules = sa.table(
        "point_rules",
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("category", sa.String()),
        sa.column("points_delta", sa.Integer()),
        sa.column("verification_method", sa.String()),
        sa.column("repeat_policy", sa.String()),
        sa.column("daily_limit", sa.Integer()),
        sa.column("monthly_limit", sa.Integer()),
        sa.column("requires_review", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
        sa.column("sort_order", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    rule_defaults = {"is_active": True, "created_at": now, "updated_at": now}
    op.bulk_insert(
        point_rules,
        [
            {**rule_defaults, "code": "registration-complete", "name": "完成注册", "description": "首次完成 Fanora 注册和钱包绑定", "category": "onboarding", "points_delta": 50, "verification_method": "system", "repeat_policy": "once", "daily_limit": None, "monthly_limit": None, "requires_review": False, "sort_order": 10},
            {**rule_defaults, "code": "profile-complete", "name": "完善个人资料", "description": "首次完善昵称、用户名、头像或简介等主要资料", "category": "onboarding", "points_delta": 30, "verification_method": "system", "repeat_policy": "once", "daily_limit": None, "monthly_limit": None, "requires_review": False, "sort_order": 20},
            {**rule_defaults, "code": "daily-check-in", "name": "每日签到", "description": "每日完成一次有效签到", "category": "activity", "points_delta": 20, "verification_method": "system", "repeat_policy": "daily", "daily_limit": 1, "monthly_limit": 31, "requires_review": False, "sort_order": 30},
            {**rule_defaults, "code": "seven-day-streak", "name": "连续签到 7 天", "description": "连续七天完成签到后获得额外奖励", "category": "activity", "points_delta": 100, "verification_method": "system", "repeat_policy": "weekly", "daily_limit": 1, "monthly_limit": 5, "requires_review": False, "sort_order": 40},
            {**rule_defaults, "code": "join-community", "name": "加入社区", "description": "首次加入一个创作者社区", "category": "community", "points_delta": 50, "verification_method": "system", "repeat_policy": "once-per-community", "daily_limit": 5, "monthly_limit": 20, "requires_review": False, "sort_order": 50},
            {**rule_defaults, "code": "valid-interaction", "name": "有效内容互动", "description": "完成被系统确认的评论、回复或社区互动", "category": "content", "points_delta": 10, "verification_method": "system", "repeat_policy": "repeatable", "daily_limit": 5, "monthly_limit": 100, "requires_review": False, "sort_order": 60},
            {**rule_defaults, "code": "quality-post", "name": "优质内容发布", "description": "发布通过社区审核的原创优质内容", "category": "content", "points_delta": 80, "verification_method": "moderator", "repeat_policy": "repeatable", "daily_limit": 2, "monthly_limit": 20, "requires_review": True, "sort_order": 70},
            {**rule_defaults, "code": "online-event", "name": "线上活动参与", "description": "完成一次线上活动的有效参与任务", "category": "event", "points_delta": 120, "verification_method": "task", "repeat_policy": "once-per-event", "daily_limit": 2, "monthly_limit": 10, "requires_review": False, "sort_order": 80},
            {**rule_defaults, "code": "offline-event-check-in", "name": "线下活动打卡", "description": "提交并通过演唱会或线下活动的打卡凭证", "category": "event", "points_delta": 500, "verification_method": "evidence", "repeat_policy": "once-per-event", "daily_limit": 1, "monthly_limit": 4, "requires_review": True, "sort_order": 90},
            {**rule_defaults, "code": "community-contribution", "name": "社区共创贡献", "description": "内容共创、志愿协助或活动组织等有效贡献", "category": "community", "points_delta": 180, "verification_method": "moderator", "repeat_policy": "repeatable", "daily_limit": 1, "monthly_limit": 8, "requires_review": True, "sort_order": 100},
            {**rule_defaults, "code": "valid-referral", "name": "有效邀请", "description": "邀请的新用户完成注册和钱包绑定后发放", "category": "referral", "points_delta": 100, "verification_method": "system", "repeat_policy": "repeatable", "daily_limit": 3, "monthly_limit": 10, "requires_review": False, "sort_order": 110},
            {**rule_defaults, "code": "onchain-fan-action", "name": "有效链上粉丝行为", "description": "完成系统认可且非刷量的粉丝链上交互", "category": "onchain", "points_delta": 30, "verification_method": "system", "repeat_policy": "daily", "daily_limit": 1, "monthly_limit": 20, "requires_review": False, "sort_order": 120},
            {**rule_defaults, "code": "content-removed", "name": "违规内容删除", "description": "内容因违反社区规则被审核删除", "category": "penalty", "points_delta": -100, "verification_method": "moderator", "repeat_policy": "manual", "daily_limit": None, "monthly_limit": None, "requires_review": True, "sort_order": 130},
            {**rule_defaults, "code": "spam-abuse", "name": "刷屏或骚扰", "description": "确认存在刷屏、骚扰或恶意灌水行为", "category": "penalty", "points_delta": -300, "verification_method": "moderator", "repeat_policy": "manual", "daily_limit": None, "monthly_limit": None, "requires_review": True, "sort_order": 140},
            {**rule_defaults, "code": "fraudulent-activity", "name": "作弊或伪造凭证", "description": "确认存在任务作弊、重复领奖或伪造活动凭证", "category": "penalty", "points_delta": -1000, "verification_method": "admin", "repeat_policy": "manual", "daily_limit": None, "monthly_limit": None, "requires_review": True, "sort_order": 150},
        ],
    )

    op.execute(
        """
        UPDATE user_profiles
        SET level = CASE
            WHEN level = '神经领袖' THEN '神经领袖'
            WHEN points >= 10000 THEN '无药可救'
            WHEN points >= 4000 THEN '病入膏肓'
            WHEN points >= 1500 THEN '重度神经'
            WHEN points >= 500 THEN '中度神经'
            WHEN points >= 100 THEN '轻度神经'
            ELSE '新生儿'
        END
        """
    )
    op.alter_column(
        "user_profiles",
        "level",
        existing_type=sa.String(length=30),
        existing_nullable=False,
        server_default="新生儿",
    )
    op.create_check_constraint("ck_user_profiles_points_nonnegative", "user_profiles", "points >= 0")
    op.create_foreign_key(
        "fk_user_profiles_level_membership_levels",
        "user_profiles",
        "membership_levels",
        ["level"],
        ["name"],
        onupdate="CASCADE",
    )
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


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_user_profiles_sync_membership_level ON user_profiles")
    op.execute("DROP FUNCTION IF EXISTS fanora_sync_membership_level()")
    op.drop_constraint("fk_user_profiles_level_membership_levels", "user_profiles", type_="foreignkey")
    op.drop_constraint("ck_user_profiles_points_nonnegative", "user_profiles", type_="check")
    op.execute("UPDATE user_profiles SET level = 'Emerging'")
    op.alter_column(
        "user_profiles",
        "level",
        existing_type=sa.String(length=30),
        existing_nullable=False,
        server_default=None,
    )
    op.drop_table("point_rules")
    op.drop_table("membership_levels")
