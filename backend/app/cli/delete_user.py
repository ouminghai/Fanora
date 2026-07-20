"""Delete a test user from the configured database."""

import argparse
import asyncio
import json
from dataclasses import asdict

from app.core.config import Environment, settings
from app.core.database import database_service
from app.services.user_cleanup import UserCleanupError, delete_user_by_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete one Fanora test user and its dependent records.")
    parser.add_argument("--user-id", required=True, help="Exact users.id value to delete")
    parser.add_argument(
        "--confirm",
        required=True,
        help="Must exactly match --user-id to guard against accidental deletion",
    )
    parser.add_argument(
        "--delete-owned-communities",
        action="store_true",
        help="Also delete communities owned by this user and every membership in those communities",
    )
    return parser.parse_args()


async def run() -> int:
    args = parse_args()
    if settings.environment == Environment.PRODUCTION:
        raise SystemExit("Refusing to delete users while ENVIRONMENT=production")
    if args.confirm != args.user_id:
        raise SystemExit("--confirm must exactly match --user-id")

    try:
        async with database_service.session() as session:
            result = await delete_user_by_id(
                session,
                args.user_id,
                delete_owned_communities=args.delete_owned_communities,
            )
    except UserCleanupError as error:
        raise SystemExit(str(error)) from error
    finally:
        await database_service.close()

    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
