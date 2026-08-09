"""Fan collection, identity synchronization, and custom badge applications."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from app.adapters.monad import ChainConfigurationError, monad_contract_adapter
from app.adapters.pinata import pinata_adapter
from app.agents.nft_creation import nft_creation_agent
from app.agents.nft_studio import nft_studio_agent
from app.agents.nft_upload_analysis import nft_upload_analysis_agent
from app.agents.nft_visual_templates import STYLE_PROMPTS, VISUAL_STYLE_OPTIONS
from app.core.config import settings
from app.core.database import get_database_session
from app.core.logging import logger
from app.core.security import get_current_identity, get_optional_identity, require_official_member
from app.models.base import utc_now
from app.models.nft import (
    ChainOperation,
    CollectibleOwnership,
    CollectibleTokenType,
    MembershipIdentityNft,
    NftApplication,
    NftCreationReaction,
    NftMetadataVersion,
)
from app.models.user import User, UserProfile
from app.schemas.nft import (
    ChainOperationResponse,
    CollectibleAvatarResponse,
    CollectibleResponse,
    FanNftCreateResponse,
    FanNftEngagementResponse,
    FanNftListingResponse,
    FanNftMintRecordResponse,
    FanNftPurchaseResponse,
    MembershipCardActionResponse,
    MembershipIdentityResponse,
    MyCollectionResponse,
    NftApplicationCreate,
    NftApplicationResponse,
    NftCreatorResponse,
    PublicCollectionResponse,
    PublicCollectionUserResponse,
)
from app.schemas.nft_agent import (
    NftAgentChatRequest,
    NftAgentChatResponse,
    NftDraftRequest,
    NftDraftResponse,
    NftUploadedImageAnalysisResponse,
    NftUploadedImageAnalyzeRequest,
    NftVisualStyle,
    NftVisualTemplate,
    NftVisualTemplateCreate,
    NftVisualTemplateUpdate,
)
from app.schemas.nft_forge import (
    NftForgeAnalyzeRequest,
    NftForgeSelectVersionRequest,
    NftForgeSessionResponse,
    NftForgeStartRequest,
    NftForgeStrategyRequest,
    NftFragmentBalanceResponse,
    NftFragmentRedeemRequest,
)
from app.services.identity import AuthenticatedIdentity
from app.services.nft import NftValidationError, nft_service
from app.services.nft_forge import ForgeValidationError, nft_forge_service
from app.services.nft_visual_templates import nft_visual_template_service

router = APIRouter(prefix="/nft")


def _application_response(application: NftApplication) -> NftApplicationResponse:
    return NftApplicationResponse(
        id=application.id,
        forge_session_id=application.forge_session_id,
        name=application.name,
        description=application.description,
        story_image_urls=application.story_image_urls,
        theme=application.theme,
        public_attributes=application.public_attributes,
        copyright_declaration=application.copyright_declaration,
        price_fan_tokens=application.price_fan_tokens,
        max_supply=application.max_supply,
        publish_fee_fan_tokens=application.publish_fee_fan_tokens,
        image_data_url=application.image_data,
        status=application.status,
        rejection_reason=application.rejection_reason,
        metadata_version_id=application.metadata_version_id,
        collectible_token_type_id=application.collectible_token_type_id,
        submitted_at=application.submitted_at,
        reviewed_at=application.reviewed_at,
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


@router.post("/forge/analyze", response_model=NftForgeSessionResponse, status_code=status.HTTP_201_CREATED)
async def analyze_nft_forge(
    payload: NftForgeAnalyzeRequest,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> NftForgeSessionResponse:
    try:
        return await nft_forge_service.analyze(session, identity.user_id, payload)
    except ForgeValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.patch("/forge/{session_id}/strategy", response_model=NftForgeSessionResponse)
async def update_nft_forge_strategy(
    session_id: str,
    payload: NftForgeStrategyRequest,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> NftForgeSessionResponse:
    try:
        return await nft_forge_service.update_strategy(session, identity.user_id, session_id, payload)
    except ForgeValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.post("/forge/{session_id}/start", response_model=NftForgeSessionResponse)
async def start_nft_forge(
    session_id: str,
    payload: NftForgeStartRequest,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> NftForgeSessionResponse:
    try:
        return await nft_forge_service.start(
            session,
            identity.user_id,
            session_id,
            payload.idempotency_key,
            use_fragment_credit=payload.use_fragment_credit,
        )
    except ForgeValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.post("/forge/{session_id}/retry", response_model=NftForgeSessionResponse)
async def retry_nft_forge(
    session_id: str,
    payload: NftForgeStartRequest,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> NftForgeSessionResponse:
    try:
        return await nft_forge_service.start(
            session,
            identity.user_id,
            session_id,
            payload.idempotency_key,
            use_fragment_credit=payload.use_fragment_credit,
        )
    except ForgeValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.get("/forge/{session_id}", response_model=NftForgeSessionResponse)
async def get_nft_forge(
    session_id: str,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> NftForgeSessionResponse:
    try:
        return await nft_forge_service.get(session, identity.user_id, session_id)
    except ForgeValidationError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/forge/{session_id}/select-version", response_model=NftForgeSessionResponse)
async def select_nft_forge_version(
    session_id: str,
    payload: NftForgeSelectVersionRequest,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> NftForgeSessionResponse:
    try:
        return await nft_forge_service.select_version(session, identity.user_id, session_id, payload.version_id)
    except ForgeValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.get("/fragments/me", response_model=NftFragmentBalanceResponse)
async def get_my_nft_fragments(
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> NftFragmentBalanceResponse:
    return await nft_forge_service.fragments(session, identity.user_id)


@router.post("/fragments/redeem", response_model=NftFragmentBalanceResponse)
async def redeem_nft_fragments(
    payload: NftFragmentRedeemRequest,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> NftFragmentBalanceResponse:
    try:
        return await nft_forge_service.redeem(session, identity.user_id, payload)
    except ForgeValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


async def _creator_response(session: AsyncSession, user_id: str) -> NftCreatorResponse:
    user = await session.get(User, user_id)
    profile = await session.get(UserProfile, user_id)
    if user is None or profile is None:
        return NftCreatorResponse(id=user_id, display_name="Fanora Creator", avatar_url=None, level="Fan")
    return NftCreatorResponse(
        id=user_id,
        display_name=user.display_name or profile.username or "Fanora Creator",
        avatar_url=profile.avatar_url,
        level=profile.level,
    )


async def _fan_nft_engagement(
    session: AsyncSession,
    application_id: str,
    user_id: str | None,
) -> tuple[int, int, bool, bool]:
    like_count = (
        await session.execute(
            select(func.count(col(NftCreationReaction.id))).where(
                NftCreationReaction.application_id == application_id,
                col(NftCreationReaction.liked).is_(True),
            )
        )
    ).scalar_one()
    favorite_count = (
        await session.execute(
            select(func.count(col(NftCreationReaction.id))).where(
                NftCreationReaction.application_id == application_id,
                col(NftCreationReaction.favorited).is_(True),
            )
        )
    ).scalar_one()
    reaction = None
    if user_id is not None:
        reaction = (
            await session.execute(
                select(NftCreationReaction).where(
                    NftCreationReaction.application_id == application_id,
                    NftCreationReaction.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
    return (
        int(like_count),
        int(favorite_count),
        bool(reaction and reaction.liked),
        bool(reaction and reaction.favorited),
    )


async def _fan_nft_mint_records(
    session: AsyncSession,
    token_type: CollectibleTokenType | None,
) -> list[FanNftMintRecordResponse]:
    if token_type is None:
        return []
    rows = (
        await session.execute(
            select(CollectibleOwnership, ChainOperation)
            .join(ChainOperation, col(ChainOperation.id) == CollectibleOwnership.chain_operation_id, isouter=True)
            .where(
                CollectibleOwnership.token_type_id == token_type.id,
                CollectibleOwnership.amount > 0,
            )
            .order_by(col(CollectibleOwnership.created_at).desc())
        )
    ).all()
    records: list[FanNftMintRecordResponse] = []
    for ownership, operation in rows:
        records.append(
            FanNftMintRecordResponse(
                id=ownership.id,
                wallet_address=ownership.wallet_address,
                amount=ownership.amount,
                status=ownership.status,
                transaction_hash=operation.transaction_hash if operation else None,
                block_number=operation.block_number if operation else None,
                minted_at=ownership.minted_at,
                created_at=ownership.created_at,
                buyer=await _creator_response(session, ownership.user_id),
            )
        )
    return records


async def _fan_nft_listing_response(
    session: AsyncSession,
    application: NftApplication,
    *,
    user_id: str | None = None,
    include_mint_records: bool = False,
) -> FanNftListingResponse:
    token_type = (
        await session.execute(
            select(CollectibleTokenType).where(CollectibleTokenType.id == application.collectible_token_type_id)
        )
    ).scalar_one_or_none()
    metadata = (
        await session.execute(
            select(NftMetadataVersion).where(NftMetadataVersion.id == application.metadata_version_id)
        )
    ).scalar_one_or_none()
    minted_supply = int(token_type.minted_supply) if token_type else 0
    token_id = int(token_type.token_id) if token_type else None
    contract_address = token_type.contract_address if token_type else None
    like_count, favorite_count, liked, favorited = await _fan_nft_engagement(session, application.id, user_id)
    return FanNftListingResponse(
        id=application.id,
        token_type_id=token_type.id if token_type else None,
        token_id=token_id,
        name=application.name,
        description=application.description,
        story_image_urls=application.story_image_urls,
        theme=application.theme,
        public_attributes=application.public_attributes,
        price_fan_tokens=application.price_fan_tokens,
        max_supply=application.max_supply,
        minted_supply=minted_supply,
        remaining_supply=max(application.max_supply - minted_supply, 0),
        image_url=pinata_adapter.gateway_url(metadata.image_cid) if metadata else application.image_data,
        metadata_uri=pinata_adapter.ipfs_uri(token_type.metadata_cid) if token_type else None,
        status=application.status,
        contract_address=contract_address,
        chain_id=token_type.chain_id if token_type else settings.monad_chain_id,
        explorer_url=(
            f"https://testnet.monadvision.com/nft/{contract_address}/{token_id}?tab=Overview"
            if contract_address and token_id
            else None
        ),
        like_count=like_count,
        favorite_count=favorite_count,
        liked=liked,
        favorited=favorited,
        mint_records=await _fan_nft_mint_records(session, token_type) if include_mint_records else [],
        creator=await _creator_response(session, application.user_id),
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


async def _identity_response_for_user(session: AsyncSession, user_id: str) -> tuple[MembershipIdentityResponse | None, str]:
    identity_nft = (
        await session.execute(select(MembershipIdentityNft).where(MembershipIdentityNft.user_id == user_id))
    ).scalar_one_or_none()
    if identity_nft is None:
        sync_status = "READY" if monad_contract_adapter.identity_configured and pinata_adapter.configured else "NOT_CONFIGURED"
        return None, sync_status
    user = await session.get(User, user_id)
    profile = await session.get(UserProfile, user_id)
    operation = (
        await session.get(ChainOperation, identity_nft.chain_operation_id)
        if identity_nft.chain_operation_id
        else None
    )
    mint_operation = (
        (
            await session.execute(
                select(ChainOperation)
                .where(
                    ChainOperation.user_id == user_id,
                    ChainOperation.operation_type == "IDENTITY_MINT",
                    ChainOperation.contract_address == identity_nft.contract_address,
                )
                .order_by(col(ChainOperation.created_at).desc())
            )
        )
        .scalars()
        .first()
    )
    metadata = (
        await session.execute(
            select(NftMetadataVersion).where(
                NftMetadataVersion.subject_type == "MEMBERSHIP_IDENTITY",
                NftMetadataVersion.subject_id == user_id,
                NftMetadataVersion.version == identity_nft.metadata_version,
            )
        )
    ).scalar_one_or_none()
    image_url = pinata_adapter.gateway_url(metadata.image_cid) if metadata else None
    card_needs_refresh = False
    if identity_nft.is_member_card and user is not None and profile is not None:
        level = await nft_service._identity_level_for_profile(session, profile)
        if level is not None:
            card_needs_refresh = nft_service.membership_card_needs_refresh(
                user=user,
                profile=profile,
                level=level,
                record=identity_nft,
            )
    return (
        MembershipIdentityResponse(
            token_id=identity_nft.token_id,
            level_id=identity_nft.level_id,
            level_code=identity_nft.level_code,
            metadata_version=identity_nft.metadata_version,
            metadata_uri=pinata_adapter.ipfs_uri(identity_nft.metadata_cid),
            metadata_gateway_url=pinata_adapter.gateway_url(identity_nft.metadata_cid),
            image_url=image_url,
            download_url=image_url if identity_nft.is_member_card else None,
            is_member_card=identity_nft.is_member_card,
            card_needs_refresh=card_needs_refresh,
            card_fee_fan_tokens=settings.membership_card_fee_fan_tokens,
            card_created_at=identity_nft.card_created_at,
            card_updated_at=identity_nft.card_updated_at,
            status=identity_nft.status,
            contract_address=identity_nft.contract_address,
            chain_id=identity_nft.chain_id,
            explorer_url=(
                f"https://testnet.monadvision.com/nft/{identity_nft.contract_address}/{identity_nft.token_id}?tab=Overview"
                if identity_nft.contract_address and identity_nft.token_id is not None
                else None
            ),
            minted_at=identity_nft.minted_at,
            mint_operation=ChainOperationResponse.model_validate(mint_operation) if mint_operation else None,
            operation=ChainOperationResponse.model_validate(operation) if operation else None,
        ),
        identity_nft.status,
    )


async def _collectibles_for_user(session: AsyncSession, user_id: str) -> list[CollectibleResponse]:
    rows = (
        await session.execute(
            select(CollectibleOwnership, CollectibleTokenType)
            .join(CollectibleTokenType, col(CollectibleTokenType.id) == CollectibleOwnership.token_type_id)
            .where(CollectibleOwnership.user_id == user_id)
            .order_by(col(CollectibleOwnership.created_at).desc())
        )
    ).all()
    collectibles: list[CollectibleResponse] = []
    for ownership, token_type in rows:
        operation = (
            await session.get(ChainOperation, ownership.chain_operation_id) if ownership.chain_operation_id else None
        )
        metadata = (
            (
                await session.execute(
                    select(NftMetadataVersion)
                    .where(NftMetadataVersion.metadata_cid == token_type.metadata_cid)
                    .order_by(col(NftMetadataVersion.created_at).desc())
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
        collectibles.append(
            CollectibleResponse(
                token_type_id=token_type.id,
                fan_nft_creation_id=token_type.source_id if token_type.source_type == "FAN_NFT" else None,
                token_id=token_type.token_id,
                category=token_type.category,
                name=token_type.name,
                description=token_type.description,
                metadata_uri=pinata_adapter.ipfs_uri(token_type.metadata_cid),
                image_url=pinata_adapter.gateway_url(metadata.image_cid) if metadata else None,
                amount=ownership.amount,
                max_supply=token_type.max_supply,
                minted_supply=token_type.minted_supply,
                transferable=token_type.transferable,
                status=ownership.status,
                contract_address=token_type.contract_address,
                chain_id=token_type.chain_id,
                explorer_url=f"https://testnet.monadvision.com/nft/{token_type.contract_address}/{token_type.token_id}?tab=Overview",
                operation=ChainOperationResponse.model_validate(operation) if operation else None,
            )
        )
    return collectibles


async def _applications_for_user(session: AsyncSession, user_id: str) -> list[NftApplication]:
    return list(
        (
            await session.execute(
                select(NftApplication)
                .where(NftApplication.user_id == user_id)
                .order_by(col(NftApplication.created_at).desc())
            )
        )
        .scalars()
        .all()
    )


@router.get("/me", response_model=MyCollectionResponse)
async def my_collection(
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> MyCollectionResponse:
    identity_response, sync_status = await _identity_response_for_user(session, identity.user_id)
    collectibles = await _collectibles_for_user(session, identity.user_id)
    applications = await _applications_for_user(session, identity.user_id)
    return MyCollectionResponse(
        chain_id=settings.monad_chain_id,
        identity_sync_status=sync_status,
        identity=identity_response,
        collectibles=collectibles,
        applications=[_application_response(item) for item in applications],
    )


@router.get("/me/creations", response_model=list[FanNftListingResponse])
async def my_fan_nft_creations(
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> list[FanNftListingResponse]:
    applications = [
        item
        for item in await _applications_for_user(session, identity.user_id)
        if item.status in {"MINTED", "MINTING", "FAILED"} and item.collectible_token_type_id
    ]
    return [await _fan_nft_listing_response(session, item, user_id=identity.user_id) for item in applications]


@router.get("/users/{user_id}", response_model=PublicCollectionResponse)
async def public_collection(
    user_id: str,
    session: AsyncSession = Depends(get_database_session),
) -> PublicCollectionResponse:
    user = await session.get(User, user_id)
    profile = await session.get(UserProfile, user_id)
    if user is None or profile is None or profile.profile_visibility != "public":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Public profile not found")
    identity_response, _ = await _identity_response_for_user(session, user_id)
    collectibles = await _collectibles_for_user(session, user_id)
    applications = [
        item
        for item in await _applications_for_user(session, user_id)
        if item.status in {"MINTED", "MINTING", "FAILED"} and item.collectible_token_type_id
    ]
    return PublicCollectionResponse(
        chain_id=settings.monad_chain_id,
        user=PublicCollectionUserResponse(
            id=user.id,
            display_name=user.display_name or profile.username or "Fanora Member",
            username=profile.username,
            avatar_url=profile.avatar_url,
            bio=profile.bio,
            level=profile.level if profile.is_official_member else "待入会",
            is_official_member=profile.is_official_member,
            official_member_since=profile.official_member_since,
            fan_token_balance=profile.fan_token_balance,
            fan_token_lifetime_earned=profile.fan_token_lifetime_earned,
            fan_type=profile.fan_type,
            created_at=user.created_at,
        ),
        identity=identity_response,
        collectibles=collectibles,
        creations=[await _fan_nft_listing_response(session, item, user_id=None) for item in applications],
    )


@router.post("/identity/sync", response_model=MyCollectionResponse)
async def sync_identity(
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> MyCollectionResponse:
    try:
        await nft_service.ensure_membership_identity(session, identity)
    except (NftValidationError, ChainConfigurationError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return await my_collection(identity, session)


async def _membership_card_action_response(
    session: AsyncSession,
    identity: AuthenticatedIdentity,
    *,
    changed: bool,
    fee_charged: int,
) -> MembershipCardActionResponse:
    profile = await session.get(UserProfile, identity.user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found")
    return MembershipCardActionResponse(
        collection=await my_collection(identity, session),
        fan_token_balance=profile.fan_token_balance,
        fee_charged=fee_charged,
        changed=changed,
    )


@router.post("/identity/card", response_model=MembershipCardActionResponse)
async def create_membership_card(
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> MembershipCardActionResponse:
    try:
        _, changed, fee_charged = await nft_service.create_membership_card(session, identity)
    except (NftValidationError, ChainConfigurationError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return await _membership_card_action_response(
        session,
        identity,
        changed=changed,
        fee_charged=fee_charged,
    )


@router.post("/identity/card/refresh", response_model=MembershipCardActionResponse)
async def refresh_membership_card(
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> MembershipCardActionResponse:
    try:
        _, changed, fee_charged = await nft_service.refresh_membership_card(session, identity)
    except (NftValidationError, ChainConfigurationError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return await _membership_card_action_response(
        session,
        identity,
        changed=changed,
        fee_charged=fee_charged,
    )


@router.get("/creations", response_model=list[FanNftListingResponse])
async def fan_nft_marketplace(
    limit: int = 24,
    offset: int = 0,
    identity: AuthenticatedIdentity | None = Depends(get_optional_identity),
    session: AsyncSession = Depends(get_database_session),
) -> list[FanNftListingResponse]:
    limit = min(max(limit, 1), 60)
    offset = max(offset, 0)
    applications = list(
        (
            await session.execute(
                select(NftApplication)
                .where(col(NftApplication.status).in_(["MINTED", "MINTING", "FAILED"]))
                .order_by(col(NftApplication.created_at).desc())
                .offset(offset)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    user_id = identity.user_id if identity else None
    return [await _fan_nft_listing_response(session, item, user_id=user_id) for item in applications]


@router.get("/creations/{creation_id}", response_model=FanNftListingResponse)
async def fan_nft_detail(
    creation_id: str,
    identity: AuthenticatedIdentity | None = Depends(get_optional_identity),
    session: AsyncSession = Depends(get_database_session),
) -> FanNftListingResponse:
    application = await session.get(NftApplication, creation_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NFT not found")
    return await _fan_nft_listing_response(
        session,
        application,
        user_id=identity.user_id if identity else None,
        include_mint_records=True,
    )


async def _toggle_nft_reaction(
    session: AsyncSession,
    *,
    application: NftApplication,
    user_id: str,
    field: str,
) -> FanNftEngagementResponse:
    reaction = (
        await session.execute(
            select(NftCreationReaction).where(
                NftCreationReaction.application_id == application.id,
                NftCreationReaction.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if reaction is None:
        reaction = NftCreationReaction(application_id=application.id, user_id=user_id)
        session.add(reaction)
    setattr(reaction, field, not bool(getattr(reaction, field)))
    reaction.updated_at = utc_now()
    await session.commit()
    like_count, favorite_count, liked, favorited = await _fan_nft_engagement(session, application.id, user_id)
    return FanNftEngagementResponse(
        creation_id=application.id,
        liked=liked,
        favorited=favorited,
        like_count=like_count,
        favorite_count=favorite_count,
    )


@router.post("/creations/{creation_id}/like", response_model=FanNftEngagementResponse)
async def toggle_fan_nft_like(
    creation_id: str,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> FanNftEngagementResponse:
    application = await session.get(NftApplication, creation_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NFT not found")
    return await _toggle_nft_reaction(session, application=application, user_id=identity.user_id, field="liked")


@router.post("/creations/{creation_id}/favorite", response_model=FanNftEngagementResponse)
async def toggle_fan_nft_favorite(
    creation_id: str,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> FanNftEngagementResponse:
    application = await session.get(NftApplication, creation_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NFT not found")
    return await _toggle_nft_reaction(session, application=application, user_id=identity.user_id, field="favorited")


@router.post("/creations", response_model=FanNftCreateResponse, status_code=status.HTTP_201_CREATED)
async def publish_fan_nft(
    payload: NftApplicationCreate,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> FanNftCreateResponse:
    try:
        application = await nft_service.publish_fan_nft(session, identity, payload)
        profile = await session.get(UserProfile, identity.user_id)
    except NftValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except ChainConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except Exception as error:
        logger.exception("fan_nft_publish_failed", user_id=identity.user_id, error=str(error))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"NFT publishing failed: {error}",
        ) from error
    return FanNftCreateResponse(
        listing=await _fan_nft_listing_response(
            session,
            application,
            user_id=identity.user_id,
            include_mint_records=True,
        ),
        fan_token_balance=profile.fan_token_balance if profile else 0,
    )


@router.post("/creations/ai-draft", response_model=NftDraftResponse)
async def create_fan_nft_ai_draft(
    payload: NftDraftRequest,
    _: AuthenticatedIdentity = Depends(require_official_member),
) -> NftDraftResponse:
    """Generate a creator-editable draft; this endpoint never publishes or mints."""

    return await nft_creation_agent.create_draft(payload.model_copy(update={"generate_image": False}))


@router.get("/creations/agent/templates", response_model=list[NftVisualTemplate])
async def get_fan_nft_visual_templates(
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> list[NftVisualTemplate]:
    """Return system templates and templates owned by the current creator."""

    return await nft_visual_template_service.list_for_user(session, identity.user_id)


@router.get("/creations/agent/styles", response_model=list[NftVisualStyle])
async def get_fan_nft_visual_styles(
    _: AuthenticatedIdentity = Depends(require_official_member),
) -> list[NftVisualStyle]:
    return [NftVisualStyle.model_validate(item) for item in VISUAL_STYLE_OPTIONS]


@router.post("/creations/agent/analyze-upload", response_model=NftUploadedImageAnalysisResponse)
async def analyze_uploaded_fan_nft_image(
    payload: NftUploadedImageAnalyzeRequest,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> NftUploadedImageAnalysisResponse:
    template = await nft_visual_template_service.get_for_user(session, identity.user_id, payload.template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visual template not found")
    style = next((item for item in VISUAL_STYLE_OPTIONS if item["id"] == payload.visual_style), None)
    if style is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Visual style not found")
    return await nft_upload_analysis_agent.analyze(
        image_url=payload.image_url,
        template=template,
        style_name=str(style["name"]),
        style_prompt=STYLE_PROMPTS[payload.visual_style],
    )


@router.post("/creations/agent/templates", response_model=NftVisualTemplate, status_code=status.HTTP_201_CREATED)
async def create_fan_nft_visual_template(
    payload: NftVisualTemplateCreate,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> NftVisualTemplate:
    try:
        return await nft_visual_template_service.create(session, identity.user_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.put("/creations/agent/templates/{template_id}", response_model=NftVisualTemplate)
async def update_fan_nft_visual_template(
    template_id: str,
    payload: NftVisualTemplateUpdate,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> NftVisualTemplate:
    try:
        template = await nft_visual_template_service.update(session, identity.user_id, template_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visual template not found")
    return template


@router.post("/creations/agent/chat", response_model=NftAgentChatResponse)
async def chat_with_fan_nft_agent(
    payload: NftAgentChatRequest,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> NftAgentChatResponse:
    """Advance one checkpointed story-development turn without publishing."""

    available_templates = await nft_visual_template_service.list_for_user(session, identity.user_id)
    template = next((item for item in available_templates if item.id == payload.template_id), None)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visual template not found")
    template = await nft_visual_template_service.get_for_user(session, identity.user_id, template.id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visual template not found")
    clean_payload = payload.model_copy(
        update={"reference_image_urls": [url for url in payload.reference_image_urls if not url.startswith("/img/")]}
    )
    return await nft_studio_agent.chat(identity.user_id, clean_payload, template, available_templates)


@router.post("/creations/{creation_id}/buy", response_model=FanNftPurchaseResponse)
async def buy_fan_nft(
    creation_id: str,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> FanNftPurchaseResponse:
    application = await session.get(NftApplication, creation_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NFT not found")
    try:
        ownership = await nft_service.buy_fan_nft(session, identity, application)
    except (NftValidationError, ChainConfigurationError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except Exception as error:
        logger.exception(
            "fan_nft_purchase_failed", user_id=identity.user_id, creation_id=creation_id, error=str(error)
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"NFT purchase minting failed: {error}",
        ) from error
    profile = await session.get(UserProfile, identity.user_id)
    token_type = await session.get(CollectibleTokenType, ownership.token_type_id)
    operation = (
        await session.get(ChainOperation, ownership.chain_operation_id) if ownership.chain_operation_id else None
    )
    if token_type is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="NFT token type is missing")
    metadata = (
        (
            await session.execute(
                select(NftMetadataVersion)
                .where(NftMetadataVersion.metadata_cid == token_type.metadata_cid)
                .order_by(col(NftMetadataVersion.created_at).desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )
    collectible = CollectibleResponse(
        token_type_id=token_type.id,
        fan_nft_creation_id=token_type.source_id if token_type.source_type == "FAN_NFT" else None,
        token_id=token_type.token_id,
        category=token_type.category,
        name=token_type.name,
        description=token_type.description,
        metadata_uri=pinata_adapter.ipfs_uri(token_type.metadata_cid),
        image_url=pinata_adapter.gateway_url(metadata.image_cid) if metadata else None,
        amount=ownership.amount,
        max_supply=token_type.max_supply,
        minted_supply=token_type.minted_supply,
        transferable=token_type.transferable,
        status=ownership.status,
        contract_address=token_type.contract_address,
        chain_id=token_type.chain_id,
        explorer_url=f"https://testnet.monadvision.com/nft/{token_type.contract_address}/{token_type.token_id}?tab=Overview",
        operation=ChainOperationResponse.model_validate(operation) if operation else None,
    )
    return FanNftPurchaseResponse(
        listing=await _fan_nft_listing_response(
            session,
            application,
            user_id=identity.user_id,
            include_mint_records=True,
        ),
        collectible=collectible,
        fan_token_balance=profile.fan_token_balance if profile else 0,
    )


@router.post("/collectibles/{token_type_id}/avatar", response_model=CollectibleAvatarResponse)
async def set_collectible_avatar(
    token_type_id: str,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> CollectibleAvatarResponse:
    try:
        avatar_url = await nft_service.set_collectible_avatar(session, identity, token_type_id)
    except NftValidationError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return CollectibleAvatarResponse(token_type_id=token_type_id, avatar_url=avatar_url)
