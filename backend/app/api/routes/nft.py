"""Fan collection, identity synchronization, and custom badge applications."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.adapters.monad import ChainConfigurationError, monad_contract_adapter
from app.adapters.pinata import pinata_adapter
from app.core.config import settings
from app.core.database import get_database_session
from app.core.security import get_current_identity, require_official_member
from app.models.base import utc_now
from app.models.nft import (
    ChainOperation,
    CollectibleOwnership,
    CollectibleTokenType,
    MembershipIdentityNft,
    NftApplication,
    NftMetadataVersion,
)
from app.models.user import UserRole
from app.schemas.nft import (
    ChainOperationResponse,
    CollectibleResponse,
    MembershipIdentityResponse,
    MyCollectionResponse,
    NftApplicationCreate,
    NftApplicationResponse,
    NftApplicationReview,
)
from app.services.identity import AuthenticatedIdentity
from app.services.nft import NftValidationError, nft_service

router = APIRouter(prefix="/nft")


def _application_response(application: NftApplication) -> NftApplicationResponse:
    return NftApplicationResponse(
        id=application.id,
        name=application.name,
        description=application.description,
        theme=application.theme,
        public_attributes=application.public_attributes,
        copyright_declaration=application.copyright_declaration,
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


async def _require_reviewer(session: AsyncSession, user_id: str) -> None:
    role = (
        await session.execute(
            select(UserRole.id).where(UserRole.user_id == user_id, col(UserRole.role).in_(["creator", "admin"]))
        )
    ).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Creator or admin role required")


@router.get("/me", response_model=MyCollectionResponse)
async def my_collection(
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> MyCollectionResponse:
    identity_nft = (
        await session.execute(select(MembershipIdentityNft).where(MembershipIdentityNft.user_id == identity.user_id))
    ).scalar_one_or_none()
    identity_response = None
    if identity_nft is not None:
        operation = await session.get(ChainOperation, identity_nft.chain_operation_id) if identity_nft.chain_operation_id else None
        metadata = (
            await session.execute(
                select(NftMetadataVersion).where(
                    NftMetadataVersion.subject_type == "MEMBERSHIP_IDENTITY",
                    NftMetadataVersion.subject_id == identity.user_id,
                    NftMetadataVersion.version == identity_nft.metadata_version,
                )
            )
        ).scalar_one_or_none()
        identity_response = MembershipIdentityResponse(
            token_id=identity_nft.token_id,
            level_id=identity_nft.level_id,
            level_code=identity_nft.level_code,
            metadata_version=identity_nft.metadata_version,
            metadata_uri=pinata_adapter.ipfs_uri(identity_nft.metadata_cid),
            image_url=pinata_adapter.gateway_url(metadata.image_cid) if metadata else None,
            status=identity_nft.status,
            contract_address=identity_nft.contract_address,
            chain_id=identity_nft.chain_id,
            explorer_url=(
                f"https://testnet.monadexplorer.com/address/{identity_nft.contract_address}"
                if identity_nft.contract_address
                else None
            ),
            operation=ChainOperationResponse.model_validate(operation) if operation else None,
        )

    rows = (
        await session.execute(
            select(CollectibleOwnership, CollectibleTokenType)
            .join(CollectibleTokenType, col(CollectibleTokenType.id) == CollectibleOwnership.token_type_id)
            .where(CollectibleOwnership.user_id == identity.user_id)
            .order_by(col(CollectibleOwnership.created_at).desc())
        )
    ).all()
    collectibles: list[CollectibleResponse] = []
    for ownership, token_type in rows:
        operation = await session.get(ChainOperation, ownership.chain_operation_id) if ownership.chain_operation_id else None
        metadata = (
            await session.execute(select(NftMetadataVersion).where(NftMetadataVersion.metadata_cid == token_type.metadata_cid))
        ).scalar_one_or_none()
        collectibles.append(
            CollectibleResponse(
                token_type_id=token_type.id,
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
                explorer_url=f"https://testnet.monadexplorer.com/address/{token_type.contract_address}",
                operation=ChainOperationResponse.model_validate(operation) if operation else None,
            )
        )
    applications = list(
        (await session.execute(select(NftApplication).where(NftApplication.user_id == identity.user_id).order_by(col(NftApplication.created_at).desc()))).scalars().all()
    )
    sync_status = identity_nft.status if identity_nft else (
        "READY" if monad_contract_adapter.identity_configured and pinata_adapter.configured else "NOT_CONFIGURED"
    )
    return MyCollectionResponse(
        chain_id=settings.monad_chain_id,
        identity_sync_status=sync_status,
        identity=identity_response,
        collectibles=collectibles,
        applications=[_application_response(item) for item in applications],
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


@router.post("/applications", response_model=NftApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: NftApplicationCreate,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> NftApplicationResponse:
    try:
        application = await nft_service.create_application(session, identity, payload)
    except NftValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return _application_response(application)


@router.post("/applications/{application_id}/submit", response_model=NftApplicationResponse)
async def submit_application(
    application_id: str,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> NftApplicationResponse:
    application = await session.get(NftApplication, application_id)
    if application is None or application.user_id != identity.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NFT application not found")
    if application.status != "DRAFT":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only draft applications can be submitted")
    application.status = "SUBMITTED"
    application.submitted_at = utc_now()
    application.updated_at = utc_now()
    await session.commit()
    return _application_response(application)


@router.put("/applications/{application_id}/review", response_model=NftApplicationResponse)
async def review_application(
    application_id: str,
    payload: NftApplicationReview,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> NftApplicationResponse:
    await _require_reviewer(session, identity.user_id)
    application = await session.get(NftApplication, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NFT application not found")
    if application.status not in {"SUBMITTED", "UNDER_REVIEW"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Application is not awaiting review")
    if payload.decision == "REJECTED" and not payload.reason:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Rejection reason is required")
    application.status = payload.decision
    application.rejection_reason = payload.reason if payload.decision == "REJECTED" else None
    application.internal_review_note = payload.internal_note
    application.reviewed_by_user_id = identity.user_id
    application.reviewed_at = utc_now()
    application.updated_at = utc_now()
    await session.commit()
    return _application_response(application)


@router.post("/applications/{application_id}/process", response_model=NftApplicationResponse)
async def process_application(
    application_id: str,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> NftApplicationResponse:
    await _require_reviewer(session, identity.user_id)
    application = await session.get(NftApplication, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NFT application not found")
    try:
        await nft_service.process_custom_badge(session, application)
    except (NftValidationError, ChainConfigurationError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="NFT pinning or minting failed") from error
    return _application_response(application)
