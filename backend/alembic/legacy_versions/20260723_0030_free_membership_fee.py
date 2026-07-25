"""Allow zero-value official membership activations."""

from alembic import op
import sqlalchemy as sa


revision = "20260723_0030"
down_revision = "20260723_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_official_membership_payment_amount_positive",
        "official_membership_payments",
        type_="check",
    )
    op.create_check_constraint(
        "ck_official_membership_payment_amount_nonnegative",
        "official_membership_payments",
        "amount_wei >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_official_membership_payment_amount_nonnegative",
        "official_membership_payments",
        type_="check",
    )
    op.create_check_constraint(
        "ck_official_membership_payment_amount_positive",
        "official_membership_payments",
        "amount_wei > 0",
    )
