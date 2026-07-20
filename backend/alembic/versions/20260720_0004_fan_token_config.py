"""Define points as the Fan Token unit."""

from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa


revision = "20260720_0004"
down_revision = "20260720_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fan_token_config",
        sa.Column("id", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("symbol", sa.String(length=12), nullable=False),
        sa.Column("icon_key", sa.String(length=50), nullable=False),
        sa.Column("decimals", sa.Integer(), nullable=False),
        sa.Column("is_onchain", sa.Boolean(), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=True),
        sa.Column("contract_address", sa.String(length=42), nullable=True),
        sa.Column("description", sa.String(length=300), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("decimals >= 0 AND decimals <= 18", name="ck_fan_token_config_decimals"),
        sa.PrimaryKeyConstraint("id"),
    )

    now = datetime.now(UTC)
    fan_token_config = sa.table(
        "fan_token_config",
        sa.column("id", sa.String()),
        sa.column("name", sa.String()),
        sa.column("symbol", sa.String()),
        sa.column("icon_key", sa.String()),
        sa.column("decimals", sa.Integer()),
        sa.column("is_onchain", sa.Boolean()),
        sa.column("chain_id", sa.Integer()),
        sa.column("contract_address", sa.String()),
        sa.column("description", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        fan_token_config,
        [
            {
                "id": "default",
                "name": "Fan Token",
                "symbol": "FAN",
                "icon_key": "ethereum-diamond",
                "decimals": 0,
                "is_onchain": False,
                "chain_id": None,
                "contract_address": None,
                "description": "Fanora 站内活动、任务、等级和奖励统一使用的粉丝积分单位；使用 ETH 菱形图标作为视觉符号，当前不代表真实 ETH 或已发行的链上代币。",
                "created_at": now,
                "updated_at": now,
            }
        ],
    )


def downgrade() -> None:
    op.drop_table("fan_token_config")
