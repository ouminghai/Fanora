"""Database-backed visual-template library for the NFT studio."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.adapters.cos import cos_adapter
from app.models.base import utc_now
from app.models.community import CommunityPost
from app.models.nft import NftVisualTemplate as NftVisualTemplateModel
from app.schemas.nft_agent import NftVisualTemplate, NftVisualTemplateCreate, NftVisualTemplateUpdate


def template_response(template: NftVisualTemplateModel) -> NftVisualTemplate:
    return NftVisualTemplate(
        id=template.id,
        owner_user_id=template.owner_user_id,
        source_post_id=template.source_post_id,
        name=template.name,
        category=template.category,
        description=template.description,
        prompt=template.prompt,
        preview_image_url=template.preview_image_url,
        reference_image_urls=template.reference_image_urls,
        palette=template.palette,
        elements=template.elements,
        forbidden=template.forbidden,
        is_system=template.is_system,
    )


class NftVisualTemplateService:
    async def list_for_user(self, session: AsyncSession, user_id: str) -> list[NftVisualTemplate]:
        rows = (
            await session.execute(
                select(NftVisualTemplateModel)
                .where(
                    col(NftVisualTemplateModel.is_system).is_(True)
                    | (NftVisualTemplateModel.owner_user_id == user_id)
                )
                .order_by(col(NftVisualTemplateModel.is_system).desc(), col(NftVisualTemplateModel.created_at).desc())
            )
        ).scalars().all()
        return [template_response(item) for item in rows]

    async def get_for_user(self, session: AsyncSession, user_id: str, template_id: str) -> NftVisualTemplate | None:
        item = await session.get(NftVisualTemplateModel, template_id)
        if item is None or (not item.is_system and item.owner_user_id != user_id):
            return None
        normalized = await cos_adapter.ensure_remote_urls(
            item.reference_image_urls,
            filename_prefix=f"nft-template-{item.id}",
        )
        if normalized and normalized != item.reference_image_urls:
            item.reference_image_urls = normalized
            item.preview_image_url = normalized[0]
            item.updated_at = utc_now()
            session.add(item)
            await session.commit()
            await session.refresh(item)
        return template_response(item)

    async def update(
        self,
        session: AsyncSession,
        user_id: str,
        template_id: str,
        payload: NftVisualTemplateUpdate,
    ) -> NftVisualTemplate | None:
        item = await session.get(NftVisualTemplateModel, template_id)
        if item is None or item.owner_user_id != user_id or item.is_system:
            return None
        references = list(dict.fromkeys(payload.reference_image_urls))[:6]
        if not references:
            raise ValueError("A visual template requires at least one reference image")
        remote_urls = await cos_adapter.ensure_remote_urls(
            references,
            filename_prefix=f"nft-template-{template_id}",
        )
        if not remote_urls:
            raise ValueError("A visual template requires at least one reference image")
        item.name = payload.name.strip()
        item.category = payload.category.strip()
        item.description = payload.description.strip()
        item.prompt = payload.prompt.strip()
        item.preview_image_url = remote_urls[0]
        item.reference_image_urls = remote_urls
        item.palette = payload.palette
        item.elements = payload.elements
        item.forbidden = payload.forbidden
        item.updated_at = utc_now()
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return template_response(item)

    async def create(
        self,
        session: AsyncSession,
        user_id: str,
        payload: NftVisualTemplateCreate,
    ) -> NftVisualTemplate:
        references = list(payload.reference_image_urls)
        if payload.source_post_id:
            post = await session.get(CommunityPost, payload.source_post_id)
            if post is None or post.status != "published":
                raise ValueError("Selected post is unavailable")
            references.extend([post.cover_url] if post.cover_url else [])
            references.extend(post.image_urls)
        references = list(dict.fromkeys(references))[:6]
        if not references:
            raise ValueError("A visual template requires at least one reference image")
        remote_urls = await cos_adapter.ensure_remote_urls(
            references,
            filename_prefix=f"nft-template-{user_id}",
        )
        if not remote_urls:
            raise ValueError("A visual template requires at least one reference image")
        item = NftVisualTemplateModel(
            owner_user_id=user_id,
            source_post_id=payload.source_post_id,
            name=payload.name.strip(),
            category=payload.category.strip(),
            description=payload.description.strip(),
            prompt=payload.prompt.strip(),
            preview_image_url=remote_urls[0],
            reference_image_urls=remote_urls,
            palette=payload.palette,
            elements=payload.elements,
            forbidden=payload.forbidden,
            is_system=False,
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return template_response(item)


nft_visual_template_service = NftVisualTemplateService()
