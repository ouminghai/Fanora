"""NFT metadata, chain operations, issued assets, and custom badge applications."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, CheckConstraint, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import new_id, utc_now


class NftMetadataVersion(SQLModel, table=True):
    __tablename__ = "nft_metadata_versions"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("subject_type", "subject_id", "version", name="uq_nft_metadata_version"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    subject_type: str = Field(max_length=30, index=True)
    subject_id: str = Field(max_length=64, index=True)
    version: int = Field(ge=1)
    image_cid: str = Field(max_length=255)
    image_pin_id: str | None = Field(default=None, max_length=255)
    metadata_cid: str = Field(max_length=255, index=True)
    metadata_pin_id: str | None = Field(default=None, max_length=255)
    content_hash: str = Field(max_length=64)
    size_bytes: int = Field(ge=0)
    mime_type: str = Field(max_length=100)
    pin_status: str = Field(default="PINNED", max_length=20, index=True)
    metadata_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_by_user_id: str | None = Field(default=None, foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)


class ChainOperation(SQLModel, table=True):
    __tablename__ = "chain_operations"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_chain_operation_idempotency_key"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str | None = Field(default=None, foreign_key="users.id", index=True)
    operation_type: str = Field(max_length=40, index=True)
    idempotency_key: str = Field(max_length=160, index=True)
    operation_hash: str = Field(max_length=66, unique=True, index=True)
    chain_id: int = Field(index=True)
    contract_address: str = Field(max_length=42, index=True)
    token_id: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    metadata_cid: str | None = Field(default=None, max_length=255)
    status: str = Field(default="PENDING", max_length=30, index=True)
    transaction_hash: str | None = Field(default=None, max_length=66, index=True)
    block_number: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    confirmations: int = Field(default=0, ge=0)
    request_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    failure_reason: str | None = Field(default=None, max_length=500)
    retry_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utc_now)
    submitted_at: datetime | None = Field(default=None)
    confirmed_at: datetime | None = Field(default=None)
    updated_at: datetime = Field(default_factory=utc_now)


class MembershipIdentityNft(SQLModel, table=True):
    __tablename__ = "membership_identity_nfts"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_membership_identity_user"),
        UniqueConstraint("chain_id", "contract_address", "token_id", name="uq_membership_identity_token"),
    )

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    wallet_address: str = Field(max_length=42, index=True)
    chain_id: int = Field(index=True)
    contract_address: str = Field(max_length=42, index=True)
    token_id: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    level_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    level_code: str = Field(max_length=50)
    metadata_version: int = Field(default=1, ge=1)
    metadata_cid: str = Field(max_length=255)
    is_member_card: bool = Field(default=False, index=True)
    card_level_code: str | None = Field(default=None, max_length=50)
    card_content_hash: str | None = Field(default=None, max_length=64)
    card_fee_fan_tokens: int = Field(default=0, ge=0)
    card_created_at: datetime | None = Field(default=None)
    card_updated_at: datetime | None = Field(default=None)
    status: str = Field(default="PENDING", max_length=30, index=True)
    chain_operation_id: str | None = Field(default=None, foreign_key="chain_operations.id")
    minted_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CollectibleTokenType(SQLModel, table=True):
    __tablename__ = "collectible_token_types"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("chain_id", "contract_address", "token_id", name="uq_collectible_token_type"),
        CheckConstraint("max_supply > 0", name="ck_collectible_max_supply_positive"),
        CheckConstraint("per_wallet_limit > 0", name="ck_collectible_wallet_limit_positive"),
    )

    id: str = Field(default_factory=new_id, primary_key=True)
    token_id: int = Field(sa_column=Column(BigInteger, nullable=False, index=True))
    category: str = Field(max_length=30, index=True)
    name: str = Field(max_length=100)
    description: str = Field(max_length=1000)
    chain_id: int = Field(index=True)
    contract_address: str = Field(max_length=42, index=True)
    metadata_cid: str = Field(max_length=255)
    max_supply: int = Field(sa_column=Column(BigInteger, nullable=False))
    minted_supply: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))
    per_wallet_limit: int = Field(sa_column=Column(BigInteger, nullable=False))
    mint_start: datetime
    mint_end: datetime
    transferable: bool = Field(default=False)
    metadata_frozen: bool = Field(default=False)
    active: bool = Field(default=True, index=True)
    source_type: str = Field(max_length=30)
    source_id: str = Field(max_length=64, index=True)
    status: str = Field(default="PENDING", max_length=30, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CollectibleOwnership(SQLModel, table=True):
    __tablename__ = "collectible_ownerships"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("token_type_id", "user_id", name="uq_collectible_ownership"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    token_type_id: str = Field(foreign_key="collectible_token_types.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    wallet_address: str = Field(max_length=42, index=True)
    amount: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))
    claim_key: str = Field(max_length=66, unique=True, index=True)
    status: str = Field(default="PENDING", max_length=30, index=True)
    chain_operation_id: str | None = Field(default=None, foreign_key="chain_operations.id")
    minted_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class TaskNftReward(SQLModel, table=True):
    __tablename__ = "task_nft_rewards"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("task_id", "user_id", "reward_version", name="uq_task_nft_reward_user_version"),
        UniqueConstraint("participation_id", "reward_version", name="uq_task_nft_reward_participation_version"),
    )

    id: str = Field(default_factory=new_id, primary_key=True)
    task_id: str = Field(foreign_key="fan_tasks.id", index=True)
    participation_id: str = Field(foreign_key="task_participations.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    reward_version: int = Field(default=1, ge=1)
    token_type_id: str | None = Field(default=None, foreign_key="collectible_token_types.id", index=True)
    ownership_id: str | None = Field(default=None, foreign_key="collectible_ownerships.id", index=True)
    status: str = Field(default="PENDING", max_length=30, index=True)
    failure_reason: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class NftCreationReaction(SQLModel, table=True):
    __tablename__ = "nft_creation_reactions"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("application_id", "user_id", name="uq_nft_creation_reaction_user"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    application_id: str = Field(foreign_key="nft_applications.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    liked: bool = Field(default=False, index=True)
    favorited: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class NftVisualTemplate(SQLModel, table=True):
    __tablename__ = "nft_visual_templates"  # pyright: ignore[reportAssignmentType]

    id: str = Field(default_factory=new_id, primary_key=True)
    owner_user_id: str | None = Field(default=None, foreign_key="users.id", index=True)
    source_post_id: str | None = Field(default=None, foreign_key="community_posts.id", index=True)
    name: str = Field(max_length=80, index=True)
    category: str = Field(max_length=40, index=True)
    description: str = Field(max_length=500)
    prompt: str = Field(max_length=2000)
    preview_image_url: str = Field(max_length=2048)
    reference_image_urls: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    palette: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    elements: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    forbidden: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    is_system: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now)


class NftForgeSession(SQLModel, table=True):
    __tablename__ = "nft_forge_sessions"  # pyright: ignore[reportAssignmentType]

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    conversation_id: str | None = Field(default=None, max_length=80, index=True)
    template_id: str | None = Field(default=None, max_length=64)
    visual_style: str = Field(default="cinematic", max_length=80)
    title: str = Field(max_length=100)
    story_summary: str = Field(max_length=1500)
    image_prompt: str = Field(max_length=2500)
    reference_image_urls: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    suggested_attributes: list[dict[str, str]] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    supply: int = Field(default=50, sa_column=Column(BigInteger, nullable=False))
    price_fan_tokens: int = Field(default=20, sa_column=Column(BigInteger, nullable=False))
    forge_mode: str = Field(default="FOCUSED", max_length=20, index=True)
    status: str = Field(default="ANALYZED", max_length=30, index=True)
    rules_version: str = Field(default="forge-v1", max_length=30)
    generated_versions: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    selected_version_id: str | None = Field(default=None, max_length=64)
    published_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now)


class NftAiAnalysis(SQLModel, table=True):
    __tablename__ = "nft_ai_analyses"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("forge_session_id", name="uq_nft_ai_analysis_session"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    forge_session_id: str = Field(foreign_key="nft_forge_sessions.id", index=True)
    rare_score: int = Field(ge=0, le=100)
    rarity_level: str = Field(max_length=20)
    originality: int = Field(ge=0, le=100)
    visual_quality: int = Field(ge=0, le=100)
    fan_emotion: int = Field(ge=0, le=100)
    scarcity: int = Field(ge=0, le=100)
    community_potential: int = Field(ge=0, le=100)
    recommend_supply_min: int = Field(ge=1)
    recommend_supply_max: int = Field(ge=1)
    recommend_supply_default: int = Field(ge=1)
    recommend_price_min: int = Field(ge=1)
    recommend_price_max: int = Field(ge=1)
    recommend_price_default: int = Field(ge=1)
    suggestions: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    model_name: str = Field(default="rules", max_length=100)
    prompt_version: str = Field(default="nft-forge-analysis-v1", max_length=50)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class NftForgeAttempt(SQLModel, table=True):
    __tablename__ = "nft_forge_attempts"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_nft_forge_attempt_idempotency"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    forge_session_id: str = Field(foreign_key="nft_forge_sessions.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    idempotency_key: str = Field(max_length=160, index=True)
    forge_mode: str = Field(max_length=20, index=True)
    payment_source: str = Field(default="FAN", max_length=20)
    fan_cost: int = Field(default=0, ge=0)
    success_rate: float = Field(ge=0, le=100)
    perfect_rate: float = Field(ge=0, le=100)
    random_roll: float = Field(ge=0, le=100)
    perfect_roll: float | None = Field(default=None, ge=0, le=100)
    server_seed_hash: str = Field(max_length=64)
    server_seed_reveal: str | None = Field(default=None, max_length=128)
    result: str = Field(default="PENDING", max_length=20, index=True)
    refund_status: str = Field(default="NOT_REQUIRED", max_length=20)
    error_message: str | None = Field(default=None, max_length=500)
    rules_version: str = Field(default="forge-v1", max_length=30)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    completed_at: datetime | None = Field(default=None)


class UserFragmentBalance(SQLModel, table=True):
    __tablename__ = "user_fragment_balances"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_fragment_balance_user"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    balance: int = Field(default=0, ge=0)
    stable_credits: int = Field(default=0, ge=0)
    focused_credits: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class FragmentLedger(SQLModel, table=True):
    __tablename__ = "fragment_ledgers"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_fragment_ledger_idempotency"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    forge_attempt_id: str | None = Field(default=None, foreign_key="nft_forge_attempts.id", index=True)
    delta: int
    balance_after: int = Field(ge=0)
    source_type: str = Field(max_length=30, index=True)
    idempotency_key: str = Field(max_length=160, index=True)
    description: str = Field(max_length=300)
    created_at: datetime = Field(default_factory=utc_now, index=True)


class NftGenerationJob(SQLModel, table=True):
    __tablename__ = "nft_generation_jobs"  # pyright: ignore[reportAssignmentType]

    id: str = Field(default_factory=new_id, primary_key=True)
    forge_attempt_id: str = Field(foreign_key="nft_forge_attempts.id", index=True)
    forge_session_id: str = Field(foreign_key="nft_forge_sessions.id", index=True)
    status: str = Field(default="PENDING", max_length=20, index=True)
    model_name: str = Field(max_length=100)
    image_prompt: str = Field(max_length=2500)
    output_versions: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    error_message: str | None = Field(default=None, max_length=500)
    duration_ms: int | None = Field(default=None, ge=0)
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = Field(default=None)


class NftApplication(SQLModel, table=True):
    __tablename__ = "nft_applications"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("forge_session_id", name="uq_nft_application_forge_session"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    forge_session_id: str | None = Field(default=None, foreign_key="nft_forge_sessions.id", index=True)
    name: str = Field(max_length=100)
    description: str = Field(max_length=1000)
    story_image_urls: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    theme: str = Field(max_length=120)
    public_attributes: list[dict[str, str]] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    copyright_declaration: str = Field(max_length=500)
    price_fan_tokens: int = Field(default=1, sa_column=Column(BigInteger, nullable=False))
    max_supply: int = Field(default=1, sa_column=Column(BigInteger, nullable=False))
    publish_fee_fan_tokens: int = Field(default=100, sa_column=Column(BigInteger, nullable=False))
    image_data: str | None = Field(default=None, max_length=2048)
    image_mime_type: str = Field(max_length=100)
    image_size_bytes: int = Field(ge=0)
    image_width: int = Field(ge=0)
    image_height: int = Field(ge=0)
    status: str = Field(default="DRAFT", max_length=30, index=True)
    rejection_reason: str | None = Field(default=None, max_length=500)
    internal_review_note: str | None = Field(default=None, max_length=1000)
    metadata_version_id: str | None = Field(default=None, foreign_key="nft_metadata_versions.id")
    collectible_token_type_id: str | None = Field(default=None, foreign_key="collectible_token_types.id")
    reviewed_by_user_id: str | None = Field(default=None, foreign_key="users.id")
    submitted_at: datetime | None = Field(default=None)
    reviewed_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
