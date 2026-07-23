"""Upload membership level badge images to Pinata and persist their CIDs."""

import argparse
import asyncio
from dataclasses import dataclass

from sqlmodel import col, select

from app.adapters.pinata import pinata_adapter
from app.core.database import database_service
from app.models.membership import MembershipLevel
from app.models.nft import MembershipIdentityNft
from app.services.identity import AuthenticatedIdentity
from app.services.nft import nft_service


@dataclass(slots=True)
class UploadSummary:
    uploaded: int = 0
    skipped: int = 0
    failed: int = 0
    identities_updated: int = 0
    identities_skipped: int = 0
    identities_failed: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload membership level badge images to Pinata.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Upload every level again, including levels that already have a CID.",
    )
    parser.add_argument(
        "--refresh-identities",
        action="store_true",
        help="Rebuild metadata and update every confirmed membership identity on-chain.",
    )
    return parser.parse_args()


async def upload_membership_levels(*, force: bool) -> UploadSummary:
    if not pinata_adapter.configured:
        raise RuntimeError("PINATA_JWT is not configured in backend/.env")

    summary = UploadSummary()
    async with database_service.session() as session:
        levels = list(
            (
                await session.execute(
                    select(MembershipLevel).order_by(col(MembershipLevel.rank))
                )
            ).scalars()
        )
        if not levels:
            raise RuntimeError("No membership levels were found in the database")

        for level in levels:
            if level.badge_image_cid and not force:
                summary.skipped += 1
                print(f"SKIP  {level.code}: ipfs://{level.badge_image_cid}")
                continue

            if force:
                level.badge_image_cid = None
                level.badge_image_pin_id = None
                level.badge_image_content_hash = None

            try:
                cid = await nft_service._pin_membership_level_image(level)
                await session.commit()
                summary.uploaded += 1
                print(f"OK    {level.code}: ipfs://{cid}")
            except Exception as error:
                await session.rollback()
                summary.failed += 1
                print(f"FAIL  {level.code}: {error}")

    return summary


async def refresh_membership_identities(summary: UploadSummary) -> None:
    async with database_service.session() as session:
        identities = list(
            (
                await session.execute(
                    select(MembershipIdentityNft).order_by(
                        col(MembershipIdentityNft.token_id)
                    )
                )
            ).scalars()
        )
        for record in identities:
            if record.token_id is None or record.status not in {"CONFIRMED", "RETRYABLE"}:
                summary.identities_skipped += 1
                print(f"SKIP  identity user={record.user_id}: status={record.status}")
                continue
            identity = AuthenticatedIdentity(
                user_id=record.user_id,
                primary_wallet=record.wallet_address,
                wallet_type="external",
                provider="badge-refresh-script",
            )
            try:
                refreshed = await nft_service.refresh_membership_identity_metadata(
                    session,
                    identity,
                )
                if refreshed.status == "CONFIRMED":
                    summary.identities_updated += 1
                    print(
                        f"OK    identity token={refreshed.token_id}: "
                        f"ipfs://{refreshed.metadata_cid}"
                    )
                else:
                    summary.identities_failed += 1
                    print(
                        f"FAIL  identity token={refreshed.token_id}: "
                        f"status={refreshed.status}"
                    )
            except Exception as error:
                await session.rollback()
                summary.identities_failed += 1
                print(f"FAIL  identity token={record.token_id}: {error}")


async def main() -> int:
    args = parse_args()
    try:
        summary = await upload_membership_levels(force=args.force)
        if args.refresh_identities and not summary.failed:
            await refresh_membership_identities(summary)
    finally:
        await database_service.close()

    print(
        "SUMMARY "
        f"uploaded={summary.uploaded} skipped={summary.skipped} failed={summary.failed} "
        f"identities_updated={summary.identities_updated} "
        f"identities_skipped={summary.identities_skipped} "
        f"identities_failed={summary.identities_failed}"
    )
    return 1 if summary.failed or summary.identities_failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
